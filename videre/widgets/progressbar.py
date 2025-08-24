import pygame
import pygame.gfxdraw

from videre.colors import Colors
from videre.core.pygame_utils import Surface
from videre.widgets.widget import Widget


class ProgressBar(Widget):
    __wprops__ = {"value"}
    __slots__ = ()

    def __init__(self, value: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.value = value

    @property
    def value(self) -> float:
        return self._get_wprop("value")

    @value.setter
    def value(self, progress: float):
        self._set_wprop("value", min(max(0.0, float(progress)), 1.0))

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        bg_w = 102 if width is None else max(width, 2)
        bg_h = window.fonts.font_height
        inner_w = int((bg_w - 2) * self.value)
        inner_h = bg_h - 2
        bg = window.new_surface(bg_w, bg_h)
        pygame.gfxdraw.rectangle(bg, pygame.Rect(0, 0, bg_w, bg_h), Colors.black)
        if inner_w:
            pygame.gfxdraw.box(bg, pygame.Rect(1, 1, inner_w, inner_h), Colors.black)
        return bg
