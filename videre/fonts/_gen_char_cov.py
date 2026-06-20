"""
Main script to generate char-support.json
"""

import json
import logging
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTCollection
from tqdm import tqdm
from uharfbuzz import Buffer, BufferFlags, Face, Font, ot_font_set_funcs, shape

from videre.core.textual.coverage import (
    UNICODE_VERSION,
    FontCapabilities,
    font_coverage_characters,
    open_type_script_tags,
)
from videre.core.textual.unicode_char import get_character
from videre.fonts.font_utils import FontUtils
from videre.fonts.provider import (
    FOLDER_FONT,
    FONT_NOTO_REGULAR,
    JSON_FONT_CAPABILITIES,
    JSON_FONT_TO_CHARACTERS,
    JSON_SEQUENCE_TO_FONT,
    get_fonts,
)
from videre.fonts.unicode_sequences import load_unicode_sequences

logger = logging.getLogger(__name__)

_COVERAGE_REPORT_PATH = os.path.join(FOLDER_FONT, "_coverage-report.json")
_NOTO_EMOJI = "Noto Emoji Regular"

PRIORITY_FONTS: dict[str, list[str]] = {
    "_": [
        FONT_NOTO_REGULAR.name,
        # Math and Symbols 2 ranked above the CJK fonts so widget icons
        # (geometric shapes, dingbats) stay rendered as compact symbols
        # rather than being pulled into the CJK fonts' fullwidth style.
        "Noto Sans Math Regular",
        "Noto Sans Symbols 2 Regular",
        # CJK Light: aerated sans-serif rendering close to Yu Gothic UI Regular,
        # avoids both BabelStone (Mincho/serif) and Plangothic (too bold).
        # JP first matches the project's "modern Japanese" reference rendering;
        # the others fill in script-specific glyphs.
        "Noto Sans JP Light",
        "Noto Sans HK Light",
        "Noto Sans SC Light",
        "Noto Sans TC Light",
        "Noto Sans KR Light",
    ],
    "Arabic": ["Noto Sans Arabic Regular"],
    "Arabic Presentation Forms-B": ["Noto Sans Arabic Regular"],
    "Hangul Compatibility Jamo": ["Noto Sans KR Light"],
    "Khitan Small Script": ["Noto Fangsong KSS Vertical Regular"],
    "Khojki": ["Noto Sans Khojki Regular", "Noto Serif Khojki Regular"],
    "Syriac": [
        "Noto Sans Syriac Regular",
        "Noto Sans Syriac Eastern Regular",
        "Noto Sans Syriac Western Regular",
    ],
    "Syriac Supplement": [
        "Noto Sans Syriac Regular",
        "Noto Sans Syriac Eastern Regular",
        "Noto Sans Syriac Western Regular",
    ],
}


class _FontPrioritizer:
    def __init__(self):
        self._block_to_font_to_rank: dict[str, dict[str, int]] = {
            block: {font: rank for rank, font in enumerate(fonts)}
            for block, fonts in PRIORITY_FONTS.items()
        }
        self._default_font_to_rank: dict[str, int] = self._block_to_font_to_rank.pop(
            "_"
        )

    def get_font_rank_for_unicode_block(
        self, unicode_block: str, font_name: str
    ) -> int | None:
        if unicode_block in self._block_to_font_to_rank:
            return self._block_to_font_to_rank[unicode_block].get(font_name)
        else:
            return self._default_font_to_rank.get(font_name)


_FONT_PRIORITIZER = _FontPrioritizer()


def _font_priority_key(
    font_name: str,
    character: str,
    block_to_cov: dict[str, list[str]],
    capabilities: dict[str, FontCapabilities],
    *,
    prefer_layout: bool,
) -> tuple[int, int, int, int, str]:
    unicode_block = get_character(character).block
    rank = _FONT_PRIORITIZER.get_font_rank_for_unicode_block(unicode_block, font_name)
    layout_support = capabilities[font_name].layout_support(
        open_type_script_tags(character)
    )
    return (
        -layout_support if prefer_layout else 0,
        rank is None,
        rank if rank is not None else 0,
        -len(block_to_cov[unicode_block]),
        font_name,
    )


def _rank_fonts(
    names: list[str],
    character: str,
    font_to_block_to_cov: dict[str, dict[str, list[str]]],
    capabilities: dict[str, FontCapabilities],
) -> list[str]:
    script_tags = open_type_script_tags(character)
    prefer_layout = bool(script_tags) and any(
        capabilities[name].layout_support(script_tags) for name in names
    )
    return sorted(
        names,
        key=lambda name: _font_priority_key(
            name,
            character,
            font_to_block_to_cov[name],
            capabilities,
            prefer_layout=prefer_layout,
        ),
    )


