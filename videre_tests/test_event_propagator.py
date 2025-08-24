import pygame.event

from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.layouts.container import Container
from videre.widgets.widget import Widget
from videre.windowing.event_propagator import EventPropagator


def _pygame_mouse_motion_event(
    x, y, rel=(0, 0), button_left=False, button_middle=False, button_right=False
):
    return pygame.event.Event(
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
        return self.capture_events

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


class TestEventPropagator:
    """Test suite for EventPropagator class"""

    def test_handle_simple_event_captured(self):
        """Test _handle with event captured by widget"""
        widget = MockWidget()

        result = EventPropagator._handle(
            widget, "handle_click", MouseButton.BUTTON_LEFT
        )

        assert result is widget
        assert len(widget.events_received) == 1
        assert widget.events_received[0] == ("click", (MouseButton.BUTTON_LEFT,), {})

    def test_handle_simple_event_not_captured(self):
        """Test _handle with event not captured, no parent"""
        widget = MockWidget(capture_events=False)

        result = EventPropagator._handle(
            widget, "handle_click", MouseButton.BUTTON_LEFT
        )

        assert result is None
        assert len(widget.events_received) == 1
        assert widget.events_received[0] == ("click", (MouseButton.BUTTON_LEFT,), {})

    def test_handle_event_propagation_to_parent(self):
        """Test _handle with event propagation to parent"""
        parent = MockWidget()
        child = MockWidget(parent=parent, capture_events=False)

        result = EventPropagator._handle(child, "handle_click", MouseButton.BUTTON_LEFT)

        assert result is parent
        assert len(child.events_received) == 1
        assert len(parent.events_received) == 1
        assert child.events_received[0] == ("click", (MouseButton.BUTTON_LEFT,), {})
        assert parent.events_received[0] == ("click", (MouseButton.BUTTON_LEFT,), {})

    def test_handle_event_propagation_multiple_levels(self):
        """Test _handle with event propagation through multiple levels"""
        grandparent = MockWidget()
        parent = MockWidget(parent=grandparent, capture_events=False)
        child = MockWidget(parent=parent, capture_events=False)

        result = EventPropagator._handle(child, "handle_click", MouseButton.BUTTON_LEFT)

        assert result is grandparent
        assert len(child.events_received) == 1
        assert len(parent.events_received) == 1
        assert len(grandparent.events_received) == 1

    def test_handle_mouse_event_captured(self):
        """Test _handle_mouse_event with event captured"""
        widget = MockWidget()
        event = MouseEvent(x=10, y=20)

        result = EventPropagator._handle_mouse_event(widget, "handle_mouse_down", event)

        assert result is widget
        assert len(widget.events_received) == 1
        assert widget.events_received[0][0] == "mouse_down"
        assert widget.events_received[0][1][0] is event

    def test_handle_mouse_event_coordinate_transformation(self):
        """Test _handle_mouse_event with coordinate transformation"""
        parent = MockWidget()
        container = Container(parent)
        container._set_child_position(parent, 50, 100)
        child = MockWidget(parent=parent, capture_events=False)

        event = MouseEvent(x=10, y=20)

        result = EventPropagator._handle_mouse_event(child, "handle_mouse_down", event)

        assert result is parent
        assert len(child.events_received) == 1
        assert len(parent.events_received) == 1

        # Check coordinate transformation
        parent_event = parent.events_received[0][1][0]
        assert parent_event.x == 60  # 50 + 10
        assert parent_event.y == 120  # 100 + 20

    def test_handle_click(self):
        """Test handle_click method"""
        widget = MockWidget()

        result = EventPropagator.handle_click(widget, MouseButton.BUTTON_RIGHT)

        assert result is widget
        assert widget.events_received[0] == ("click", (MouseButton.BUTTON_RIGHT,), {})

    def test_handle_focus_in(self):
        """Test handle_focus_in method"""
        widget = MockWidget()

        result = EventPropagator.handle_focus_in(widget)

        assert result is widget
        assert widget.events_received[0] == ("focus_in", (), {})

    def test_handle_mouse_over(self):
        """Test handle_mouse_over method"""
        widget = MockWidget()
        event = MouseEvent(x=5, y=15)

        result = EventPropagator.handle_mouse_over(widget, event)

        assert result is widget
        assert widget.events_received[0] == ("mouse_over", (event,), {})

    def test_handle_mouse_enter(self):
        """Test handle_mouse_enter method"""
        widget = MockWidget()
        event = MouseEvent(x=5, y=15)

        result = EventPropagator.handle_mouse_enter(widget, event)

        assert result is widget
        assert widget.events_received[0] == ("mouse_enter", (event,), {})

    def test_handle_mouse_exit(self):
        """Test handle_mouse_exit method"""
        widget = MockWidget()

        result = EventPropagator.handle_mouse_exit(widget)

        assert result is widget
        assert widget.events_received[0] == ("mouse_exit", (), {})

    def test_handle_mouse_down(self):
        """Test handle_mouse_down method"""
        widget = MockWidget()
        event = MouseEvent(x=5, y=15)

        result = EventPropagator.handle_mouse_down(widget, event)

        assert result is widget
        assert widget.events_received[0] == ("mouse_down", (event,), {})

    def test_handle_mouse_up(self):
        """Test handle_mouse_up method"""
        widget = MockWidget()
        event = MouseEvent(x=5, y=15)

        result = EventPropagator.handle_mouse_up(widget, event)

        assert result is widget
        assert widget.events_received[0] == ("mouse_up", (event,), {})

    def test_handle_mouse_down_move(self):
        """Test handle_mouse_down_move method"""
        widget = MockWidget()
        event = MouseEvent(x=5, y=15)

        result = EventPropagator.handle_mouse_down_move(widget, event)

        assert result is widget
        assert widget.events_received[0] == ("mouse_down_move", (event,), {})

    def test_handle_mouse_down_canceled(self):
        """Test handle_mouse_down_canceled method"""
        widget = MockWidget()

        result = EventPropagator.handle_mouse_down_canceled(
            widget, MouseButton.BUTTON_MIDDLE
        )

        assert result is widget
        assert widget.events_received[0] == (
            "mouse_down_canceled",
            (MouseButton.BUTTON_MIDDLE,),
            {},
        )

    def test_manage_mouse_motion_simple_enter(self):
        """Test manage_mouse_motion with simple mouse enter"""
        # Setup widgets
        root = MockWidget(capture_events=False)
        child = MockWidget(parent=root, capture_events=False)

        # Setup ownership
        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)

        # Setup previous widget (different hierarchy)
        previous = MockWidget(capture_events=False)

        # Create pygame event
        pygame_event = _pygame_mouse_motion_event(100, 200, rel=(5, 5))

        # Test
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous)

        # Verify mouse enter was called on new widgets
        assert len(child.events_received) == 1
        assert child.events_received[0][0] == "mouse_enter"
        assert len(root.events_received) == 1
        assert root.events_received[0][0] == "mouse_enter"

        # Verify mouse exit was called on previous
        assert len(previous.events_received) == 1
        assert previous.events_received[0][0] == "mouse_exit"

    def test_manage_mouse_motion_on_same_widget(self):
        """Test manage_mouse_motion on same widget"""
        # Setup widgets
        root = MockWidget(capture_events=True)
        child = MockWidget(parent=root, capture_events=False)

        # Setup ownership
        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)

        # Setup previous widget (different hierarchy)
        previous = MockWidget(capture_events=False)

        # Create pygame event
        pygame_event1 = _pygame_mouse_motion_event(100, 200, rel=(5, 5))
        pygame_event2 = _pygame_mouse_motion_event(101, 201, rel=(1, 1))

        # Test
        EventPropagator.manage_mouse_motion(pygame_event1, ownership, previous)

        # Verify mouse enter was called on new widgets
        assert len(child.events_received) == 1
        assert child.events_received[0][0] == "mouse_enter"
        assert len(root.events_received) == 1
        assert root.events_received[0][0] == "mouse_enter"

        # Verify mouse exit was called on previous
        assert len(previous.events_received) == 1
        assert previous.events_received[0][0] == "mouse_exit"

        child.events_received.clear()
        root.events_received.clear()
        previous.events_received.clear()

        # Test second event on same widget (child)
        EventPropagator.manage_mouse_motion(pygame_event2, ownership, child)

        # No new mouse enter or exit events should be triggered
        # But we should have mouse_over on child and root
        assert len(child.events_received) == 1
        assert child.events_received[0][0] == "mouse_over"
        assert len(root.events_received) == 1
        assert root.events_received[0][0] == "mouse_over"

        assert len(previous.events_received) == 0

    def test_manage_mouse_motion_with_capture(self):
        """Test manage_mouse_motion with event capture stopping propagation"""
        # Setup widgets
        root = MockWidget(capture_events=False)
        child = MockWidget(parent=root)  # Captures

        # Setup ownership
        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)

        # Setup previous widget
        previous = MockWidget()  # Captures

        # Create pygame event
        pygame_event = _pygame_mouse_motion_event(100, 200)

        # Test
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous)

        # Child should capture mouse_enter, root should not receive event
        assert len(child.events_received) == 1
        assert child.events_received[0][0] == "mouse_enter"
        assert len(root.events_received) == 0

        # Previous should capture mouse_exit
        assert len(previous.events_received) == 1
        assert previous.events_received[0][0] == "mouse_exit"

    def test_manage_mouse_motion_overlapping_hierarchy(self):
        """Test manage_mouse_motion with overlapping widget hierarchies"""
        # Setup shared parent
        shared_parent = MockWidget(capture_events=False)

        # Setup current hierarchy
        current_child = MockWidget(parent=shared_parent, capture_events=False)

        # Setup previous hierarchy (shares parent)
        previous_child = MockWidget(parent=shared_parent, capture_events=False)

        # Setup ownership
        ownership = MouseOwnership(widget=current_child, x_in_parent=10, y_in_parent=20)

        # Create pygame event
        pygame_event = _pygame_mouse_motion_event(100, 200)

        # Test
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous_child)

        # Current child should get mouse_enter
        assert len(current_child.events_received) == 1
        assert current_child.events_received[0][0] == "mouse_enter"

        # Shared parent should get mouse_over
        # (not enter, because it was already in lineage)
        assert len(shared_parent.events_received) == 1
        assert shared_parent.events_received[0][0] == "mouse_over"

        # Previous child should get mouse_exit
        assert len(previous_child.events_received) == 1
        assert previous_child.events_received[0][0] == "mouse_exit"

    def test_manage_mouse_motion_coordinate_transformation(self):
        """Test coordinate transformation in manage_mouse_motion"""
        # Setup hierarchy
        root = MockWidget(capture_events=False)
        container = Container(root)
        container._set_child_position(root, 100, 200)

        parent = MockWidget(parent=root, capture_events=False)
        root._set_child_position(parent, 50, 75)

        child = MockWidget(parent=parent, capture_events=False)

        # Setup ownership
        ownership = MouseOwnership(widget=child, x_in_parent=10, y_in_parent=20)

        # Setup previous
        previous = MockWidget(capture_events=False)

        # Create pygame event
        pygame_event = _pygame_mouse_motion_event(300, 400)

        # Test
        EventPropagator.manage_mouse_motion(pygame_event, ownership, previous)

        # Check coordinate transformation for child (original coordinates)
        child_event = child.events_received[0][1][0]
        assert child_event.x == 10
        assert child_event.y == 20

        # Check coordinate transformation for parent (child.x + mouse_x)
        parent_event = parent.events_received[0][1][0]
        assert parent_event.x == 60  # parent.x + mouse_x = 50 + 10
        assert parent_event.y == 95  # parent.y + mouse_y = 75 + 20

        # Check coordinate transformation for root (parent.x + parent_mouse_x)
        root_event = root.events_received[0][1][0]
        assert root_event.x == 160  # root.x + parent_mouse_x = 100 + 60
        assert root_event.y == 295  # root.y + parent_mouse_y = 200 + 95

    def test_handle_with_none_widget(self):
        """Test _handle with None widget"""
        result = EventPropagator._handle(None, "handle_click", MouseButton.BUTTON_LEFT)
        assert result is None

    def test_handle_mouse_event_with_none_widget(self):
        """Test _handle_mouse_event with None widget"""
        event = MouseEvent(x=10, y=20)
        result = EventPropagator._handle_mouse_event(None, "handle_mouse_down", event)
        assert result is None

    def test_handle_returns_custom_widget(self):
        """Test _handle when handler returns a custom widget instead of True/False"""

        class CustomWidget(MockWidget):
            def __init__(self, return_widget):
                super().__init__()
                self.return_widget = return_widget

            def handle_click(self, button):
                self._log_event("click", button)
                return self.return_widget

        return_widget = MockWidget()
        widget = CustomWidget(return_widget)

        result = EventPropagator._handle(
            widget, "handle_click", MouseButton.BUTTON_LEFT
        )

        assert result is return_widget
        assert len(widget.events_received) == 1
        assert len(return_widget.events_received) == 0

    def test_handle_mouse_event_returns_custom_widget(self):
        """Test _handle_mouse_event when handler returns custom widget"""

        class CustomWidget(MockWidget):
            def __init__(self, return_widget):
                super().__init__()
                self.return_widget = return_widget

            def handle_mouse_down(self, event):
                self._log_event("mouse_down", event)
                return self.return_widget

        return_widget = MockWidget()
        widget = CustomWidget(return_widget)
        event = MouseEvent(x=10, y=20)

        result = EventPropagator._handle_mouse_event(widget, "handle_mouse_down", event)

        assert result is return_widget
        assert len(widget.events_received) == 1
        assert len(return_widget.events_received) == 0
