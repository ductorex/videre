from __future__ import annotations

import logging
from typing import assert_never

import pygame
import pygame.freetype
import pygame.gfxdraw
import pygame.image
import pygame.transform
from PIL.Image import Image as PILImage

from videre.core.drawer import (
    Args,
    BlitArgs,
    BoxArgs,
    Color,
    Drawer,
    DrawerFont,
    FillArgs,
    FilledPolygonArgs,
    ImageArgs,
    LineArgs,
    Rectangle,
    RectangleArgs,
    SmoothScaleArgs,
    TextArgs,
)
from videre.core.fontfactory.pygame_font_factory import PygameFontFactory


def _color(c: Color) -> tuple[int, int, int, int]:
    return c.r, c.g, c.b, c.a


def _rect(r: Rectangle) -> pygame.Rect:
    return pygame.Rect(int(r.x), int(r.y), int(r.width), int(r.height))


def _pil_to_surface(image: PILImage) -> pygame.Surface:
    converted = image if image.mode == "RGBA" else image.convert("RGBA")
    return pygame.image.frombytes(converted.tobytes(), converted.size, "RGBA")


class PygameDrawerExecutor:
    """Executes a Drawer's command list on a pygame Surface.

    Recursive strategy: when a BlitArgs is encountered, the source Drawer is
    rasterized to a fresh ARGB Surface and then blitted onto the target.
    Equivalent in behavior to the existing per-widget Surface model — useful
    as a correctness baseline before introducing flattening optimizations.
    """

    __slots__ = ("_fonts", "_key_to_font")

    def __init__(self, fonts: PygameFontFactory):
        self._fonts = fonts
        self._key_to_font: dict[DrawerFont, pygame.freetype.Font] = {}

    def execute(self, drawer: Drawer, surface: pygame.Surface) -> None:
        """Execute every command of ``drawer`` on ``surface``."""
        for args in drawer:
            self._execute_one(args, surface)

    def render_to_surface(self, drawer: Drawer) -> pygame.Surface:
        """Allocate a fresh ARGB surface for ``drawer`` and execute on it."""
        surface = pygame.Surface(
            (drawer.get_width(), drawer.get_height()), flags=pygame.SRCALPHA
        )
        self.execute(drawer, surface)
        return surface

    def _execute_one(self, args: Args, surface: pygame.Surface) -> None:
        match args:
            case FillArgs(color):
                surface.fill(_color(color))
            case BlitArgs(child, position):
                surface.blit(self.render_to_surface(child), (position.x, position.y))
            case LineArgs(color, start, end):
                pygame.gfxdraw.line(
                    surface,
                    int(start.x),
                    int(start.y),
                    int(end.x),
                    int(end.y),
                    _color(color),
                )
            case RectangleArgs(rect, color):
                pygame.gfxdraw.rectangle(surface, _rect(rect), _color(color))
            case BoxArgs(rect, color):
                pygame.gfxdraw.box(surface, _rect(rect), _color(color))
            case FilledPolygonArgs(points, color):
                pygame.gfxdraw.filled_polygon(
                    surface, [(int(p.x), int(p.y)) for p in points], _color(color)
                )
            case TextArgs(font, destination, text, size, fgcolor):
                pf = self._load_pygame_font(font)
                actual_size = size or self._fonts.default_size
                actual_color = _color(fgcolor) if fgcolor is not None else None
                pf.render_to(
                    surface,
                    (destination.x, destination.y),
                    text,
                    fgcolor=actual_color,
                    size=actual_size,
                )
            case SmoothScaleArgs(child):
                src = self.render_to_surface(child)
                surface.blit(
                    pygame.transform.smoothscale(src, surface.get_size()), (0, 0)
                )
            case ImageArgs(image):
                surface.blit(_pil_to_surface(image), (0, 0))
            case _:
                assert_never(args)

    def _load_pygame_font(self, font: DrawerFont) -> pygame.freetype.Font:
        pygame.freetype.init()
        pf = self._key_to_font.get(font)
        if pf is None:
            pf = pygame.freetype.Font(font.path)
            pf.origin = True
            try:
                pf.strong = font.strong
                pf.oblique = font.italic
            except Exception as exc:
                logging.warning(
                    f'Unable to set strong or italic for font "{pf.name}": '
                    f"{type(exc).__name__}: {exc}"
                )
            self._key_to_font[font] = pf
        return pf
