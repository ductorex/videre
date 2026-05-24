import pytest

from videre.core.events import MouseButton, MouseEvent


def test_button_detection():
    """Each button property reflects presence of the corresponding MouseButton."""
    event = MouseEvent(buttons=(MouseButton.BUTTON_LEFT, MouseButton.BUTTON_RIGHT))
    assert event.button_left is True
    assert event.button_middle is False
    assert event.button_right is True


def test_button_single_value():
    """MouseEvent.button returns the single pressed button when exactly one is set."""
    event = MouseEvent(buttons=(MouseButton.BUTTON_MIDDLE,))
    assert event.button is MouseButton.BUTTON_MIDDLE


def test_button_single_value_requires_one_button():
    """MouseEvent.button raises when 0 or 2+ buttons are set (contract)."""
    with pytest.raises(ValueError):
        _ = MouseEvent().button
    with pytest.raises(ValueError):
        _ = MouseEvent(
            buttons=(MouseButton.BUTTON_LEFT, MouseButton.BUTTON_RIGHT)
        ).button


def test_replace_returns_new_event():
    """MouseEvent is frozen ; .replace() returns a new event with the original unchanged."""
    original = MouseEvent(x=10, y=20, dx=5, dy=-3, buttons=(MouseButton.BUTTON_LEFT,))
    new = original.replace(x=100, y=200)

    assert (new.x, new.y) == (100, 200)
    assert (new.dx, new.dy, new.buttons) == (5, -3, (MouseButton.BUTTON_LEFT,))
    assert (original.x, original.y) == (10, 20)
