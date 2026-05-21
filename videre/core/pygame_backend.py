from dataclasses import dataclass
from typing import Sequence, TypeAlias

import pygame
import pygame.gfxdraw
from PIL.Image import Image

from videre.colors import Color

Surface = pygame.Surface
Rect = pygame.Rect
Event = pygame.event.Event
PygameColor = pygame.Color


_Position: TypeAlias = tuple[int | float, int | float]


class Pygame:
    __slots__ = ("__default_cursor", "__text_cursor")

    def __init__(self):
        self.init()
        self.__default_cursor = pygame.mouse.get_cursor()
        self.__text_cursor = pygame.cursors.compile(pygame.cursors.textmarker_strings)

    def set_text_cursor(self):
        pygame.mouse.set_cursor((8, 16), (0, 0), *self.__text_cursor)

    def set_default_cursor(self):
        pygame.mouse.set_cursor(*self.__default_cursor)

    def cursor_is_default(self) -> bool:
        return pygame.mouse.get_cursor() == self.__default_cursor

    @classmethod
    def init(cls):
        # Init pygame here.
        pygame.init()

    @classmethod
    def new_surface(cls, width: int | float, height: int | float) -> Surface:
        return Surface((width, height), flags=pygame.SRCALPHA)

    @classmethod
    def zero(cls) -> Surface:
        return Surface((0, 0), flags=pygame.SRCALPHA)

    @classmethod
    def new_color(cls, color: Color) -> PygameColor:
        return PygameColor(color.r, color.g, color.b, color.a)

    @classmethod
    def fill(cls, surface: Surface, color: Color) -> None:
        surface.fill(cls.new_color(color))

    @classmethod
    def blit(cls, dst: Surface, src: Surface, position: _Position) -> None:
        dst.blit(src, position)

    @classmethod
    def line(
        cls, surface: Surface, color: Color, start: _Position, end: _Position
    ) -> None:
        # `pygame.draw.line` over `pygame.gfxdraw.line`: faster on tight
        # loops (gradients trace hundreds of lines per frame) and supports
        # a `width` parameter if we ever need thicker strokes. `gfxdraw`
        # only offers pixel-exact non-AA single-pixel lines.
        pygame.draw.line(surface, Pygame.new_color(color), start, end)

    @classmethod
    def rectangle(cls, surface: Surface, rectangle: Rect, color: Color) -> None:
        pygame.gfxdraw.rectangle(surface, rectangle, Pygame.new_color(color))

    @classmethod
    def box(cls, surface: Surface, rectangle: Rect, color: Color) -> None:
        pygame.gfxdraw.box(surface, rectangle, Pygame.new_color(color))

    @classmethod
    def filled_polygon(
        cls, surface: Surface, points: Sequence[_Position], color: Color
    ) -> None:
        pygame.gfxdraw.filled_polygon(surface, points, Pygame.new_color(color))

    @classmethod
    def smoothscale(
        cls, surface: Surface, width: int | float, height: int | float
    ) -> Surface:
        return pygame.transform.smoothscale(surface, (width, height))

    @classmethod
    def image(cls, image: Image) -> Surface:
        # `frombytes` copies the buffer; `frombuffer` would share it and
        # require the PIL image to stay alive for as long as the Surface
        # exists. A self-contained Surface is safer at this boundary and
        # the copy cost is dwarfed by the upstream PIL decode + tobytes.
        return pygame.image.frombytes(image.tobytes(), image.size, "RGBA")


@dataclass(slots=True, frozen=True)
class PygameRendered:
    surface: Surface