def generate_char_to_font(
    fonts: list[FontUtils] | None = None,
    capabilities: dict[str, FontCapabilities] | None = None,
) -> dict[str, str]:
    font_to_block_to_cov: dict[str, dict[str, list[str]]] = {}

    fonts = fonts or _load_fonts()
    capabilities = capabilities or generate_font_capabilities(fonts)

    char_to_fonts = {}
    for font in fonts:
        coverage = font.coverage()
        font_to_block_to_cov[font.name] = coverage
        for block, covered_chars in coverage.items():
            for c in covered_chars:
                char_to_fonts.setdefault(c, []).append(font.name)
    nb_unicode = sum(1 for _ in font_coverage_characters())
    nb_covered = len(char_to_fonts)

    char_to_font: dict[str, str] = {
        c: (
            names[0]
            if len(names) == 1
            else _rank_fonts(names, c, font_to_block_to_cov, capabilities)[0]
        )
        for c, names in tqdm(char_to_fonts.items(), desc="Mapping char => font")
    }

    logger.info(
        f"fonts: {len(set(char_to_font.values()))} / {len(fonts)}, "
        f"characters: {nb_covered} / {nb_unicode} "
        f"({nb_covered * 100 / nb_unicode} %)"
    )
    return char_to_font


def generate_font_capabilities(fonts: list[FontUtils]) -> dict[str, FontCapabilities]:
    return {
        font.name: font.capabilities()
        for font in tqdm(fonts, desc="Inspecting font capabilities")
    }


def _font_capabilities_json(capabilities: dict[str, FontCapabilities]) -> dict:
    return {
        "schema_version": 1,
        "unicode_version": UNICODE_VERSION,
        "fonts": {
            name: {
                "codepoint_ranges": [
                    [start, end] for start, end in capability.codepoint_ranges
                ],
                "variation_sequences": sorted(capability.variation_sequences),
                "gsub_scripts": sorted(capability.gsub_scripts),
                "gpos_scripts": sorted(capability.gpos_scripts),
            }
            for name, capability in capabilities.items()
        },
    }


def _decode_sequence(value: str) -> str:
    return "".join(chr(int(codepoint, 16)) for codepoint in value.split())


class _RawShaper:
    def __init__(self, fonts: list[FontUtils]) -> None:
        self._fonts = {font.name: font for font in fonts}
        self._hb_fonts: dict[str, Font] = {}

    def shape(self, font_name: str, text: str) -> tuple[tuple[int, int], ...]:
        font = self._hb_fonts.get(font_name)
        if font is None:
            source = self._fonts[font_name]
            font = Font(Face(Path(source.path).read_bytes(), source.font_index))
            ot_font_set_funcs(font)
            self._hb_fonts[font_name] = font
        buffer = Buffer()
        buffer.add_str(text)
        buffer.flags = BufferFlags.DO_NOT_INSERT_DOTTED_CIRCLE
        buffer.guess_segment_properties()
        shape(font, buffer)
        return tuple((info.codepoint, info.cluster) for info in buffer.glyph_infos)

    def is_atomic_sequence(self, font_name: str, text: str) -> bool:
        glyphs = self.shape(font_name, text)
        return (
            bool(glyphs)
            and all(glyph_id != 0 for glyph_id, _ in glyphs)
            and len({cluster for _, cluster in glyphs}) == 1
        )

    def shapes_variant(self, font_name: str, text: str) -> bool:
        glyphs = self.shape(font_name, text)
        return (
            bool(glyphs)
            and all(glyph_id != 0 for glyph_id, _ in glyphs)
            and glyphs != self.shape(font_name, text[0])
        )


def generate_sequence_to_font(
    fonts: list[FontUtils],
    capabilities: dict[str, FontCapabilities],
    char_to_font: dict[str, str],
) -> tuple[dict[str, str], dict[str, dict]]:
    sequence_data = load_unicode_sequences()
    font_to_block_to_cov = {font.name: font.coverage() for font in fonts}
    raw_shaper = _RawShaper(fonts)
    routes: dict[str, str] = {}
    report: dict[str, dict] = {}

    variation_to_fonts: dict[str, list[str]] = {}
    for name, capability in capabilities.items():
        for sequence in capability.variation_sequences:
            variation_to_fonts.setdefault(sequence, []).append(name)

    for kind, encoded_sequences in sequence_data["sequences"].items():
        missing: list[str] = []
        for encoded in tqdm(encoded_sequences, desc=f"Routing {kind}"):
            text = _decode_sequence(encoded)
            selected: str | None = None

            if kind in {"standardized_variation", "ideographic_variation"}:
                names = variation_to_fonts.get(text, [])
                if names:
                    selected = _rank_fonts(
                        names, text[0], font_to_block_to_cov, capabilities
                    )[0]
                elif kind == "standardized_variation":
                    script_tags = open_type_script_tags(text[0])
                    names = [
                        font.name
                        for font in fonts
                        if all(
                            font.supports_raw_codepoint(ord(character))
                            for character in text
                        )
                        and bool(capabilities[font.name].gsub_scripts & script_tags)
                        and raw_shaper.shapes_variant(font.name, text)
                    ]
                    if names:
                        selected = _rank_fonts(
                            names, text[0], font_to_block_to_cov, capabilities
                        )[0]
            elif kind == "emoji_variation":
                selector = ord(text[-1])
                if selector == 0xFE0F and capabilities[
                    _NOTO_EMOJI
                ].supports_visible_codepoints(text):
                    selected = _NOTO_EMOJI
                elif selector == 0xFE0E:
                    preferred = char_to_font.get(text[0])
                    if preferred is not None and capabilities[
                        preferred
                    ].supports_visible_codepoints(text):
                        selected = preferred
            else:
                if capabilities[_NOTO_EMOJI].supports_visible_codepoints(
                    text
                ) and raw_shaper.is_atomic_sequence(_NOTO_EMOJI, text):
                    selected = _NOTO_EMOJI

            if selected is None:
                missing.append(encoded)
            else:
                routes[text] = selected
        report[kind] = {
            "target": len(encoded_sequences),
            "covered": len(encoded_sequences) - len(missing),
            "missing": missing,
        }
    return routes, report


