"""`ShapedDocument`: the text-only, width-independent half of shaped rendering.

Holds the partition + shaped lines + edit units, computed once. `render(width)`
replays only the width-dependent half (collapse + wrap + reorder + paint), so a
resize never re-shapes. See docs/text-document-and-contract.md.
"""

from videre.colors import Color
from videre.core.abstract_backend import AbstractBackend
from videre.core.constants import TextAlign, TextSpacePolicy
from videre.core.rendering_result import AbstractTextDocument, Rendering
from videre.core.shaping.rasterizer import GlyphRasterizer
from videre.core.shaping.render import layout_glyph_lines, paint_glyph_lines
from videre.core.shaping.rendering.layout import RenderedText
from videre.core.shaping.shaper import Shaper, shape_line
from videre.core.shaping.text_partition.partitioner import partition_text
from videre.core.text_editing import EditUnit


class ShapedDocument(AbstractTextDocument):
    __slots__ = (
        "_text",
        "_edit_units",
        "_shaped_lines",
        "_backend",
        "_rasterizer",
        "_size",
        "_bold",
        "_height_delta",
        "_compact",
        "_subpixel",
    )

    def __init__(
        self,
        text: str,
        *,
        backend: AbstractBackend,
        shaper: Shaper,
        rasterizer: GlyphRasterizer,
        size: int,
        bold: bool = False,
        italic: bool = False,
        height_delta: int = 2,
        compact: bool = True,
        subpixel: bool = False,
    ) -> None:
        # Text-only work, done once: partition (+ edit-unit segmentation) and
        # HarfBuzz shaping per logical line. italic is baked into the glyphs.
        partition = partition_text(text)
        self._text = text
        self._edit_units = partition.edit_units
        self._shaped_lines = [
            shape_line(line, shaper, size, bold=bold, italic=italic)
            for line in partition.lines
        ]
        self._backend = backend
        self._rasterizer = rasterizer
        self._size = size
        self._bold = bold
        self._height_delta = height_delta
        self._compact = compact
        self._subpixel = subpixel

    @property
    def text(self) -> str:
        return self._text

    @property
    def edit_units(self) -> tuple[EditUnit, ...]:
        return self._edit_units

    def render(
        self,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
        underline: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[RenderedText, Rendering]:
        lines = layout_glyph_lines(
            self._shaped_lines,
            width=width,
            wrap_words=wrap_words,
            space_policy=space_policy,
        )
        return paint_glyph_lines(
            lines,
            backend=self._backend,
            rasterizer=self._rasterizer,
            size=self._size,
            color=color,
            width=width,
            align=align,
            underline=underline,
            bold=self._bold,
            height_delta=self._height_delta,
            compact=self._compact,
            subpixel=self._subpixel,
            edit_units=self._edit_units,
            selection=selection,
        )
