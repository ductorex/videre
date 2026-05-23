import threading
import time
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from videre.core.events import Key, KeyboardEntry, MouseButton
from videre.core.pygame_backend.definitions import Event
from videre.core.pygame_backend.primitives import Pygame
from videre.core.tasks import CallbackTask, NotificationTask
from videre.layouts.column import Column
from videre.widgets.widget import Widget


class TrackerWidget(Widget):
    """Widget that tracks received events for testing."""

    __slots__ = ("events",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = []

    def draw(self, window, width=None, height=None):
        surface = Pygame.new_surface(width or 50, height or 50)
        surface.fill((200, 200, 200))
        return surface

    def handle_mouse_wheel(self, x, y, shift):
        self.events.append(("mouse_wheel", x, y, shift))
        return True

    def handle_text_input(self, text):
        self.events.append(("text_input", text))
        return True

    def handle_keydown(self, key: KeyboardEntry):
        self.events.append(("keydown", key))
        return self

    def handle_focus_in(self):
        self.events.append(("focus_in",))
        return self

    def handle_focus_out(self):
        self.events.append(("focus_out",))

    def handle_click(self, button):
        self.events.append(("click", button))
        return self

    def handle_mouse_enter(self, event):
        self.events.append(("mouse_enter",))
        return self

    def handle_mouse_over(self, event):
        self.events.append(("mouse_over",))
        return self

    def handle_mouse_exit(self):
        self.events.append(("mouse_exit",))
        return self

    def handle_mouse_down(self, event):
        self.events.append(("mouse_down",))
        return self

    def handle_mouse_up(self, event):
        self.events.append(("mouse_up",))
        return self

    def handle_mouse_down_move(self, event):
        self.events.append(("mouse_down_move",))
        return self

    def handle_mouse_down_canceled(self, button):
        self.events.append(("mouse_down_canceled", button))
        return self


# --- Quit ---


def test_on_quit(fake_win):
    fake_user = fake_win.user
    assert fake_win._is_running()
    fake_user.quit()
    fake_win.render()
    assert not fake_win._is_running()


# --- Mouse wheel ---


def test_on_mouse_wheel_with_owner(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()
    fake_user.mouse_wheel(x=1, y=-2)
    fake_win.render()
    assert ("mouse_wheel", 1, -2, False) in tracker.events


def test_on_mouse_wheel_with_shift(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()
    fake_user.mouse_wheel(x=1, y=-2, shift=True)
    fake_win.render()
    assert ("mouse_wheel", 1, -2, True) in tracker.events


def test_on_mouse_wheel_no_owner(fake_win):
    fake_user = fake_win.user
    fake_win.render()
    fake_user.mouse_wheel(x=1, y=-2)
    fake_win.render()  # should not raise


# --- Mouse button down ---


def test_on_mouse_button_down(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    x = tracker.global_x + 5
    y = tracker.global_y + 5
    fake_user.mouse_down(x, y)
    fake_win.render()

    assert ("mouse_down",) in tracker.events
    assert ("focus_in",) in tracker.events
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is tracker
    assert fake_win._event_manager._focus is tracker


def test_on_mouse_button_down_focus_change(fake_win):
    fake_user = fake_win.user
    tracker1 = TrackerWidget()
    tracker2 = TrackerWidget()
    fake_win.controls = [Column([tracker1, tracker2])]
    fake_win.render()

    # Click first widget to give it focus
    fake_user.click(tracker1)
    fake_win.render()
    assert fake_win._event_manager._focus is tracker1

    # Click second widget
    fake_user.click(tracker2)
    fake_win.render()

    assert ("focus_out",) in tracker1.events
    assert fake_win._event_manager._focus is tracker2


def test_on_mouse_button_down_no_owner(fake_win):
    fake_user = fake_win.user
    fake_win.render()
    fake_user.mouse_down(5000, 5000)
    fake_win.render()
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is None


# --- Mouse button up ---


def test_on_mouse_button_up_with_click(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    fake_user.click(tracker)
    fake_win.render()

    assert ("click", MouseButton.BUTTON_LEFT) in tracker.events
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is None


def test_on_mouse_button_up_different_widget(fake_win):
    fake_user = fake_win.user
    tracker1 = TrackerWidget()
    tracker2 = TrackerWidget()
    fake_win.controls = [Column([tracker1, tracker2])]
    fake_win.render()

    # Mouse down on tracker1
    fake_user.mouse_down(tracker1.global_x + 5, tracker1.global_y + 5)
    fake_win.render()
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is tracker1

    # Mouse up on tracker2
    fake_user.mouse_up(tracker2.global_x + 5, tracker2.global_y + 5)
    fake_win.render()

    assert ("click", MouseButton.BUTTON_LEFT) not in tracker1.events
    assert ("click", MouseButton.BUTTON_LEFT) not in tracker2.events
    assert ("mouse_down_canceled", MouseButton.BUTTON_LEFT) in tracker1.events
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is None


def test_on_mouse_button_up_no_owner(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    # Mouse down on tracker
    fake_user.mouse_down(tracker.global_x + 5, tracker.global_y + 5)
    fake_win.render()
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is tracker

    # Mouse up outside window
    fake_user.mouse_up(5000, 5000)
    fake_win.render()

    assert ("mouse_down_canceled", MouseButton.BUTTON_LEFT) in tracker.events
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is None


# --- Mouse motion ---


def test_on_mouse_motion_first_enter(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()
    assert fake_win._event_manager._motion is None

    fake_user.mouse_motion(tracker.global_x + 5, tracker.global_y + 5)
    fake_win.render()

    assert ("mouse_enter",) in tracker.events
    assert fake_win._event_manager._motion is tracker


def test_on_mouse_motion_same_widget(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    x = tracker.global_x + 5
    y = tracker.global_y + 5

    # First motion - enter
    fake_user.mouse_motion(x, y)
    fake_win.render()
    assert fake_win._event_manager._motion is tracker

    # Second motion on same widget - over
    fake_user.mouse_motion(x + 1, y + 1)
    fake_win.render()

    assert ("mouse_over",) in tracker.events
    assert fake_win._event_manager._motion is tracker


def test_on_mouse_motion_different_widget(fake_win):
    fake_user = fake_win.user
    tracker1 = TrackerWidget()
    tracker2 = TrackerWidget()
    fake_win.controls = [Column([tracker1, tracker2])]
    fake_win.render()

    # Motion to tracker1
    fake_user.mouse_motion(tracker1.global_x + 5, tracker1.global_y + 5)
    fake_win.render()
    assert fake_win._event_manager._motion is tracker1

    # Motion to tracker2
    fake_user.mouse_motion(tracker2.global_x + 5, tracker2.global_y + 5)
    fake_win.render()

    assert ("mouse_enter",) in tracker2.events
    assert ("mouse_exit",) in tracker1.events
    assert fake_win._event_manager._motion is tracker2


def test_on_mouse_motion_no_owner(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    # Enter the widget
    fake_user.mouse_motion(tracker.global_x + 5, tracker.global_y + 5)
    fake_win.render()
    assert fake_win._event_manager._motion is tracker

    # Motion outside window bounds
    fake_user.mouse_motion(5000, 5000)
    fake_win.render()

    assert ("mouse_exit",) in tracker.events
    assert fake_win._event_manager._motion is None


def test_on_mouse_motion_with_button_down(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    x = tracker.global_x + 5
    y = tracker.global_y + 5

    # Enter the widget, then press button
    fake_user.mouse_motion(x, y)
    fake_win.render()
    fake_user.mouse_down(x, y)
    fake_win.render()
    assert fake_win._event_manager._down[MouseButton.BUTTON_LEFT] is tracker

    # Motion with button pressed
    fake_user.mouse_motion(x + 2, y + 2, button_left=True)
    fake_win.render()

    assert ("mouse_down_move",) in tracker.events


# --- Window leave ---


def test_on_window_leave(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    # Enter the widget
    fake_user.mouse_motion(tracker.global_x + 5, tracker.global_y + 5)
    fake_win.render()
    assert fake_win._event_manager._motion is tracker

    # Window leave
    pygame.event.post(Event(pygame.WINDOWLEAVE))
    fake_win.render()

    assert ("mouse_exit",) in tracker.events
    assert fake_win._event_manager._motion is None


def test_on_window_leave_no_motion(fake_win):
    fake_win.render()
    assert fake_win._event_manager._motion is None
    pygame.event.post(Event(pygame.WINDOWLEAVE))
    fake_win.render()
    assert fake_win._event_manager._motion is None


# --- Window resized ---


def test_on_window_resized(fake_win):
    fake_win.render()
    assert fake_win.width == 320
    assert fake_win.height == 240

    x = 1024
    y = 768
    fake_win._backend._screen = pygame.display.set_mode((x, y), pygame.RESIZABLE)
    pygame.event.post(Event(pygame.WINDOWRESIZED, x=x, y=y))
    fake_win.render()
    assert fake_win.width == x
    assert fake_win.height == y


# --- Text input ---


def test_on_text_input_with_focus(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    fake_user.click(tracker)
    fake_win.render()
    assert fake_win._event_manager._focus is tracker

    fake_user.text_input("Hello")
    fake_win.render()

    assert ("text_input", "Hello") in tracker.events


def test_on_text_input_no_focus(fake_win):
    fake_user = fake_win.user
    fake_win.render()
    assert fake_win._event_manager._focus is None
    fake_user.text_input("Hello")
    fake_win.render()  # should not raise


# --- Keydown ---


def test_on_keydown_with_focus(fake_win):
    fake_user = fake_win.user
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    fake_user.click(tracker)
    fake_win.render()
    assert fake_win._event_manager._focus is tracker

    fake_user.key_down(Key.SPACE, unicode=" ")
    fake_win.render()

    keydown_events = [e for e in tracker.events if e[0] == "keydown"]
    assert len(keydown_events) == 1
    assert isinstance(keydown_events[0][1], KeyboardEntry)


def test_on_keydown_no_focus(fake_win):
    fake_user = fake_win.user
    fake_win.render()
    assert fake_win._event_manager._focus is None
    fake_user.key_down(Key.SPACE, unicode=" ")
    fake_win.render()  # should not raise


# --- Custom callback ---


def test_on_custom_callback(fake_win):
    callback_data = SimpleNamespace(called=False, args=None, kwargs=None)

    def test_callback(*args, **kwargs):
        callback_data.called = True
        callback_data.args = args
        callback_data.kwargs = kwargs

    callback_event = CallbackTask.new(test_callback, "arg1", "arg2", key="value")
    fake_win._post_event(callback_event)
    fake_win.render()

    assert callback_data.called is True
    assert callback_data.args == ("arg1", "arg2")
    assert callback_data.kwargs == {"key": "value"}


# --- Notification ---


def test_on_notification(fake_win):
    notification_data = SimpleNamespace(received=None)

    def notification_callback(notification):
        notification_data.received = notification

    fake_win.set_notification_callback(notification_callback)
    notification_event = NotificationTask("Test notification")
    fake_win._post_event(notification_event)
    fake_win.render()

    assert notification_data.received == "Test notification"


def test_on_notification_no_callback(fake_win):
    assert not fake_win._notification_callbacks
    notification_event = NotificationTask("Test notification")
    fake_win._post_event(notification_event)
    fake_win.render()  # should not raise


# --- Post event & thread safety ---


def test_run_later_method(fake_win):
    data = SimpleNamespace(called=False, args=None, key=None)

    def test_func(a, b, key=None):
        data.called = True
        data.args = (a, b)
        data.key = key

    fake_win.call_later(test_func, "arg1", "arg2", key="value")
    # First render pushes manual events to pygame queue
    fake_win.render()
    # Second render processes the callback event
    fake_win.render()

    assert data.called is True
    assert data.args == ("arg1", "arg2")
    assert data.key == "value"


def test_thread_safety_of_post_event(fake_win):
    """Posts from multiple threads must all land in `_pending_tasks`
    without loss or corruption (the buffer is protected by `_lock`)."""
    tasks_posted = []

    def post_tasks():
        for _ in range(10):
            task = CallbackTask.new(lambda: None)
            fake_win._post_event(task)
            tasks_posted.append(task)
            time.sleep(0.001)

    threads = [threading.Thread(target=post_tasks) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with fake_win._task_manager._lock:
        assert len(fake_win._task_manager._pending_tasks) == 30
    assert len(tasks_posted) == 30


# --- Default mouse over (synthetic MOUSEMOTION) ---


def test_window_default_mouse_over_no(fake_win):
    """In headless mode, get_focused() returns False: no synthetic mouse motion."""
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()
    assert fake_win._event_manager._motion is None


def test_window_default_mouse_over(fake_win):
    """When get_focused() returns True, a synthetic MOUSEMOTION is created."""
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    with patch("pygame.mouse.get_focused", return_value=True):
        fake_win.render()

    assert fake_win._event_manager._motion is tracker


# --- Async ---


def test_run_async(fake_win):
    data = SimpleNamespace(value=1, called=0)

    def function(a, b):
        data.value += a * b
        data.called += 1

    fake_win.call_async(function, 6, 7)
    # This render() will push call event into manual events queue
    fake_win.render()
    # This render() will handle manual events queue
    fake_win.render()
    # Let's wait a little, to let thread run.
    time.sleep(0.25)
    assert data.called == 1
    assert data.value == 43
    assert fake_win._exit_code == 0


def test_run_async_with_error(fake_win):
    data = SimpleNamespace(value=1, called=0)

    def function(a, b):
        data.called += 1
        raise Exception("function error")
        data.value += a * b

    assert fake_win._exit_code == 0
    assert fake_win._exit_exception is None
    # Call task will be pushed in window tasks queue
    fake_win.call_async(function, 6, 7)
    # This render() will handle window tasks queue and launch the thread
    fake_win.render()
    # Let's wait a little, to let thread run and post its ExitTask.
    time.sleep(0.5)
    assert data.called == 1
    assert data.value == 1

    # This render() drains the ExitTask posted by the failing thread,
    # which sets _exit_exception.
    fake_win.render()

    assert fake_win._exit_code == 0
    assert fake_win._exit_exception is not None
    assert isinstance(fake_win._exit_exception, Exception)
    assert fake_win._exit_exception.args == ("function error",)
