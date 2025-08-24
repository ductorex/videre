import pygame.gfxdraw

from videre.colors import Colors
from videre.core.pygame_utils import Surface
from videre.widgets.abstractanimation import AbstractAnimation, AbstractFraming, FPS


class Progressing(AbstractAnimation):
    __wprops__ = {"_cursor", "_direction"}
    __slots__ = ("_max_cursor",)

    def __init__(self, framing: AbstractFraming = None, steps=15, **kwargs):
        super().__init__(framing=framing or FPS(30), **kwargs)
        self._set_wprops(_cursor=0, _direction=1)
        self._max_cursor = steps

    def _on_frame(self):
        curr_direction = self._get_wprop("_direction")
        next_cursor = self._get_wprop("_cursor") + curr_direction
        next_direction = curr_direction
        if next_cursor % self._max_cursor == 0:
            next_direction = -curr_direction
        self._set_wprops(_cursor=next_cursor, _direction=next_direction)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        bg_w = 102 if width is None else max(width, 2)
        bg_h = window.fonts.font_height
        inner_w = (bg_w - 2) // 2
        inner_h = bg_h - 2

        inner_max_x = bg_w - 2 - inner_w
        inner_x = int(self._get_wprop("_cursor") * inner_max_x / self._max_cursor)

        bg = window.new_surface(bg_w, bg_h)
        pygame.gfxdraw.rectangle(bg, pygame.Rect(0, 0, bg_w, bg_h), Colors.black)
        if inner_w:
            pygame.gfxdraw.box(
                bg, pygame.Rect(inner_x + 1, 1, inner_w, inner_h), Colors.black
            )
        return bg
