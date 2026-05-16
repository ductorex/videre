import logging
from dataclasses import dataclass

import pygame
import pygame.freetype

from videre.core.pygame_backend import Pygame, Rect
from videre.fonts.provider import FontProvider
from videre.fonts.unicode_utils import Unicode


@dataclass(slots=True)
class CharMeasures:
    font: pygame.freetype.Font
    rect: Rect
    metrics: tuple[int, int, int, int, float, float]


class PygameFontFactory(Pygame):
    __slots__ = (
        "_prov",
        "_key_to_font",
        "_size",
        "_origin",
        "_base_font",
        "_cached_char_measures",
    )

    def __init__(self, size=14):
        super().__init__()
        self._prov = FontProvider()
        self._key_to_font: dict[tuple[str, bool, bool], pygame.freetype.Font] = {}
        self._size = size
        self._origin = True
        self._base_font = None

        self._cached_char_measures: dict[tuple[str, int, bool, bool], CharMeasures] = {}

    @property
    def base_font(self) -> pygame.freetype.Font:
        if self._base_font is None:
            self._base_font = self.get_font(" ")
        return self._base_font

    @property
    def size(self) -> int:
        return self._size

    @property
    def font_height(self) -> int:
        return self.base_font.get_sized_height(self._size)

    @property
    def symbol_size(self) -> int:
        # Round to the nearest pixel rather than truncating: the legacy
        # pipeline accepts the float directly and pygame.freetype's grid-fit
        # lands on the nearest pixel, while the shaped pipeline can only
        # consume integer pixel sizes. `int()` would always round down by
        # up to 0.999 px, shrinking the symbol bitmap by a row at common
        # base sizes (e.g. 14 → 22.75 truncates to 22, losing 1 row).
        return int(round(self._size * 1.625))

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
            logging.debug(
                f"[pygame][font](block={Unicode.block(c)}, c={c}) {name}, "
                f"height {font.get_sized_height(self._size)}, "
                f"glyph height {font.get_sized_glyph_height(self._size)}, "
                f"ascender {font.get_sized_ascender(self._size)}, "
                f"descender {font.get_sized_descender(self._size)}"
            )
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
