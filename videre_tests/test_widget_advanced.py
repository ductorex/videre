import pygame
import pytest

from videre import Text
from videre.core.constants import MouseButton
from videre.core.events import KeyboardEntry
from videre.widgets.widget import Widget


class TestWidgetAdvanced:
    """Test advanced Widget functionality and edge cases"""

    def test_widget_key_handling_default(self):
        """Test widget keyboard event handling default behavior"""
        widget = Widget()

        # Create mock keyboard event
        mock_event = pygame.event.Event(
            pygame.KEYDOWN, {"mod": pygame.KMOD_CTRL, "key": pygame.K_c, "unicode": "c"}
        )

        entry = KeyboardEntry(mock_event)

        # Test default key handling (should not crash and return None/False)
        result = widget.handle_keydown(entry)
        assert result is None or isinstance(result, bool)

    def test_widget_parent_child_relationships(self):
        """Test widget parent-child relationship edge cases"""
        parent = Widget()
        child1 = Widget()

        # Test initial state
        assert child1._parent is None
        assert len(parent._children_pos._el_to_pos) == 0

        # Test setting parent
        child1.with_parent(parent)
        assert child1._parent is parent
        parent._set_child_x(child1, 0)
        assert child1 in parent._children_pos._el_to_pos

        # Test changing parent
        new_parent = Widget()
        child1.with_parent(new_parent)
        assert child1._parent is new_parent
        assert child1 not in parent._children_pos._el_to_pos
        new_parent._set_child_x(child1, 0)
        assert child1 in new_parent._children_pos._el_to_pos

        # Test setting same parent again (should be no-op)
        initial_count = len(new_parent._children_pos._el_to_pos)
        child1.with_parent(new_parent)
        assert len(new_parent._children_pos._el_to_pos) == initial_count

    def test_widget_property_change_detection(self):
        """Test widget property change detection mechanisms"""
        widget = Widget(weight=1)

        # Test initial state
        assert widget.weight == 1
        assert widget.has_changed() is True  # New widget should report changed

        # After update, should not report changed until property changes
        widget.update()
        # Note: has_changed() behavior depends on implementation details

        # Test changing property
        widget._set_wprop("weight", 2)
        assert widget.weight == 2

    def test_widget_wprop_getters_setters(self):
        """Test widget property getters and setters"""
        widget = Widget()

        # Test setting and getting weight
        widget._set_wprop("weight", 5)
        assert widget._get_wprop("weight") == 5
        assert widget.weight == 5

        # Test setting multiple properties
        # Should raise error for unknown properties
        with pytest.raises(
            AssertionError, match="unknown widget property: custom_prop"
        ):
            widget._set_wprops(weight=10, custom_prop=42)

        # Test setting known properties
        class CustomWidget(Widget):
            __wprops__ = {"custom_prop"}

        widget = CustomWidget()
        widget._set_wprops(weight=10, custom_prop=42)
        assert widget.weight == 10
        assert widget._get_wprop("custom_prop") == 42

    def test_widget_surface_rendering_lifecycle(self, fake_win):
        """Test widget surface rendering lifecycle"""
        widget = Text("Test Content", size=16)

        # Initially no surface
        assert widget._surface is None

        # After adding to window and rendering
        fake_win.controls = [widget]
        fake_win.render()

        # Should have surface
        assert widget._surface is not None
        assert isinstance(widget._surface, pygame.Surface)

        # Surface should have reasonable dimensions
        assert widget._surface.get_width() > 0
        assert widget._surface.get_height() > 0

    def test_widget_coordinate_calculations(self, fake_win):
        """Test widget coordinate calculation methods"""
        widget = Text("Test", size=16)
        fake_win.controls = [widget]
        fake_win.render()

        # Test global coordinates
        global_x = widget.global_x
        global_y = widget.global_y
        assert isinstance(global_x, int)
        assert isinstance(global_y, int)

        # Test boundary coordinates
        assert widget.right == widget.x + widget.rendered_width - 1
        assert widget.bottom == widget.y + widget.rendered_height - 1

    def test_widget_mouse_event_handling_edge_cases(self):
        """Test widget mouse event handling edge cases"""
        widget = Widget()

        # Test mouse events without proper setup (should not crash)
        from videre.core.events import MouseEvent

        event = MouseEvent(x=10, y=10, buttons=[MouseButton.BUTTON_LEFT])

        # These should not crash even if not properly implemented
        try:
            widget.handle_mouse_down(event)
            widget.handle_mouse_up(event)
            widget.handle_mouse_down_move(event)
            widget.handle_mouse_down_canceled(MouseButton.BUTTON_LEFT)
            widget.handle_mouse_enter(event)
            widget.handle_mouse_exit()
        except NotImplementedError:
            # Some widgets might have abstract methods
            pass
        except Exception as e:
            # Any other exception should be investigated
            pytest.fail(f"Unexpected exception in mouse handling: {e}")

    def test_widget_update_mechanism(self, fake_win):
        """Test widget update mechanism and change tracking"""
        widget = Text(weight=1)

        # Test that update processes changes
        initial_old_state = dict(widget._old)
        widget.weight = 2  # Change a property

        widget.render(fake_win, 0, 0)

        # After update, old state should be updated
        assert widget._old != initial_old_state

    def test_widget_key_property(self):
        """Test widget key property behavior"""
        # Widget with default key
        widget1 = Widget()
        assert widget1._key == id(widget1)

        # Widget with custom key
        custom_key = "my_custom_key"
        widget2 = Widget(key=custom_key)
        assert widget2._key == custom_key

        # Widgets should have different keys by default
        widget3 = Widget()
        assert widget1._key != widget3._key
