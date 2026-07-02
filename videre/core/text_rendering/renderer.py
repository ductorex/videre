"""`TextRendering` on the flat `text_partition` pipeline.

Implements `AbstractTextRendering` (`render_char` + `render_text`) by holding
the per-style config plus a shared `Shaper` / `GlyphRasterizer`, and delegating
to `render`. Holds no backend reference — `render_char`/`render_text` emit a
`Drawer` command IR, rasterized later by the backend.

The display scale enters here — the text counterpart of `Drawing`: the
font size is scaled once at the source, so the whole pipeline below works
in device pixels and glyphs rasterize pixel-native, never resampled. There
is no adapter layer: the result types carry both units themselves
(`TextDocument` converts wrap widths in, `RenderedText` converts its
widget-facing metrics out). At scale 1.0 everything is the identity.
"""

from videre.colors import Color
from videre.core.constants import TextAlign, TextSpacePolicy
from videre.core.dpi import to_device
from videre.core.drawer import Drawer
from videre.core.drawing import logical_view
from videre.core.rendering_result import AbstractTextRendering, TextRenderingResult
from videre.core.text_rendering.document import TextDocument
from videre.core.text_rendering.rasterizer import GlyphRasterizer
from videre.core.text_rendering.render import render_char
from videre.core.text_rendering.shaper import Shaper


class TextRendering(AbstractTextRendering):
    __slots__ = (
        "_size",
        "_bold",
        "_italic",
        "_height_delta",
        "_compact",
        "_subpixel",
        "_scale",
        "_shaper",
        "_rasterizer",
    )

    def __init__(
        self,
        size: int = 14,
        bold: bool = False,
        italic: bool = False,
        height_delta: int = 2,
        compact: bool = True,
        subpixel: bool = False,
        scale: float = 1.0,
        *,
        shaper: Shaper | None = None,
        rasterizer: GlyphRasterizer | None = None,
    ) -> None:
        # `size` and `height_delta` are logical; the scale is applied here,
        # once, so everything downstream is device (see module docstring).
        self._scale = float(scale)
        if self._scale == 1.0:
            self._size = size
            self._height_delta = height_delta
        else:
            self._size = to_device(size, self._scale)
            self._height_delta = to_device(height_delta, self._scale)
        self._bold = bold
        self._italic = italic
        self._compact = compact
        # Sub-pixel glyph positioning. `render_text` threads it down to `_paint_line`.
        self._subpixel = bool(subpixel)
        self._shaper = shaper or Shaper()
        self._rasterizer = rasterizer or GlyphRasterizer()

    def render_char(self, c: str, color: Color | None = None) -> Drawer:
        drawer = render_char(
            c,
            rasterizer=self._rasterizer,
            shaper=self._shaper,
            size=self._size,
            color=color,
            bold=self._bold,
            italic=self._italic,
        )
        if self._scale != 1.0:
            logical_view(drawer, self._scale)
        return drawer

    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
        underline: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[TextRenderingResult, Drawer]:
        # The document is the single rendering route; this is a one-shot wrapper
        # over it (re-shapes per call, no caching at this level). The module-level
        # `render.render_text` stays as the document's independent reference
        # oracle -- see test_document.py.
        return self.document(text).render(
            width,
            color=color,
            align=align,
            wrap_words=wrap_words,
            space_policy=space_policy,
            underline=underline,
            selection=selection,
        )

    def document(self, text: str) -> TextDocument:
        """Build a cacheable document (text-only shape, shared with the resize
        and edit-unit paths). `document.render(width, ...)` re-lays-out without
        re-shaping. See docs/text-document-and-contract.md."""
        return TextDocument(
            text,
            shaper=self._shaper,
            rasterizer=self._rasterizer,
            size=self._size,
            bold=self._bold,
            italic=self._italic,
            height_delta=self._height_delta,
            compact=self._compact,
            subpixel=self._subpixel,
            scale=self._scale,
        )
