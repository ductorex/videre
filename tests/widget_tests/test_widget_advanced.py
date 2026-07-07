import pytest

from videre import Text
from videre.widgets.empty_widget import EmptyWidget


class TestWidgetAdvanced:
    """Test advanced Widget functionality and edge cases"""

    def test_widget_parent_child_relationships(self):
        parent = EmptyWidget()
        child = EmptyWidget()

        assert child._parent is None

        # Set parent
        child.with_parent(parent)
        assert child._parent is parent

        # Change parent
        new_parent = EmptyWidget()
        child.with_parent(new_parent)
        assert child._parent is new_parent

        # Same parent again (no-op)
        child.with_parent(new_parent)
        assert child._parent is new_parent

    def test_widget_wprop_getters_setters(self):
        widget = EmptyWidget()

        widget._set_wprop("weight", 5)
        assert widget._get_wprop("weight") == 5
        assert widget.weight == 5

        with pytest.raises(
            AssertionError, match="unknown widget property: custom_prop"
        ):
            widget._set_wprops(weight=10, custom_prop=42)

        class CustomWidget(EmptyWidget):
            __wprops__ = {"custom_prop"}

        widget = CustomWidget()
        widget._set_wprops(weight=10, custom_prop=42)
        assert widget.weight == 10
        assert widget._get_wprop("custom_prop") == 42

    def test_widget_surface_rendering_lifecycle(self, fake_win):
        widget = Text("Test Content", size=16)

        assert not widget.is_rendered()

        fake_win.controls = [widget]
        fake_win.render()

        assert widget.is_rendered()
        assert widget.rendered_width > 0
        assert widget.rendered_height > 0

    def test_widget_coordinate_calculations(self, fake_win):
        widget = Text("Test", size=16)
        fake_win.controls = [widget]
        fake_win.render()

        assert widget.right == widget.x + widget.rendered_width - 1
        assert widget.bottom == widget.y + widget.rendered_height - 1

    def test_widget_update_mechanism(self, fake_win):
        widget = Text(weight=1)
        fake_win.controls = [widget]
        fake_win.render()
        assert not widget.has_changed()

        widget.weight = 2
        assert widget.has_changed()

        fake_win.render()
        assert not widget.has_changed()

    def test_widget_key_property(self):
        widget1 = EmptyWidget()
        assert widget1._key == str(id(widget1))

        widget2 = EmptyWidget(key="my_custom_key")
        assert widget2._key == "my_custom_key"

        widget3 = EmptyWidget()
        assert widget1._key != widget3._key
