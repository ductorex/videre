import pygame.event

from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_backend import Event
from videre.layouts.container import Container
from videre.widgets.widget import Widget
from videre.windowing.event_propagator import EventPropagator


def _pygame_mouse_motion_event(
    x, y, rel=(0, 0), button_left=False, button_middle=False, button_right=False
):
    return Event(
        pygame.MOUSEMOTION,
        pos=(x, y),
        rel=rel,
        buttons=(button_left, button_middle, button_right),
    )


class MockWidget(Widget):
    """Test widget for event propagation tests"""

    def __init__(self, parent: Widget | None = None, capture_events=True):
        super().__init__(parent=parent)
        self.capture_events = capture_events
        self.events_received = []

    def _log_event(self, event_name, *args, **kwargs):
        self.events_received.append((event_name, args, kwargs))
        return self if self.capture_events else None

    def handle_click(self, button):
        return self._log_event("click", button)

    def handle_focus_in(self):
        return self._log_event("focus_in")

    def handle_mouse_over(self, event):
        return self._log_event("mouse_over", event)

    def handle_mouse_enter(self, event):
        return self._log_event("mouse_enter", event)

    def handle_mouse_exit(self):
        return self._log_event("mouse_exit")

    def handle_mouse_down(self, event):
        return self._log_event("mouse_down", event)

    def handle_mouse_up(self, event):
        return self._log_event("mouse_up", event)

    def handle_mouse_down_move(self, event):
        return self._log_event("mouse_down_move", event)

    def handle_mouse_down_canceled(self, button):
        return self._log_event("mouse_down_canceled", button)


class TestHandlePropagation:
    """Test _handle and _handle_mouse_event core mechanics."""

    def test_event_captured(self):
        widget = MockWidget()
        result = EventPropagator._handle(
            widget, Widget.handle_click, MouseButton.BUTTON_LEFT
        )
        assert result is widget
        assert widget.events_received[0] == ("click", (MouseButton.BUTTON_LEFT,), {})

    def test_event_not_captured_no_parent(self):
        widget = MockWidget(capture_events=False)
        result = EventPropagator._handle(
            widget, Widget.handle_click, MouseButton.BUTTON_LEFT
        )
        assert result is None
        assert len(widget.events_received) == 1

    def test_propagation_to_parent(self):
        parent = MockWidget()
        child = MockWidget(parent=parent, capture_events=False)
        result = EventPropagator._handle(
            child, Widget.handle_click, MouseButton.BUTTON_LEFT
        )
        assert result is parent
        assert len(child.events_received) == 1
        assert len(parent.events_received) == 1

    def test_propagation_multiple_levels(self):
        grandparent = MockWidget()
        parent = MockWidget(parent=grandparent, capture_events=False)
        child = MockWidget(parent=parent, capture_events=False)
        result = EventPropagator._handle(
            child, Widget.handle_click, MouseButton.BUTTON_LEFT
        )
        assert result is grandparent
        assert len(child.events_received) == 1
        assert len(parent.events_received) == 1
        assert len(grandparent.events_received) == 1

    def test_mouse_event_captured(self):
        widget = MockWidget()
        event = MouseEvent(x=10, y=20)
        result = EventPropagator._handle_mouse_event(
            widget, Widget.handle_mouse_down, event
        )
        assert result is widget
        assert widget.events_received[0][1][0] is event

    def test_mouse_event_coordinate_transformation(self):
        parent = MockWidget()
        container = Container(parent)
        container._set_child_position(parent, 50, 100)
        child = MockWidget(parent=parent, capture_events=False)

        event = MouseEvent(x=10, y=20)
        result = EventPropagator._handle_mouse_event(
            child, Widget.handle_mouse_down, event
        )

        assert result is parent
        parent_event = parent.events_received[0][1][0]
        assert parent_event.x == 60  # 50 + 10
        assert parent_event.y == 120  # 100 + 20

    def test_none_widget(self):
        assert (
            EventPropagator._handle(None, Widget.handle_click, MouseButton.BUTTON_LEFT)
            is None
        )

    def test_none_widget_mouse_event(self):
        event = MouseEvent(x=10, y=20)
        assert (
            EventPropagator._handle_mouse_event(None, Widget.handle_mouse_down, event)
            is None
        )

    def test_handler_returns_custom_widget(self):
        class CustomWidget(MockWidget):
            def __init__(self, return_widget):
                super().__init__()
                self.return_widget = return_widget

            def handle_click(self, button):
                self._log_event("click", button)
                return self.return_widget

        target = MockWidget()
        widget = CustomWidget(target)
        result = EventPropagator._handle(
            widget, Widget.handle_click, MouseButton.BUTTON_LEFT
        )
        assert result is target

    def test_mouse_handler_returns_custom_widget(self):
        class CustomWidget(MockWidget):
            def __init__(self, return_widget):
                super().__init__()
                self.return_widget = return_widget

            def handle_mouse_down(self, event):
                self._log_event("mouse_down", event)
                return self.return_widget

        target = MockWidget()
        widget = CustomWidget(target)
        event = MouseEvent(x=10, y=20)
        result = EventPropagator._handle_mouse_event(
            widget, Widget.handle_mouse_down, event
        )
        assert result is target


