from typing import Protocol

from videre.core.caret_position import CaretPosition
from videre.core.pygame_utils import Surface


class RenderingResult(Protocol):
    surface: Surface


class TextRenderingResult(Protocol):
    def pos_to_pixel(self, pos: int) -> CaretPosition: ...

    def pixel_to_pos(self, x: int, y: int) -> int: ...
