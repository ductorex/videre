import pygame
import pytest
from videre import Text
from videre.widgets.widget import Widget


class TestWidgetAdvanced:
    """Test advanced Widget functionality and edge cases"""

    def test_widget_parent_child_relationships(self):
        parent = Widget()
        child = Widget()

        assert child._parent is None

        # Set parent
        child.with_parent(parent)
        assert child._parent is parent

        # Change parent
        new_parent = Widget()
        child.with_parent(new_parent)
        assert child._parent is new_parent

        # Same parent again (no-op)
        child.with_parent(new_parent)
        assert child._parent is new_parent

    def test_widget_wprop_getters_setters(self):
        widget = Widget()

        widget._set_wprop("weight", 5)
        assert widget._get_wprop("weight") == 5
        assert widget.weight == 5

        with pytest.raises(
            AssertionError, match="unknown widget property: custom_prop"
        ):
            widget._set_wprops(weight=10, custom_prop=42)

        class CustomWidget(Widget):
            __wprops__ = {"custom_prop"}

        widget = CustomWidget()
        widget._set_wprops(weight=10, custom_prop=42)
        assert widget.weight == 10
        assert widget._get_wprop("custom_prop") == 42

    def test_widget_surface_rendering_lifecycle(self, fake_win):
        widget = Text("Test Content", size=16)

        assert widget._surface is None

        fake_win.controls = [widget]
        fake_win.render()

        assert widget._surface is not None
        assert isinstance(widget._surface, pygame.Surface)
        assert widget._surface.get_width() > 0
        assert widget._surface.get_height() > 0

    def test_widget_coordinate_calculations(self, fake_win):
        widget = Text("Test", size=16)
        fake_win.controls = [widget]
        fake_win.render()

        assert widget.right == widget.x + widget.rendered_width - 1
        assert widget.bottom == widget.y + widget.rendered_height - 1

    def test_widget_update_mechanism(self, fake_win):
        widget = Text(weight=1)

        initial_old_state = dict(widget._old)
        widget.weight = 2

        widget.render(fake_win, 0, 0)

        assert widget._old != initial_old_state

    def test_widget_key_property(self):
        widget1 = Widget()
        assert widget1._key == id(widget1)

        widget2 = Widget(key="my_custom_key")
        assert widget2._key == "my_custom_key"

        widget3 = Widget()
        assert widget1._key != widget3._key
