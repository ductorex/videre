import logging
from dataclasses import dataclass

import pygame
import pygame.freetype

from videre.core.pygame_backend.definitions import Rect
from videre.fonts.provider import FontProvider


@dataclass(slots=True)
class CharMeasures:
    font: pygame.freetype.Font
    rect: Rect
    metrics: tuple[int, int, int, int, float, float]


class PygameFontFactory:
    __slots__ = ("_prov", "_key_to_font", "_origin", "_cached_char_measures")

    def __init__(self):
        self._prov = FontProvider()
        self._key_to_font: dict[tuple[str, bool, bool], pygame.freetype.Font] = {}
        self._origin = True
        self._cached_char_measures: dict[tuple[str, int, bool, bool], CharMeasures] = {}

    def get_font(
        self, c: str, strong: bool = False, italic: bool = False
    ) -> pygame.freetype.Font:
        name, path = self._prov.get_font_info(c)
        cache_key = (name, strong, italic)
        font = self._key_to_font.get(cache_key)
        if not font:
            font = pygame.freetype.Font(path)
            font.origin = self._origin
            try:
                font.strong = strong
                font.oblique = italic
            except Exception as exc:
                logging.warning(
                    f'Unable to set strong or italic for font "{font.name}": '
                    f"{type(exc).__name__}: {exc}"
                )
            self._key_to_font[cache_key] = font
        return font

    def get_char_measures(
        self, c: str, size: int, strong: bool, italic: bool
    ) -> CharMeasures:
        key = (c, size, strong, italic)
        if key not in self._cached_char_measures:
            font = self.get_font(c, strong, italic)
            rect = font.get_rect(c, size=size)
            (metrics,) = font.get_metrics(c, size=size)
            self._cached_char_measures[key] = CharMeasures(font, rect, metrics)
        return self._cached_char_measures[key]
