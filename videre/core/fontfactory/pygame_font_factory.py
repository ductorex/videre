import logging
from dataclasses import dataclass

import pygame
import pygame.freetype
import pygame.surfarray

from videre.core.abstract_font_factory import (
    AbstractFontFactory,
    CharMetrics,
    LineMetrics,
    UnderlineMetrics,
)
from videre.core.drawer import DrawerFont
from videre.core.pygame_utils import PygameUtils
from videre.fonts.provider import FontProvider


@dataclass(slots=True)
class CharMeasures:
    font: pygame.freetype.Font
    rect: pygame.Rect
    metrics: tuple[int, int, int, int, float, float]


class PygameFontFactory(AbstractFontFactory):
    __slots__ = (
        "_prov",
        "_key_to_font",
        "_size",
        "_origin",
        "_base_font",
        "_cached_char_measures",
        "_cached_underline_metrics",
    )

    def __init__(self, size: int = 14):
        super().__init__()
        self._prov = FontProvider()
        self._key_to_font: dict[DrawerFont, pygame.freetype.Font] = {}
        self._size = size
        self._origin = True
        self._base_font: pygame.freetype.Font | None = None

        self._cached_char_measures: dict[tuple[str, int, bool, bool], CharMeasures] = {}
        self._cached_underline_metrics: dict[
            tuple[DrawerFont, int], UnderlineMetrics
        ] = {}

    @property
    def base_font(self) -> pygame.freetype.Font:
        if self._base_font is None:
            self._base_font = self.get_font(" ")
        return self._base_font

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
        pf = self._load_pygame_font(font)
        rect = pf.get_rect(char, size=size)
        (metric,) = pf.get_metrics(char, size=size)
        if metric is None:
            return CharMetrics(
                advance=float(rect.width),
                width=rect.width,
                height=rect.height,
                x=rect.x,
                y=rect.y,
                horizontal_shift=0.0,
            )
        return CharMetrics(
            advance=metric[4],
            width=rect.width,
            height=rect.height,
            x=rect.x,
            y=rect.y,
            horizontal_shift=float(metric[0]),
        )

    def underline_metrics(self, font: DrawerFont, size: int) -> UnderlineMetrics:
        key = (font, size)
        cached = self._cached_underline_metrics.get(key)
        if cached is not None:
            return cached
        pf = self._load_pygame_font(font)
        ascender = abs(pf.get_sized_ascender(size))
        descender = abs(pf.get_sized_descender(size))
        # Render a probe glyph (ascender-only, no descender) to a canvas with
        # the baseline at a known y, with and without pygame's native underline.
        # The rows that newly contain pixels reveal the underline's extent
        # relative to the baseline.
        baseline_y = ascender + 5
        canvas_h = ascender + descender + 20
        canvas_w = 50
        previous_underline = pf.underline
        try:
            pf.underline = False
            no_underline = pygame.Surface((canvas_w, canvas_h), flags=pygame.SRCALPHA)
            pf.render_to(no_underline, (5, baseline_y), "M", size=size)
            with_underline = pygame.Surface((canvas_w, canvas_h), flags=pygame.SRCALPHA)
            pf.underline = True
            pf.render_to(with_underline, (5, baseline_y), "M", size=size)
        finally:
            pf.underline = previous_underline
        alpha_no = pygame.surfarray.array_alpha(no_underline)
        alpha_u = pygame.surfarray.array_alpha(with_underline)
        rows_no = alpha_no.sum(axis=0)
        rows_u = alpha_u.sum(axis=0)
        diff = [i for i in range(canvas_h) if int(rows_u[i]) > int(rows_no[i])]
        if not diff:
            # Fallback: 1px stroke directly under the baseline.
            metrics = UnderlineMetrics(offset=1, thickness=1)
        else:
            metrics = UnderlineMetrics(
                offset=diff[0] - baseline_y, thickness=diff[-1] - diff[0] + 1
            )
        self._cached_underline_metrics[key] = metrics
        return metrics

    def get_font(
        self, c: str, strong: bool = False, italic: bool = False
    ) -> pygame.freetype.Font:
        return self._load_pygame_font(self.resolve(c, strong=strong, italic=italic))

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
