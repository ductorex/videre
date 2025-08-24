import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame
import pytest

from videre.core.constants import MouseButton
from videre.core.events import CustomEvents, KeyboardEntry, MouseEvent
from videre.widgets.widget import Widget
from videre.windowing.window import Window


@pytest.fixture
def mock_layout_get_mouse_owner():
    with patch("videre.windowing.window.WindowLayout.get_mouse_owner") as mock:
        yield mock


@pytest.fixture
def mock_layout_get_mouse_wheel_owner():
    with patch("videre.windowing.window.WindowLayout.get_mouse_wheel_owner") as mock:
        yield mock


@pytest.fixture
def mock_get_pos():
    with patch("pygame.mouse.get_pos") as mock:
        mock.return_value = (100, 200)
        yield mock


@pytest.fixture
def mock_get_mods():
    with patch("pygame.key.get_mods") as mock:
        yield mock


class MockWidget(Widget):
    """Mock widget for testing window event handling"""

    def __init__(self):
        super().__init__()
        self.events_received = []

    def handle_mouse_wheel(self, dx, dy, shift):
        self.events_received.append(("mouse_wheel", dx, dy, shift))
        return True

    def handle_text_input(self, text):
        self.events_received.append(("text_input", text))
        return True

    def handle_keydown(self, entry):
        self.events_received.append(("keydown", entry))
        return True

    def handle_focus_out(self):
        self.events_received.append(("focus_out",))


class Events:
    wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, x=1, y=-2)
    mouse_down_event = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, pos=(100, 200), button=1
    )
    mouse_up_event = pygame.event.Event(pygame.MOUSEBUTTONUP, pos=(150, 250), button=1)
    mouse_motion_event = pygame.event.Event(
        pygame.MOUSEMOTION, pos=(100, 150), rel=(5, 3), buttons=(0, 0, 0)
    )
    mouse_motion_event_pressed = pygame.event.Event(
        pygame.MOUSEMOTION, pos=(100, 150), rel=(5, 3), buttons=(1, 0, 0)
    )
    window_leave_event = pygame.event.Event(pygame.WINDOWLEAVE)
    text_input_event = pygame.event.Event(pygame.TEXTINPUT, text="Hello")
    keydown_event = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_SPACE, mod=0, unicode=" "
    )


