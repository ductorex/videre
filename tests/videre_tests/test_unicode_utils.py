from videre.fonts.unicode_utils import Unicode


def test_printable():
    assert Unicode.printable("A") is True
    assert Unicode.printable("é") is True
    assert Unicode.printable("\x00") is False  # Cc - control
    assert Unicode.printable("\ud800") is False  # Cs - surrogate
    assert Unicode.printable("\ufdd0") is False  # Cn - non-character


def test_printable_private_use():
    # Co - private use area
    assert Unicode.printable("\ue000") is False


def test_font_coverage_profile() -> None:
    assert Unicode.FONT_COVERAGE_VERSION == "16.0.0"
    assert Unicode.requires_font_glyph("A")
    assert Unicode.requires_font_glyph(" ")
    assert Unicode.requires_font_glyph("\u0301")
    assert not Unicode.requires_font_glyph("\ue000")  # Private use
    assert not Unicode.requires_font_glyph("\ufe0f")  # Variation selector
    assert not Unicode.requires_font_glyph("\u200d")  # ZWJ
    assert not Unicode.requires_font_glyph("\v")  # Control


def test_blocks():
    blocks = Unicode.blocks()
    assert isinstance(blocks, dict)
    assert "Basic Latin" in blocks
    assert "A" in blocks["Basic Latin"]
