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
from videre.core.shaping.render import (
    AssembledText,
    assemble_glyph_lines,
    layout_glyph_lines,
    paint_assembled,
)
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
        "_assembled",
        "_assembled_key",
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
        # Shared width-dependent layout cache (single entry), filled by `_lay_out`
        # and read by both `layout` and `render`. The document is immutable per
        # (text, size, …), so it never needs explicit invalidation.
        self._assembled: AssembledText | None = None
        self._assembled_key: tuple | None = None

    @property
    def text(self) -> str:
        return self._text

    @property
    def edit_units(self) -> tuple[EditUnit, ...]:
        return self._edit_units

    def _lay_out(
        self,
        width: int | None,
        wrap_words: bool,
        space_policy: TextSpacePolicy,
        align: TextAlign | None,
    ) -> AssembledText:
        """Width + align dependent layout — collapse + wrap + reorder + geometry,
        but NO painting. Memoized on its full key and shared by `layout` and
        `render`: within a frame the key is stable, so pairing them (navigate then
        draw) costs a single layout. The shape is already cached, so this never
        re-shapes — only wrap + geometry run. The document is immutable per
        (text, size, strong, italic, height_delta) (a mutation builds a new
        document), so a single-entry cache invalidates at the right granularity."""
        key = (width, wrap_words, space_policy, align)
        if self._assembled is None or self._assembled_key != key:
            lines = layout_glyph_lines(
                self._shaped_lines,
                width=width,
                wrap_words=wrap_words,
                space_policy=space_policy,
            )
            self._assembled = assemble_glyph_lines(
                lines,
                size=self._size,
                width=width,
                align=align,
                height_delta=self._height_delta,
                compact=self._compact,
                edit_units=self._edit_units,
            )
            self._assembled_key = key
        return self._assembled

    def layout(
        self,
        width: int | None = None,
        *,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
    ) -> RenderedText:
        """Width-dependent layout WITHOUT painting — just the caret / hit-test
        `RenderedText`, from the same cache `render` paints from. For navigation /
        measurement that must not force a repaint (see the contract doc)."""
        return self._lay_out(width, wrap_words, space_policy, align).rendered

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
        assembled = self._lay_out(width, wrap_words, space_policy, align)
        out = paint_assembled(
            assembled,
            backend=self._backend,
            rasterizer=self._rasterizer,
            size=self._size,
            color=color,
            underline=underline,
            bold=self._bold,
            subpixel=self._subpixel,
            selection=selection,
        )
        return assembled.rendered, out
