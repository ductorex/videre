import pytest

import videre
from videre.widgets.dropdown import _OptionWidget


def test_dropdown_display(snap_win):
    dropdown = videre.Dropdown(options=["Apple", "Banana", "Cherry"])
    snap_win.controls = [dropdown]


def test_dropdown_selection(fake_win):
    dropdown = videre.Dropdown(options=["Apple", "Banana", "Cherry"])
    fake_win.controls = [dropdown]
    fake_win.render()

    assert dropdown.index == 0
    assert dropdown.selected == "Apple"

    # Test index property
    dropdown.index = 1
    fake_win.render()
    assert dropdown.index == 1
    assert dropdown.selected == "Banana"

    # Test bounds checking - too high
    dropdown.index = 10
    fake_win.render()
    assert dropdown.index == 2  # Clamped to max index
    assert dropdown.selected == "Cherry"

    # Test bounds checking - too low
    dropdown.index = -5
    fake_win.render()
    assert dropdown.index == 0  # Clamped to min index
    assert dropdown.selected == "Apple"


def test_dropdown_options_change(fake_win):
    dropdown = videre.Dropdown(options=["A", "B"])
    fake_win.controls = [dropdown]
    fake_win.render()

    dropdown.index = 1
    fake_win.render()
    assert dropdown.selected == "B"

    # Change options - should reset index to 0
    dropdown.options = ["X", "Y", "Z"]
    fake_win.render()
    assert dropdown.index == 0
    assert dropdown.selected == "X"
    assert dropdown.options == ("X", "Y", "Z")


def test_dropdown_click_opens_context(fake_win, fake_user):
    dropdown = videre.Dropdown(options=["Apple", "Banana", "Cherry"])
    fake_win.controls = [dropdown]
    fake_win.check("default")

    # Initially no context
    assert dropdown._context is None

    # Click to open context
    fake_user.click(dropdown)
    fake_win.check("opened")

    # Context should be created
    assert dropdown._context is not None
    assert len(dropdown._context.controls) == 3

    # Click again to close context
    fake_user.click(dropdown)
    fake_win.check("default")

    # Context should be closed
    assert dropdown._context is None


def test_dropdown_focus_behavior(fake_win, fake_user):
    dropdown = videre.Dropdown(options=["Apple", "Banana", "Cherry"])
    fake_win.controls = [dropdown]
    fake_win.render()

    # Open context
    fake_user.click(dropdown)
    fake_win.render()
    assert dropdown._context is not None

    # Simulate focus out
    dropdown.handle_focus_out()
    fake_win.render()

    # Context should be closed
    assert dropdown._context is None


def test_dropdown_click_to_option(fake_win, fake_user):
    dropdown = videre.Dropdown(options=["Apple", "Banana", "Cherry"])
    fake_win.controls = [dropdown]
    fake_win.render()
    assert dropdown._context is None

    fake_user.click(dropdown)
    fake_win.render()
    assert dropdown._context is not None
    assert dropdown.selected == "Apple"
    (option,) = dropdown._context.collect_matches(
        lambda widget: isinstance(widget, _OptionWidget) and widget._index == 1
    )
    assert dropdown.options[option._index] == "Banana"

    fake_user.click(option)
    fake_win.render()

    assert dropdown._context is None
    assert dropdown.selected == "Banana"


def test_dropdown_click_outer(fake_win, fake_user):
    dropdown = videre.Dropdown(options=["Apple", "Banana", "Cherry"])
    fake_win.controls = [dropdown]
    fake_win.render()

    # Open context
    fake_user.click(dropdown)
    fake_win.render()
    assert dropdown._context is not None

    # click outside to close context
    fake_user.click_at(fake_win.width - 1, fake_win.height - 1)
    fake_win.render()

    # Context should be closed
    assert dropdown._context is None


def test_dropdown_empty_options():
    with pytest.raises(AssertionError):
        videre.Dropdown(options=[])
