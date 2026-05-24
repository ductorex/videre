import pytest

from videre.core.events import Key, KeyboardEntry, KeyMod


@pytest.mark.parametrize(
    "modifier,prop,combined",
    [
        (KeyMod.LSHIFT, "lshift", "shift"),
        (KeyMod.RSHIFT, "rshift", "shift"),
        (KeyMod.LCTRL, "lctrl", "ctrl"),
        (KeyMod.RCTRL, "rctrl", "ctrl"),
        (KeyMod.LALT, "lalt", "alt"),
        (KeyMod.RALT, "ralt", "alt"),
    ],
)
def test_modifier_routing(modifier, prop, combined):
    """Each modifier flips its individual property AND its combined L/R alias."""
    entry = KeyboardEntry(modifiers=frozenset([modifier]))
    assert getattr(entry, prop)
    assert getattr(entry, combined)


def test_caps_modifier():
    """CAPS is its own modifier with no L/R variant."""
    entry = KeyboardEntry(modifiers=frozenset([KeyMod.CAPS]))
    assert entry.caps
    assert not entry.shift and not entry.ctrl and not entry.alt


def test_special_keys_are_mutually_exclusive():
    """For each key, exactly one key-property is True and all others are False."""
    key_props = [
        (Key.UP, "up"),
        (Key.DOWN, "down"),
        (Key.LEFT, "left"),
        (Key.RIGHT, "right"),
        (Key.HOME, "home"),
        (Key.END, "end"),
        (Key.PAGEUP, "pageup"),
        (Key.PAGEDOWN, "pagedown"),
        (Key.BACKSPACE, "backspace"),
        (Key.DELETE, "delete"),
        (Key.TAB, "tab"),
        (Key.ENTER, "enter"),
        (Key.ESCAPE, "escape"),
        (Key.PRINTSCREEN, "printscreen"),
        (Key.A, "A"),
        (Key.C, "C"),
        (Key.V, "V"),
    ]
    all_props = [prop for _, prop in key_props]

    for key, prop in key_props:
        entry = KeyboardEntry(key=key)
        assert getattr(entry, prop) is True
        for other in all_props:
            if other != prop:
                assert getattr(entry, other) is False


def test_keyboard_entry_repr():
    """Empty modifiers render as '', non-empty join modifier names with ' + '."""
    assert repr(KeyboardEntry(key=Key.A, unicode="a")) == ""

    repr_str = repr(
        KeyboardEntry(modifiers=frozenset([KeyMod.LCTRL, KeyMod.LSHIFT]), key=Key.C)
    )
    assert "ctrl" in repr_str
    assert "shift" in repr_str
    assert " + " in repr_str
