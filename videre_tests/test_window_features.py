"""Tests for Window features: fancybox, confirm, error, escape, notifications, repr."""

from types import SimpleNamespace

import videre
from videre.windowing.fancyclosebutton import FancyCloseButton

# --- repr and background ---


def test_window_repr(fake_win):
    r = repr(fake_win)
    assert "FakeWindow" in r


def test_window_background_property(fake_win):
    bg = fake_win.background
    assert bg is not None


# --- confirm ---


def test_confirm(fake_win, fake_user):
    data = SimpleNamespace(confirmed=False)

    def on_confirm():
        data.confirmed = True

    fake_win.confirm("Are you sure?", title="Confirm", on_confirm=on_confirm)
    fake_win.render()

    assert fake_win.has_fancybox()
    (_,) = fake_win.find(videre.Text, text="Are you sure?")

    # Click the confirm button (FancyCloseButton with title text)
    confirm_buttons = fake_win.find(FancyCloseButton, text="Confirm")
    assert len(confirm_buttons) == 1
    fake_user.click(confirm_buttons[0])
    fake_win.render()

    assert data.confirmed is True
    assert not fake_win.has_fancybox()


# --- error ---


def test_error(fake_win):
    fake_win.error(ValueError("something broke"))
    fake_win.render()

    assert fake_win.has_fancybox()
    (_,) = fake_win.find(videre.Text, text="ValueError: something broke")


# --- set_fancybox with existing focus ---


def test_set_fancybox_clears_focus(fake_win, fake_user):
    ti = videre.TextInput(text="hello")
    fake_win.controls = [ti]
    fake_win.render()

    # Give focus
    fake_user.click(ti)
    fake_win.render()
    assert fake_win._event_manager._focus is ti

    # Open fancybox should clear focus
    fake_win.set_fancybox(videre.Text("content"), title="box")
    fake_win.render()

    assert fake_win.has_fancybox()


# --- escape handling ---


def test_escape_closes_fancybox(fake_win, fake_user):
    fake_win.alert("message")
    fake_win.render()
    assert fake_win.has_fancybox()

    fake_user.keyboard_entry("escape")
    fake_win.render()

    assert not fake_win.has_fancybox()


def test_escape_closes_context(fake_win, fake_user):
    from videre.widgets.context_button import ContextButton

    cb = ContextButton("Menu", actions=[("Action", None)])  # ty: ignore[invalid-argument-type]
    fake_win.controls = [cb]
    fake_win.render()

    # Open context
    fake_user.click(cb)
    fake_win.render()
    assert fake_win.has_context()

    # Click elsewhere so focus leaves the context button (so keydown goes to window)
    # Actually, escape without focus goes through the window's _on_keydown else branch
    fake_win._event_manager._focus = None
    fake_user.keyboard_entry("escape")
    fake_win.render()

    assert not fake_win.has_context()


# --- notification callbacks ---


def test_remove_notification_callback(fake_win):
    called = []

    def cb(n):
        called.append(n)

    fake_win.add_notification_callback(cb)
    assert len(fake_win._notification_callbacks) == 1

    fake_win.remove_notification_callback(cb)
    assert len(fake_win._notification_callbacks) == 0

    # Remove again (no-op)
    fake_win.remove_notification_callback(cb)
    assert len(fake_win._notification_callbacks) == 0


def test_clear_notification_callbacks(fake_win):
    fake_win.add_notification_callback(lambda n: None)
    fake_win.add_notification_callback(lambda n: None)
    assert len(fake_win._notification_callbacks) == 2

    fake_win.clear_notification_callbacks()
    assert len(fake_win._notification_callbacks) == 0


# --- force_quit with alert_on_exceptions ---


def test_force_alert_on_handled_exception(fake_user):
    from videre.testing.step_window import StepWindow

    def raise_value_error():
        raise ValueError("test error")

    with StepWindow(alert_on_exceptions=[ValueError]) as win:
        win.controls = [videre.Text("hello")]
        win.render()

        # Simulate a call that raises a handled exception
        win.call_later(raise_value_error)
        win.render()  # pushes callback to queue
        win.render()  # executes callback, _force_alert posts another callback
        win.render()  # executes error() callback which opens fancybox

        # Should show error fancybox instead of quitting
        assert win.has_fancybox()
        assert win._is_running()
        assert win._exit_code == 0
