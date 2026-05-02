import logging

import freetype
import pygame.freetype

from videre.core.abstract_font_factory import (
    AbstractFontFactory,
    CharMetrics,
    LineMetrics,
    UnderlineMetrics,
)
from videre.core.drawer import DrawerFont
from videre.fonts.provider import FontProvider


class PygameFontFactory(AbstractFontFactory):
    __slots__ = (
        "_prov",
        "_key_to_font",
        "_key_to_freetype_face",
        "_size",
        "_origin",
        "_cached_char_metrics",
        "_cached_underline_metrics",
    )

    def __init__(self, size: int = 14):
        super().__init__()
        self._prov = FontProvider()
        self._key_to_font: dict[DrawerFont, pygame.freetype.Font] = {}
        self._key_to_freetype_face: dict[DrawerFont, freetype.Face] = {}
        self._size = size
        self._origin = True

        self._cached_char_metrics: dict[tuple[DrawerFont, str, int], CharMetrics] = {}
        self._cached_underline_metrics: dict[
            tuple[DrawerFont, int], UnderlineMetrics
        ] = {}

    @property
    def default_size(self) -> int:
        return self._size

    @property
    def symbol_size(self) -> float:
        return self._size * 1.625

    def resolve(
        self, char: str, *, strong: bool = False, italic: bool = False
    ) -> DrawerFont:
        _, path = self._prov.get_font_info(char)
        return DrawerFont(path=path, strong=strong, italic=italic)

    def line_metrics(self, font: DrawerFont, size: int) -> LineMetrics:
        pf = self._load_pygame_font(font)
        space = self.char_metrics(font, " ", size)
        return LineMetrics(
            height=pf.get_sized_height(size),
            ascender=abs(pf.get_sized_ascender(size)),
            descender=abs(pf.get_sized_descender(size)),
            space_advance=space.advance,
        )

    def char_metrics(self, font: DrawerFont, char: str, size: int) -> CharMetrics:
        key = (font, char, size)
        cached = self._cached_char_metrics.get(key)
        if cached is not None:
            return cached
        pf = self._load_pygame_font(font)
        rect = pf.get_rect(char, size=size)
        (metric,) = pf.get_metrics(char, size=size)
        if metric is None:
            cm = CharMetrics(
                advance=float(rect.width),
                width=rect.width,
                height=rect.height,
                x=rect.x,
                y=rect.y,
            )
        else:
            cm = CharMetrics(
                advance=metric[4],
                width=rect.width,
                height=rect.height,
                x=rect.x,
                y=rect.y,
            )
        self._cached_char_metrics[key] = cm
        return cm

    def underline_metrics(self, font: DrawerFont, size: int) -> UnderlineMetrics:
        key = (font, size)
        cached = self._cached_underline_metrics.get(key)
        if cached is not None:
            return cached
        face = self._load_freetype_face(font)
        em = face.units_per_EM
        if em <= 0:
            metrics = UnderlineMetrics(offset=1, thickness=1)
        else:
            # face.underline_thickness/position come from the TTF `post` table,
            # both in font units. underline_position is signed: negative means
            # below the baseline and represents the *center* of the stroke.
            thickness = max(1, int(round(face.underline_thickness * size / em)))
            center_below_baseline = -face.underline_position * size / em
            top_below_baseline = center_below_baseline - thickness / 2
            metrics = UnderlineMetrics(
                offset=int(round(top_below_baseline)), thickness=thickness
            )
        self._cached_underline_metrics[key] = metrics
        return metrics

    def _load_pygame_font(self, font: DrawerFont) -> pygame.freetype.Font:
        pygame.freetype.init()

        pf = self._key_to_font.get(font)
        if pf is None:
            pf = pygame.freetype.Font(font.path)
            pf.origin = self._origin
            try:
                pf.strong = font.strong
                pf.oblique = font.italic
            except Exception as exc:
                logging.warning(
                    f'Unable to set strong or italic for font "{pf.name}": '
                    f"{type(exc).__name__}: {exc}"
                )
            self._key_to_font[font] = pf
            logging.debug(
                f"[pygame][font] loaded {pf.name} from {font.path}, "
                f"height {pf.get_sized_height(self._size)}, "
                f"glyph height {pf.get_sized_glyph_height(self._size)}, "
                f"ascender {pf.get_sized_ascender(self._size)}, "
                f"descender {pf.get_sized_descender(self._size)}"
            )
        return pf

    def _load_freetype_face(self, font: DrawerFont) -> freetype.Face:
        face = self._key_to_freetype_face.get(font)
        if face is None:
            face = freetype.Face(font.path)
            self._key_to_freetype_face[font] = face
        return face
