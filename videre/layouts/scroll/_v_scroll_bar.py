from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_utils import Surface
from videre.layouts.scroll._h_scroll_bar import _HScrollBar


class _VScrollBar(_HScrollBar):
    __slots__ = ()
    __is_horizontal__ = False

    def _bar_length(self) -> int:
        h = self._prev_scope_height()
        if self.both:
            h = max(0, h - self.thickness)
        return h

    def get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        if (
            self._surface
            and self.x <= x_in_parent < self.x + self.thickness
            and 0 <= y_in_parent < self._bar_length()
        ):
            return MouseOwnership(self, x_in_parent, y_in_parent)
        return None

    def handle_mouse_down(self, event: MouseEvent):
        button = event.button
        y = event.y
        if self.on_jump and button == MouseButton.BUTTON_LEFT:
            grip_length = self._surface.get_height()
            h = self._bar_length()
            if y < self.y or y >= self.y + grip_length:
                y = min(y, h - grip_length)
                self._jump(y, h, grip_length)
            else:
                self._grabbed = (y - self.y,)

    def handle_mouse_down_move(self, event: MouseEvent):
        if self.on_jump and self._grabbed and event.button_left:
            grab_y = event.y
            y = grab_y - self._grabbed[0]
            h = self._bar_length()
            grip_length = self._surface.get_height()
            y = min(max(y, 0), h - grip_length)
            if y != self.y:
                self._jump(y, h, grip_length)

    def _jump(self, y: int, h: int, grip_length: int):
        if y == h - grip_length:
            self.on_jump(self.content_length)
        else:
            content_pos = (y * self.content_length) / h
            self.on_jump(round(content_pos))

    def _compute(
        self, window, view_width: int, view_height: int
    ) -> tuple[Surface, tuple[int, int]]:
        thickness = self.thickness
        v_scroll_y, v_scroll_height = self._compute_scroll_metrics(
            view_height,
            self.content_length,
            self.content_pos,
            scrollbar_length=(max(0, view_height - thickness) if self.both else None),
        )
        v_scroll = window.new_surface(thickness, v_scroll_height)
        v_scroll.fill(self.color)
        pos = (view_width - thickness, v_scroll_y)
        return v_scroll, pos
