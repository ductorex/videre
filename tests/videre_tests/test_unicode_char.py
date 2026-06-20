from videre.core.textual.unicode_char import get_character


def test_font_coverage_profile() -> None:
    assert get_character("A").requires_font_glyph()
    assert get_character(" ").requires_font_glyph()  # Space (still needs a glyph)
    assert get_character("\u0301").requires_font_glyph()
    assert not get_character("\ue000").requires_font_glyph()  # Private use
    assert not get_character("\ufe0f").requires_font_glyph()  # Variation selector
    assert not get_character("\u200d").requires_font_glyph()  # ZWJ
    assert not get_character("\v").requires_font_glyph()  # Control


def test_blocks():
    assert get_character("A").block == "Basic Latin"
