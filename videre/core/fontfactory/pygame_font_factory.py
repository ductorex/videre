import logging

import pygame
import pygame.freetype

from videre.core.pygame_utils import PygameUtils
from videre.fonts import FontProvider
from videre.fonts.unicode_utils import Unicode


class PygameFontFactory(PygameUtils):
    __slots__ = ("_prov", "_name_to_font", "_size", "_origin", "_base_font")

    def __init__(self, size=14):
        super().__init__()
        self._prov = FontProvider()
        self._name_to_font = {}
        self._size = size
        self._origin = True
        self._base_font = self.get_font(" ")

    @property
    def base_font(self) -> pygame.freetype.Font:
        return self._base_font

    @property
    def size(self) -> int:
        return self._size

    @property
    def font_height(self) -> int:
        return self._base_font.get_sized_height(self._size)

    @property
    def symbol_size(self):
        return self._size * 1.625

    def get_font(self, c: str) -> pygame.freetype.Font:
        name, path = self._prov.get_font_info(c)
        font = self._name_to_font.get(name)
        if not font:
            font = pygame.freetype.Font(path, size=self._size)
            font.origin = self._origin
            self._name_to_font[name] = font
            logging.debug(
                f"[pygame][font](block={Unicode.block(c)}, c={c}) {name}, "
                f"height {font.get_sized_height(self._size)}, "
                f"glyph height {font.get_sized_glyph_height(self._size)}, "
                f"ascender {font.get_sized_ascender(self._size)}, "
                f"descender {font.get_sized_descender(self._size)}"
            )
        return font
