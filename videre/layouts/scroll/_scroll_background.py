from videre.core.pygame_utils import Color, Surface
from videre.widgets.widget import Widget


class _ScrollBackground(Widget):
    __wprops__ = {"thickness", "both", "hover"}
    __slots__ = ("_h",)
    _COLOR_HOVER = Color(0, 0, 0, 16)
    _COLOR_NORMAL = Color(0, 0, 0, 0)

    def __init__(self, horizontal=True, **kwargs):
        super().__init__(**kwargs)
        self._h = horizontal

    def configure(self, thickness: int, both: bool, hover: bool):
        self._set_wprops(thickness=thickness, both=both, hover=hover)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        assert width and height

        thickness = self._get_wprop("thickness")
        both = self._get_wprop("both")
        hover = self._get_wprop("hover")

        if self._h:
            b_width = max(0, width - thickness) if both else width
            b_height = thickness
            x, y = 0, height - thickness
        else:
            b_width = thickness
            b_height = max(0, height - thickness) if both else height
            x, y = width - thickness, 0

        self._parent._set_child_position(self, x, y)

        surface = window.new_surface(b_width, b_height)
        surface.fill(self._COLOR_HOVER if hover else self._COLOR_NORMAL)
        return surface
