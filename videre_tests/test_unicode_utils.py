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


def test_blocks():
    blocks = Unicode.blocks()
    assert isinstance(blocks, dict)
    assert "Basic Latin" in blocks
    assert "A" in blocks["Basic Latin"]
