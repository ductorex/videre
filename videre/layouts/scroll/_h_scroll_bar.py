from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_utils import Color, Surface
from videre.layouts.scroll._scroll_background import _ScrollBackground
from videre.widgets.widget import Widget


class _HScrollBar(Widget):
    __wprops__ = {"content_length", "content_pos", "thickness", "both", "color"}
    __slots__ = ("on_jump", "_grabbed", "_hover", "background")
    __is_horizontal__ = True
    _SCROLL_COLOR_HOVER = Color(216, 216, 216, 255)
    _SCROLL_COLOR = Color(216, 216, 216, 128)

    def __init__(self, thickness=18, on_jump=None, **kwargs):
        super().__init__(**kwargs)
        self._set_wprop("thickness", thickness)
        self.on_jump = on_jump
        self._hover = False
        self._grabbed = ()
        self._set_color()
        self.background = _ScrollBackground(self.__is_horizontal__).with_parent(self)

    def has_changed(self) -> bool:
        return super().has_changed() and self.content_length is not None

    def configure(
        self,
        content_length: int,
        content_pos: int,
        both: bool,
        thickness: int | None = None,
    ):
        self._set_wprops(
            content_length=content_length, content_pos=content_pos, both=both
        )
        if thickness is not None:
            self._set_wprop("thickness", thickness)
        self.background.configure(self.thickness, both, self._hover or self._grabbed)

    @property
    def content_length(self) -> int:
        return self._get_wprop("content_length")

    @property
    def content_pos(self) -> int:
        return self._get_wprop("content_pos")

    @property
    def thickness(self) -> int:
        return self._get_wprop("thickness")

    @property
    def both(self) -> bool:
        return self._get_wprop("both")

    @property
    def color(self) -> Color:
        return self._get_wprop("color")

    def _set_color(self):
        self._set_wprop(
            "color",
            (
                self._SCROLL_COLOR_HOVER
                if self._hover or self._grabbed
                else self._SCROLL_COLOR
            ),
        )

    def _bar_length(self) -> int:
        w = self._prev_scope_width()
        if self.both:
            w = max(0, w - self.thickness)
        return w

    def get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        if (
            self._surface
            and 0 <= x_in_parent < self._bar_length()
            and self.y <= y_in_parent < self.y + self.thickness
        ):
            return MouseOwnership(self, x_in_parent, y_in_parent)
        return None

    def handle_mouse_down(self, event: MouseEvent):
        button = event.button
        x = event.x
        if self.on_jump and button == MouseButton.BUTTON_LEFT:
            grip_length = self._surface.get_width()
            w = self._bar_length()
            if x < self.x or x >= self.x + grip_length:
                x = min(x, w - grip_length)
                self._jump(x, w, grip_length)
            else:
                self._grabbed = (x - self.x,)
                self._set_color()

    def handle_mouse_up(self, event: MouseEvent):
        return self.handle_mouse_down_canceled(event.button)

    def handle_mouse_down_canceled(self, button: MouseButton):
        if button == MouseButton.BUTTON_LEFT:
            self._grabbed = ()
            self._set_color()

    def handle_mouse_down_move(self, event: MouseEvent):
        if self.on_jump and self._grabbed and event.button_left:
            grab_x = event.x
            x = grab_x - self._grabbed[0]
            w = self._bar_length()
            grip_length = self._surface.get_width()
            x = min(max(x, 0), w - grip_length)
            if x != self.x:
                self._jump(x, w, grip_length)

    def handle_mouse_enter(self, event: MouseEvent):
        self._hover = True
        self._set_color()

    def handle_mouse_exit(self):
        self._hover = False
        self._set_color()

    def _jump(self, x: int, w: int, grip_length: int):
        if x == w - grip_length:
            self.on_jump(self.content_length)
        else:
            content_pos = (x * self.content_length) / w
            self.on_jump(round(content_pos))

    def _compute(
        self, window, view_width: int, view_height: int
    ) -> tuple[Surface, tuple[int, int]]:
        thickness = self.thickness
        h_scroll_x, h_scroll_width = self._compute_scroll_metrics(
            view_width,
            self.content_length,
            self.content_pos,
            scrollbar_length=(max(0, view_width - thickness) if self.both else None),
        )
        h_scroll = window.new_surface(h_scroll_width, thickness)
        h_scroll.fill(self.color)
        pos = (h_scroll_x, view_height - thickness)
        return h_scroll, pos

    @classmethod
    def _compute_scroll_metrics(
        cls, view_length, content_length, content_pos, *, scrollbar_length=None
    ) -> tuple[int, int]:
        if scrollbar_length is None:
            scrollbar_length = view_length
        scroll_pos = (scrollbar_length * abs(content_pos)) / content_length
        scroll_length = (scrollbar_length * view_length) / content_length
        return round(scroll_pos), round(scroll_length)

    def draw(self, window, view_width: int = None, view_height: int = None) -> Surface:
        assert view_width and view_height
        scroll, pos = self._compute(window, view_width, view_height)
        self._parent._set_child_position(self, *pos)
        return scroll
