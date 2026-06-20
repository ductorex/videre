import json

from videre.core.textual.coverage import UNICODE_VERSION, requires_standalone_glyph
from videre.fonts._gen_char_cov import _COVERAGE_REPORT_PATH, generate_font_artifacts
from videre.fonts.provider import (
    JSON_FONT_CAPABILITIES,
    JSON_FONT_TO_CHARACTERS,
    JSON_SEQUENCE_TO_FONT,
    FontProvider,
)


def _load_json(path: str):
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def test_production_font_json_files_are_current() -> None:
    generated = generate_font_artifacts()

    assert _load_json(JSON_FONT_TO_CHARACTERS) == generated.font_to_characters
    assert _load_json(JSON_FONT_CAPABILITIES) == generated.font_capabilities
    assert _load_json(JSON_SEQUENCE_TO_FONT) == generated.sequence_to_font
    assert _load_json(_COVERAGE_REPORT_PATH) == generated.coverage_report


def test_generated_character_routing_uses_font_coverage_profile() -> None:
    font_to_characters = _load_json(JSON_FONT_TO_CHARACTERS)["fonts"]
    _fonts, char_to_indice = FontProvider._parse_font_to_characters(font_to_characters)

    assert len(char_to_indice) == 153936
    assert all(requires_standalone_glyph(c) for c in char_to_indice)
    assert "\ue000" not in char_to_indice
    assert "\ufe0f" not in char_to_indice


def test_generated_coverage_report_has_no_selected_notdef() -> None:
    report = _load_json(_COVERAGE_REPORT_PATH)

    assert report["unicode_version"] == UNICODE_VERSION
    assert report["private_use_included"] is False
    assert report["codepoints"]["target"] == 154591
    assert report["codepoints"]["missing_by_block"] == {
        "Egyptian Hieroglyphs Extended-A": 568,
        "Tulu-Tigalari": 80,
        "Symbols and Pictographs Extended-A": 7,
    }
    assert report["shaping"]["checked"] == report["codepoints"]["covered"]
    assert report["shaping"]["missing"] == []
    assert report["shaping"]["multi_glyph"]


def test_cluster_font_routing_handles_variation_kinds() -> None:
    provider = FontProvider()

    assert provider.get_font_info_for_cluster("0\ufe00")[0] == (
        "Noto Sans Math Regular"
    )
    assert provider.get_font_info_for_cluster("\u1000\ufe00")[0] == (
        "Noto Sans Myanmar Regular"
    )
    assert provider.get_font_info_for_cluster("\u3402\U000e0100")[0] == (
        "Noto Sans JP Light"
    )


def test_cluster_font_routing_distinguishes_emoji_presentation() -> None:
    provider = FontProvider()
    text_font = provider.get_font_info_for_cluster("\u231a\ufe0e")[0]
    emoji_font = provider.get_font_info_for_cluster("\u231a\ufe0f")[0]

    assert text_font == "Noto Sans Symbols 2 Regular"
    assert emoji_font == "Noto Emoji Regular"


def test_cluster_font_routing_keeps_combining_sequence_together() -> None:
    provider = FontProvider()
    name, _ = provider.get_font_info_for_cluster("A\u0301")
    assert name == "Noto Sans Regular"


def test_complex_scripts_prefer_fonts_with_open_type_layout() -> None:
    provider = FontProvider()

    assert provider.get_font_info("\U00011f12")[0] == "Noto Sans Kawi Regular"
    assert provider.get_font_info("\u0872")[0] == "Noto Sans Arabic Regular"
    assert provider.get_font_info("\U00011208")[0] == "Noto Sans Khojki Regular"
    assert provider.get_font_info("\U00011241")[0] == "Noto Serif Khojki Regular"
    assert provider.get_font_info("\U00011bc0")[0] == "Noto Sans Sunuwar Regular"
    assert provider.get_font_info("\U000105c0")[0] == "Noto Serif Todhri Regular"


def test_khojki_cluster_uses_serif_only_when_sans_lacks_a_character() -> None:
    provider = FontProvider()

    assert provider.get_font_info_for_cluster("\U00011208\U0001122d")[0] == (
        "Noto Sans Khojki Regular"
    )
    assert provider.get_font_info_for_cluster("\U00011208\U00011241")[0] == (
        "Noto Serif Khojki Regular"
    )
