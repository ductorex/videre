"""`ShapedTextRendering` on the flat `text_partition` pipeline.

Implements `AbstractTextRendering` (`render_char` + `render_text`) by holding
the per-style config plus a shared `Shaper` / `GlyphRasterizer`, and delegating
to `render`. Backend-agnostic (only goes through `AbstractBackend`).
"""

from videre.colors import Color
from videre.core.abstract_backend import AbstractBackend
from videre.core.constants import TextAlign, TextSpacePolicy
from videre.core.rendering_result import AbstractTextRendering, Rendering
from videre.core.shaping.rasterizer import GlyphRasterizer
from videre.core.shaping.render import render_char, render_text
from videre.core.shaping.rendering.layout import RenderedText
from videre.core.shaping.shaper import Shaper


class ShapedTextRendering(AbstractTextRendering):
    __slots__ = (
        "_backend",
        "_size",
        "_bold",
        "_italic",
        "_underline",
        "_height_delta",
        "_compact",
        "_subpixel",
        "_shaper",
        "_rasterizer",
    )

    def __init__(
        self,
        backend: AbstractBackend,
        size: int = 14,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int = 2,
        compact: bool = True,
        subpixel: bool = False,
        *,
        shaper: Shaper | None = None,
        rasterizer: GlyphRasterizer | None = None,
    ) -> None:
        self._backend = backend
        self._size = size
        self._bold = bold
        self._italic = italic
        self._underline = underline
        self._height_delta = height_delta
        self._compact = compact
        # Sub-pixel glyph positioning. `render_text` threads it down to `_paint_line`.
        self._subpixel = bool(subpixel)
        self._shaper = shaper or Shaper()
        self._rasterizer = rasterizer or GlyphRasterizer()

    def render_char(self, c: str, color: Color | None = None) -> Rendering:
        return render_char(
            c,
            backend=self._backend,
            rasterizer=self._rasterizer,
            shaper=self._shaper,
            size=self._size,
            color=color,
            bold=self._bold,
            italic=self._italic,
        )

    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
        selection: tuple[int, int] | None = None,
    ) -> tuple[RenderedText, Rendering]:
        return render_text(
            text,
            backend=self._backend,
            rasterizer=self._rasterizer,
            shaper=self._shaper,
            size=self._size,
            color=color,
            width=width,
            wrap_words=wrap_words,
            space_policy=space_policy,
            align=align,
            bold=self._bold,
            italic=self._italic,
            underline=self._underline,
            height_delta=self._height_delta,
            compact=self._compact,
            subpixel=self._subpixel,
            selection=selection,
        )