class TestWindowEvents:
    """Test suite for Window event handling methods"""

    def setup_method(self):
        """Setup for each test method"""
        # Mock pygame to avoid actual window creation
        self.pygame_patches = [
            patch("pygame.display.set_mode"),
            patch("pygame.display.set_caption"),
            patch("pygame.key.set_repeat"),
            patch("pygame.mouse.get_cursor"),
            patch("pygame.cursors.compile"),
            patch("pygame.display.flip"),
        ]

        for p in self.pygame_patches:
            p.start()

        # Create window without actually initializing display
        self.window = Window(title="Test", width=800, height=600, hide=True)
        self.window._screen = MagicMock()  # Mock the screen

        self.mock_widget = MockWidget()
        self.mock_ownership = MagicMock()
        self.mock_ownership.widget = self.mock_widget
        self.mock_ownership.x_in_parent = 50
        self.mock_ownership.y_in_parent = 75

    def teardown_method(self):
        """Cleanup after each test method"""
        for p in self.pygame_patches:
            p.stop()

    def test_on_quit(self):
        """Test _on_quit event handler"""
        assert self.window._running is True

        quit_event = pygame.event.Event(pygame.QUIT)
        self.window._on_quit(quit_event)

        assert self.window._running is False

    def test_on_mouse_wheel_with_owner(
        self, mock_get_mods, mock_get_pos, mock_layout_get_mouse_wheel_owner
    ):
        """Test _on_mouse_wheel with widget owner"""
        # Setup mocks
        mock_get_mods.return_value = 0  # No shift

        # Mock layout to return ownership
        mock_layout_get_mouse_wheel_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_wheel(Events.wheel_event)

        # Verify
        self.window._layout.get_mouse_wheel_owner.assert_called_once_with(100, 200)
        assert len(self.mock_widget.events_received) == 1
        assert self.mock_widget.events_received[0] == ("mouse_wheel", 1, -2, False)

    def test_on_mouse_wheel_with_shift(
        self, mock_get_mods, mock_get_pos, mock_layout_get_mouse_wheel_owner
    ):
        """Test _on_mouse_wheel with shift key pressed"""
        # Setup mocks
        mock_get_mods.return_value = pygame.KMOD_SHIFT

        # Mock layout to return ownership
        mock_layout_get_mouse_wheel_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_wheel(Events.wheel_event)

        # Verify shift was detected
        assert self.mock_widget.events_received[0] == ("mouse_wheel", 1, -2, True)

    def test_on_mouse_wheel_no_owner(
        self, mock_get_pos, mock_layout_get_mouse_wheel_owner
    ):
        """Test _on_mouse_wheel with no widget owner"""

        # Mock layout to return no ownership
        mock_layout_get_mouse_wheel_owner.return_value = None

        # Test (should not raise exception)
        self.window._on_mouse_wheel(Events.wheel_event)

        # Verify layout was called but no further processing
        self.window._layout.get_mouse_wheel_owner.assert_called_once_with(100, 200)

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_down")
    @patch("videre.windowing.event_propagator.EventPropagator.handle_focus_in")
    def test_on_mouse_button_down(
        self, mock_handle_focus, mock_handle_mouse_down, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_button_down event handler"""

        # Mock layout
        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Mock EventPropagator
        mock_focus_widget = MockWidget()
        mock_handle_focus.return_value = mock_focus_widget

        # Test
        self.window._on_mouse_button_down(Events.mouse_down_event)

        # Verify mouse down handling
        self.window._layout.get_mouse_owner.assert_called_once_with(100, 200)
        mock_handle_mouse_down.assert_called_once()

        # Verify mouse down was registered
        assert self.window._down[MouseButton.BUTTON_LEFT] is self.mock_widget

        # Verify focus handling
        mock_handle_focus.assert_called_once_with(self.mock_widget)
        assert self.window._focus is mock_focus_widget

    @patch("videre.windowing.event_propagator.EventPropagator.handle_focus_in")
    def test_on_mouse_button_down_focus_change(
        self, mock_handle_focus, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_button_down with focus change"""
        # Setup initial focus
        old_focus = MockWidget()
        self.window._focus = old_focus

        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # New focus widget
        new_focus = MockWidget()
        mock_handle_focus.return_value = new_focus

        # Test
        self.window._on_mouse_button_down(Events.mouse_down_event)

        # Verify old focus lost focus
        assert len(old_focus.events_received) == 1
        assert old_focus.events_received[0] == ("focus_out",)

        # Verify new focus is set
        assert self.window._focus is new_focus

    def test_on_mouse_button_down_no_owner(self, mock_layout_get_mouse_owner):
        """Test _on_mouse_button_down with no widget owner"""
        # Mock layout to return no ownership
        mock_layout_get_mouse_owner.return_value = None

        # Test (should not raise exception)
        self.window._on_mouse_button_down(Events.mouse_down_event)

        # Verify layout was called but no widget registered
        self.window._layout.get_mouse_owner.assert_called_once_with(100, 200)
        assert self.window._down[MouseButton.BUTTON_LEFT] is None

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_up")
    @patch("videre.windowing.event_propagator.EventPropagator.handle_click")
    def test_on_mouse_button_up_with_click(
        self, mock_handle_click, mock_handle_mouse_up, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_button_up with successful click"""

        # Set widget as pressed down
        self.window._down[MouseButton.BUTTON_LEFT] = self.mock_widget

        # Mock layout
        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_button_up(Events.mouse_up_event)

        # Verify mouse up and click were handled
        mock_handle_mouse_up.assert_called_once()
        mock_handle_click.assert_called_once_with(
            self.mock_widget, MouseButton.BUTTON_LEFT
        )

        # Verify button state cleared
        assert self.window._down[MouseButton.BUTTON_LEFT] is None

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_up")
    @patch(
        "videre.windowing.event_propagator.EventPropagator.handle_mouse_down_canceled"
    )
    def test_on_mouse_button_up_different_widget(
        self, mock_handle_canceled, mock_handle_mouse_up, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_button_up on different widget than mouse down"""
        # Setup widgets
        down_widget = MockWidget()

        # Set different widget as pressed down
        self.window._down[MouseButton.BUTTON_LEFT] = down_widget

        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_button_up(Events.mouse_up_event)

        # Verify mouse up was handled
        mock_handle_mouse_up.assert_called_once()

        # Verify mouse down was canceled on original widget
        mock_handle_canceled.assert_called_once_with(
            down_widget, MouseButton.BUTTON_LEFT
        )

        # Verify button state cleared
        assert self.window._down[MouseButton.BUTTON_LEFT] is None

    @patch(
        "videre.windowing.event_propagator.EventPropagator.handle_mouse_down_canceled"
    )
    def test_on_mouse_button_up_no_owner(
        self, mock_handle_canceled, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_button_up with no widget owner but button was down"""
        # Setup widget as pressed down
        down_widget = MockWidget()
        self.window._down[MouseButton.BUTTON_LEFT] = down_widget

        # Mock layout to return no ownership
        mock_layout_get_mouse_owner.return_value = None

        # Test
        self.window._on_mouse_button_up(Events.mouse_up_event)

        mock_layout_get_mouse_owner.assert_called_once()
        # Verify mouse down was canceled
        mock_handle_canceled.assert_called_once_with(
            down_widget, MouseButton.BUTTON_LEFT
        )

        # Verify button state cleared
        assert self.window._down[MouseButton.BUTTON_LEFT] is None

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_enter")
    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_over")
    @patch("videre.windowing.event_propagator.EventPropagator.manage_mouse_motion")
    def test_on_mouse_motion_first_enter(
        self,
        mock_manage_motion,
        mock_handle_over,
        mock_handle_enter,
        mock_layout_get_mouse_owner,
    ):
        """Test _on_mouse_motion with first mouse enter"""

        # No previous motion widget
        self.window._motion = None

        # Mock layout
        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_motion(Events.mouse_motion_event)

        # Verify mouse enter was called
        mock_handle_enter.assert_called_once()
        mock_handle_over.assert_not_called()
        mock_manage_motion.assert_not_called()

        # Verify motion widget is set
        assert self.window._motion is self.mock_widget

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_over")
    def test_on_mouse_motion_same_widget(
        self, mock_handle_over, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_motion on same widget"""

        # Set as current motion widget
        self.window._motion = self.mock_widget

        # Mock layout
        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_motion(Events.mouse_motion_event)

        # Verify mouse over was called
        mock_handle_over.assert_called_once()

        # Verify motion widget stays the same
        assert self.window._motion is self.mock_widget

    @patch("videre.windowing.event_propagator.EventPropagator.manage_mouse_motion")
    def test_on_mouse_motion_different_widget(
        self, mock_manage_motion, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_motion on different widget"""
        # Setup widgets
        old_widget = MockWidget()
        new_widget = self.mock_widget

        # Set old widget as motion
        self.window._motion = old_widget

        # Mock layout
        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Create event
        mouse_motion_event = Events.mouse_motion_event

        # Test
        self.window._on_mouse_motion(mouse_motion_event)

        # Verify manage_mouse_motion was called
        mock_manage_motion.assert_called_once_with(
            mouse_motion_event, self.mock_ownership, old_widget
        )

        # Verify motion widget is updated
        assert self.window._motion is new_widget

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_exit")
    def test_on_mouse_motion_no_owner(
        self, mock_handle_exit, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_motion with no owner but previous motion"""
        # Setup previous motion widget
        old_widget = MockWidget()
        self.window._motion = old_widget

        # Mock layout to return no ownership
        mock_layout_get_mouse_owner.return_value = None

        # Test
        self.window._on_mouse_motion(Events.mouse_motion_event)

        # Verify mouse exit was called
        mock_handle_exit.assert_called_once_with(old_widget)

        # Verify motion widget is cleared
        assert self.window._motion is None

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_down_move")
    def test_on_mouse_motion_with_button_down(
        self, mock_handle_move, mock_layout_get_mouse_owner
    ):
        """Test _on_mouse_motion with button pressed down"""
        # Setup widgets
        motion_widget = self.mock_widget
        down_widget = MockWidget()

        # Set up motion and down states
        self.window._motion = motion_widget
        self.window._down[MouseButton.BUTTON_LEFT] = down_widget

        # Mock layout
        mock_layout_get_mouse_owner.return_value = self.mock_ownership

        # Test
        self.window._on_mouse_motion(Events.mouse_motion_event_pressed)

        # Verify mouse down move was called
        mock_handle_move.assert_called_once()
        args = mock_handle_move.call_args[0]
        assert args[0] is down_widget
        assert isinstance(args[1], MouseEvent)
        assert self.window._motion is motion_widget

    @patch("videre.windowing.event_propagator.EventPropagator.handle_mouse_exit")
    def test_on_window_leave(self, mock_handle_exit):
        """Test _on_window_leave event handler"""
        # Setup motion widget
        motion_widget = MockWidget()
        self.window._motion = motion_widget

        # Test
        self.window._on_window_leave(Events.window_leave_event)

        # Verify mouse exit was called
        mock_handle_exit.assert_called_once_with(motion_widget)

        # Verify motion is cleared
        assert self.window._motion is None

    def test_on_window_leave_no_motion(self):
        """Test _on_window_leave with no motion widget"""
        # No motion widget
        self.window._motion = None

        # Test (should not raise exception)
        self.window._on_window_leave(Events.window_leave_event)

        # Motion should still be None
        assert self.window._motion is None

    def test_on_window_resized(self):
        """Test _on_window_resized event handler"""
        # Original size
        assert self.window._width == 800
        assert self.window._height == 600

        # Create resize event
        resize_event = pygame.event.Event(pygame.WINDOWRESIZED, x=1024, y=768)

        # Test
        self.window._on_window_resized(resize_event)

        # Verify size was updated
        assert self.window._width == 1024
        assert self.window._height == 768

    def test_on_text_input_with_focus(self):
        """Test _on_text_input with focused widget"""
        # Setup focused widget
        focus_widget = MockWidget()
        self.window._focus = focus_widget

        # Test
        self.window._on_text_input(Events.text_input_event)

        # Verify text input was handled
        assert len(focus_widget.events_received) == 1
        assert focus_widget.events_received[0] == ("text_input", "Hello")

    def test_on_text_input_no_focus(self):
        """Test _on_text_input with no focused widget"""
        # No focus widget
        self.window._focus = None

        # Test (should not raise exception)
        self.window._on_text_input(Events.text_input_event)

        # No widget should receive the event
        # (This is verified by not crashing)

    def test_on_keydown_with_focus(self):
        """Test _on_keydown with focused widget"""
        # Setup focused widget
        focus_widget = MockWidget()
        self.window._focus = focus_widget

        # Test
        self.window._on_keydown(Events.keydown_event)

        # Verify keydown was handled
        assert len(focus_widget.events_received) == 1
        event_name, keyboard_entry = focus_widget.events_received[0]
        assert event_name == "keydown"
        assert isinstance(keyboard_entry, KeyboardEntry)

    def test_on_keydown_no_focus(self):
        """Test _on_keydown with no focused widget"""
        # No focus widget
        self.window._focus = None

        # Test (should not raise exception)
        self.window._on_keydown(Events.keydown_event)

    def test_on_custom_callback(self):
        """Test _on_custom_callback event handler"""
        # Setup callback data
        callback_data = SimpleNamespace(called=False, args=None, kwargs=None)

        def test_callback(*args, **kwargs):
            callback_data.called = True
            callback_data.args = args
            callback_data.kwargs = kwargs

        # Create custom callback event
        callback_event = CustomEvents.callback_event(
            test_callback, "arg1", "arg2", key="value"
        )

        # Test
        self.window._on_custom_callback(callback_event)

        # Verify callback was executed
        assert callback_data.called is True
        assert callback_data.args == ("arg1", "arg2")
        assert callback_data.kwargs == {"key": "value"}

    def test_on_notification(self):
        """Test _on_notification event handler with callback set"""
        # Setup notification callback
        notification_data = SimpleNamespace(received=None)

        def notification_callback(notification):
            notification_data.received = notification

        self.window.set_notification_callback(notification_callback)

        # Create notification event
        notification_event = CustomEvents.notification_event("Test notification")

        # Test
        self.window._on_notification(notification_event)

        # Verify notification was handled
        assert notification_data.received == "Test notification"

    def test_on_notification_no_callback(self):
        """Test _on_notification event handler with no callback set"""
        # No notification callback set
        assert self.window._notification_callback is None

        # Create notification event
        notification_event = CustomEvents.notification_event("Test notification")

        # Test (should not raise exception)
        self.window._on_notification(notification_event)

    def test_post_event(self):
        """Test _post_event method"""
        # Create test event
        test_event = pygame.event.Event(pygame.USEREVENT, data="test")

        # Test
        self.window._post_event(test_event)

        # Verify event was added to manual events
        with self.window._lock:
            assert len(self.window._manual_events_after) == 1
            assert self.window._manual_events_after[0] is test_event

    @patch("videre.windowing.window.Window._post_event")
    def test_run_later_method(self, mock_post):
        """Test run_later method creates callback event"""

        def test_func(a, b, key=None):
            pass

        # Test
        self.window.run_later(test_func, "arg1", "arg2", key="value")

        # Verify callback event was posted
        mock_post.assert_called_once()
        event = mock_post.call_args[0][0]
        assert event.type == CustomEvents.CALLBACK_EVENT
        assert event.function.__name__ == "test_func"
        assert event.args == ("arg1", "arg2")
        assert event.kwargs == {"key": "value"}

    def test_thread_safety_of_post_event(self):
        """Test thread safety of _post_event method"""
        # Create multiple threads that post events
        events_posted = []

        def post_events():
            for i in range(10):
                event = pygame.event.Event(
                    pygame.USEREVENT,
                    data=f"event_{threading.current_thread().ident}_{i}",
                )
                self.window._post_event(event)
                events_posted.append(event)
                time.sleep(0.001)  # Small delay to encourage race conditions

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=post_events)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all events were posted safely
        with self.window._lock:
            assert (
                len(self.window._manual_events_after) == 30
            )  # 3 threads * 10 events each

        # Verify no events were lost or corrupted
        assert len(events_posted) == 30

    def test_window_default_mouse_over_no(self, fake_win, mock_layout_get_mouse_owner):
        with patch("pygame.mouse.get_focused") as mock_get_focused:
            mock_get_focused.return_value = False
            fake_win.render()
            mock_layout_get_mouse_owner.assert_not_called()

    def test_window_default_mouse_over(self, fake_win, mock_layout_get_mouse_owner):
        with patch("pygame.mouse.get_focused") as mock_get_focused:
            mock_get_focused.return_value = True
            fake_win.render()
            mock_layout_get_mouse_owner.assert_called_once_with(0, 0)


def test_run_async(fake_win):
    data = SimpleNamespace(value=1)

    def function(a, b):
        data.value += a * b
        function.called += 1

    function.called = 0

    fake_win.run_async(function, 6, 7)
    # This render() will push call event into manual events queue
    fake_win.render()
    # This render() will handle manual events queue
    fake_win.render()
    # Let's wait a little, to let thread run.
    time.sleep(0.25)
    assert function.called == 1
    assert data.value == 43
    assert fake_win._exit_code == 0


def test_run_async_with_error(fake_win):
    data = SimpleNamespace(value=1)

    def function(a, b):
        function.called += 1
        raise Exception("function error")
        data.value += a * b

    function.called = 0

    fake_win.run_async(function, 6, 7)
    # This render() will push call event into manual events queue
    fake_win.render()
    # This render() will handle manual events queue
    fake_win.render()
    # Let's wait a little, to let thread run.
    time.sleep(0.25)
    assert function.called == 1
    assert data.value == 1
    assert fake_win._exit_code == -1