class TestManageMouseMotion:
    """Test manage_mouse_motion with various hierarchy configurations."""

    def test_simple_enter_exit(self):
        root = MockWidget(capture_events=False)
        child = MockWidget(parent=root, capture_events=False)
        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)
        previous = MockWidget(capture_events=False)

        pygame_event = _pygame_mouse_motion_event(100, 200, rel=(5, 5))
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous)

        assert child.events_received[0][0] == "mouse_enter"
        assert root.events_received[0][0] == "mouse_enter"
        assert previous.events_received[0][0] == "mouse_exit"

    def test_capture_stops_propagation(self):
        root = MockWidget(capture_events=False)
        child = MockWidget(parent=root)  # captures

        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)
        previous = MockWidget()  # captures

        pygame_event = _pygame_mouse_motion_event(100, 200)
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous)

        assert len(child.events_received) == 1
        assert child.events_received[0][0] == "mouse_enter"
        assert len(root.events_received) == 0
        assert previous.events_received[0][0] == "mouse_exit"

    def test_overlapping_hierarchy(self):
        shared_parent = MockWidget(capture_events=False)
        current_child = MockWidget(parent=shared_parent, capture_events=False)
        previous_child = MockWidget(parent=shared_parent, capture_events=False)

        ownership = MouseOwnership(widget=current_child, x_in_parent=10, y_in_parent=20)
        pygame_event = _pygame_mouse_motion_event(100, 200)
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous_child)

        assert current_child.events_received[0][0] == "mouse_enter"
        assert shared_parent.events_received[0][0] == "mouse_over"
        assert previous_child.events_received[0][0] == "mouse_exit"

    def test_overlapping_hierarchy_capture_on_shared_parent(self):
        """Shared parent captures mouse_over, stopping propagation."""
        shared_parent = MockWidget(capture_events=True)
        current_child = MockWidget(parent=shared_parent, capture_events=False)
        previous_child = MockWidget(parent=shared_parent, capture_events=False)

        ownership = MouseOwnership(widget=current_child, x_in_parent=10, y_in_parent=20)
        pygame_event = _pygame_mouse_motion_event(100, 200)
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous_child)

        assert current_child.events_received[0][0] == "mouse_enter"
        # Shared parent captures mouse_over -> break
        assert shared_parent.events_received[0][0] == "mouse_over"
        assert previous_child.events_received[0][0] == "mouse_exit"

    def test_coordinate_transformation(self):
        root = MockWidget(capture_events=False)
        container = Container(root)
        container._set_child_position(root, 100, 200)

        parent = MockWidget(parent=root, capture_events=False)
        root._set_child_position(parent, 50, 75)

        child = MockWidget(parent=parent, capture_events=False)

        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)
        previous = MockWidget(capture_events=False)

        pygame_event = _pygame_mouse_motion_event(300, 400)
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous)

        child_event = child.events_received[0][1][0]
        assert child_event.x == 10
        assert child_event.y == 20

        parent_event = parent.events_received[0][1][0]
        assert parent_event.x == 60  # 50 + 10
        assert parent_event.y == 95  # 75 + 20

        root_event = root.events_received[0][1][0]
        assert root_event.x == 160  # 100 + 60
        assert root_event.y == 295  # 200 + 95