def _shaping_report(char_to_font: dict[str, str], fonts: list[FontUtils]) -> dict:
    raw_shaper = _RawShaper(fonts)
    missing: list[str] = []
    multi_glyph: list[dict] = []
    for character, font_name in tqdm(
        char_to_font.items(), desc="Verifying selected-font shaping"
    ):
        glyphs = raw_shaper.shape(font_name, character)
        encoded = f"{ord(character):04X}"
        if not glyphs or any(glyph_id == 0 for glyph_id, _ in glyphs):
            missing.append(encoded)
        elif len(glyphs) > 1:
            multi_glyph.append(
                {
                    "codepoint": encoded,
                    "font": font_name,
                    "glyph_ids": [glyph_id for glyph_id, _ in glyphs],
                }
            )
    return {
        "checked": len(char_to_font),
        "missing": missing,
        "multi_glyph": multi_glyph,
    }


def _coverage_report(
    char_to_font: dict[str, str], sequence_report: dict[str, dict], shaping_report: dict
) -> dict:
    target = set(font_coverage_characters())
    covered = set(char_to_font)
    missing = sorted(target - covered, key=ord)
    blocks = Counter(get_character(character).block for character in missing)
    return {
        "schema_version": 1,
        "unicode_version": UNICODE_VERSION,
        "private_use_included": False,
        "codepoints": {
            "target": len(target),
            "covered": len(covered),
            "percent": len(covered) * 100 / len(target),
            "missing": [f"{ord(character):04X}" for character in missing],
            "missing_by_block": dict(blocks.most_common()),
        },
        "sequences": sequence_report,
        "shaping": shaping_report,
    }


@dataclass(slots=True, frozen=True)
class GeneratedFontArtifacts:
    font_to_characters: dict
    font_capabilities: dict
    sequence_to_font: dict
    coverage_report: dict


def generate_font_artifacts(
    fonts: list[FontUtils] | None = None,
) -> GeneratedFontArtifacts:
    fonts = fonts or _load_fonts()
    capabilities = generate_font_capabilities(fonts)
    char_to_font = generate_char_to_font(fonts, capabilities)
    sequence_to_font, sequence_report = generate_sequence_to_font(
        fonts, capabilities, char_to_font
    )
    shaping_report = _shaping_report(char_to_font, fonts)
    return GeneratedFontArtifacts(
        font_to_characters={
            "schema_version": 1,
            "unicode_version": UNICODE_VERSION,
            "fonts": _gen_font_to_characters(char_to_font),
        },
        font_capabilities=_font_capabilities_json(capabilities),
        sequence_to_font={
            "schema_version": 1,
            "unicode_version": UNICODE_VERSION,
            "sequences": sequence_to_font,
        },
        coverage_report=_coverage_report(char_to_font, sequence_report, shaping_report),
    )


def _load_fonts(font_table: dict[str, str] | None = None) -> list[FontUtils]:
    font_table = font_table or get_fonts()
    fonts = []
    for path in font_table.values():
        if path.lower().endswith(".ttc"):
            with TTCollection(path, lazy=True) as coll:
                nb_fonts = len(coll)
            print(f"Found TTC file {os.path.basename(path)} with {nb_fonts} fonts")
            fonts.extend(FontUtils(path, font_index=i) for i in range(nb_fonts))
        else:
            fonts.append(FontUtils(path))
    return fonts


def _gen_font_to_characters(char_to_font: dict[str, str]) -> dict[str, str]:
    font_to_chars: dict[str, list[str]] = {}
    for char, font_name in char_to_font.items():
        font_to_chars.setdefault(font_name, []).append(char)
    return {font_name: "".join(chars) for font_name, chars in font_to_chars.items()}


def _write_json(path: str, value: object) -> None:
    with open(path, "w", encoding="utf-8") as file:
        json.dump(value, file, ensure_ascii=False, separators=(",", ":"))


def generate_char_cov() -> None:
    artifacts = generate_font_artifacts()
    _write_json(JSON_FONT_TO_CHARACTERS, artifacts.font_to_characters)
    _write_json(JSON_FONT_CAPABILITIES, artifacts.font_capabilities)
    _write_json(JSON_SEQUENCE_TO_FONT, artifacts.sequence_to_font)
    _write_json(_COVERAGE_REPORT_PATH, artifacts.coverage_report)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, force=True)
    generate_char_cov()
