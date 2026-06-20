from videre.core.pygame_backend.font_factory_utils import Unicode


def test_printable():
    assert Unicode.FONT_COVERAGE_VERSION == "16.0.0"
    assert Unicode.printable("A") is True
    assert Unicode.printable("é") is True
    assert Unicode.printable("\x00") is False  # Cc - control
    assert Unicode.printable("\ud800") is False  # Cs - surrogate
    assert Unicode.printable("\ufdd0") is False  # Cn - non-character


def test_printable_private_use():
    # Co - private use area
    assert Unicode.printable("\ue000") is False
