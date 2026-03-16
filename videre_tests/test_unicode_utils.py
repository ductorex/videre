from videre.fonts.unicode_utils import Unicode


def test_printable():
    assert Unicode._printable("A") is True
    assert Unicode._printable("é") is True
    assert Unicode._printable("\x00") is False  # Cc - control
    assert Unicode._printable("\ud800") is False  # Cs - surrogate
    assert Unicode._printable("\ufdd0") is False  # Cn - non-character


def test_printable_private_use():
    # Co - private use area
    assert Unicode._printable("\ue000") is False


def test_blocks():
    blocks = Unicode.blocks()
    assert isinstance(blocks, dict)
    assert "Basic Latin" in blocks
    assert "A" in blocks["Basic Latin"]
