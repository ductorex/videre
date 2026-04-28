from types import SimpleNamespace

import pytest

import videre


@pytest.mark.parametrize("checked", [False, True])
def test_checkbox_unchecked(snap_win, checked):
    checkbox = videre.Checkbox(checked=checked)
    snap_win.controls = [checkbox]


def test_checkbox_toggle(fake_win, fake_user):
    data = SimpleNamespace(value=0, checkbox=None)

    def on_change(checkbox):
        data.value += 1
        data.checkbox = checkbox

    checkbox = videre.Checkbox(checked=False, on_change=on_change)
    fake_win.controls = [checkbox]
    fake_win.render()

    assert checkbox.on_change is on_change
    assert checkbox.checked is False
    assert data.value == 0

    # Click to check
    fake_user.click(checkbox)
    fake_win.render()

    assert checkbox.checked is True
    assert data.value == 1
    assert data.checkbox is checkbox

    # Click to uncheck
    fake_user.click(checkbox)
    fake_win.render()

    assert checkbox.checked is False
    assert data.value == 2
    assert data.checkbox is checkbox


def test_checkbox_set_checked_property(fake_win):
    data = SimpleNamespace(value=0)

    def on_change(checkbox):
        data.value += 1

    checkbox = videre.Checkbox(checked=False, on_change=on_change)
    fake_win.controls = [checkbox]
    fake_win.render()

    assert checkbox.checked is False
    assert data.value == 0

    # Set checked programmatically
    checkbox.checked = True
    fake_win.render()

    assert checkbox.checked is True
    assert data.value == 1


def test_checkbox_change_callback(fake_win, fake_user):
    data = SimpleNamespace(value=0)

    def on_change1(checkbox):
        data.value += 10

    def on_change2(checkbox):
        data.value += 100

    checkbox = videre.Checkbox(checked=False, on_change=on_change1)
    fake_win.controls = [checkbox]
    fake_win.render()

    fake_user.click(checkbox)
    fake_win.render()
    assert data.value == 10

    # Change callback
    checkbox.on_change = on_change2
    fake_win.render()

    fake_user.click(checkbox)
    fake_win.render()
    assert data.value == 110
