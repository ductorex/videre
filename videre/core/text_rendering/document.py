"""`TextDocument`: the text-only, width-independent half of shaped rendering.

Holds the partition + shaped lines + edit units, computed once. `render(width)`
replays only the width-dependent half (collapse + wrap + reorder + paint), so a
resize never re-shapes. See docs/text-document-and-contract.md.

Two units, like `Drawer`: everything inside is device pixels (`size`
arrives already scaled); the widget-facing boundary is logical — wrap
widths convert on the way in (floor, so wrapped content fits back in the
logical box), results carry their logical view on the way out. At scale
1.0 all of this is the identity.
"""

from dataclasses import replace

from videre.colors import Color
from videre.core.constants import TextAlign, TextSpacePolicy
from videre.core.dpi import DevicePx, LogicalPx, to_device_floor
from videre.core.drawer import Drawer
from videre.core.drawing import logical_view
from videre.core.rendering_result import AbstractTextDocument
from videre.core.text_editing import EditUnit
from videre.core.text_rendering.rasterizer import GlyphRasterizer
from videre.core.text_rendering.render import (
    AssembledText,
    assemble_glyph_lines,
    layout_glyph_lines,
    paint_assembled,
)
from videre.core.text_rendering.rendering.layout import RenderedText
from videre.core.text_rendering.shaper import Shaper, shape_line
from videre.core.text_rendering.text_partition.partitioner import partition_text


class TextDocument(AbstractTextDocument):
    __slots__ = (
        "_text",
        "_edit_units",
        "_shaped_lines",
        "_rasterizer",
        "_size",
        "_bold",
        "_height_delta",
        "_compact",
        "_subpixel",
        "_scale",
        "_assembled",
        "_assembled_key",
    )

    def __init__(
        self,
        text: str,
        *,
        shaper: Shaper,
        rasterizer: GlyphRasterizer,
        size: int,
        bold: bool = False,
        italic: bool = False,
        height_delta: int = 2,
        compact: bool = True,
        subpixel: bool = False,
        scale: float = 1.0,
    ) -> None:
        # Text-only work, done once: partition (+ edit-unit segmentation) and
        # HarfBuzz shaping per source line. italic is baked into the glyphs.
        partition = partition_text(text)
        self._text = text
        self._edit_units = partition.edit_units
        self._shaped_lines = [
            shape_line(line, shaper, size, bold=bold, italic=italic)
            for line in partition.lines
        ]
        self._rasterizer = rasterizer
        self._size = size
        self._bold = bold
        self._height_delta = height_delta
        self._compact = compact
        self._subpixel = subpixel
        self._scale = float(scale)
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
            assembled = assemble_glyph_lines(
                lines,
                size=self._size,
                width=width,
                align=align,
                height_delta=self._height_delta,
                compact=self._compact,
                edit_units=self._edit_units,
            )
            if self._scale != 1.0:
                # The pipeline is scale-free; the document owns the scale
                # and tags the result (`RenderedText.scale` drives its
                # logical conversions).
                assembled = replace(
                    assembled, rendered=replace(assembled.rendered, scale=self._scale)
                )
            self._assembled = assembled
            self._assembled_key = key
        return self._assembled

    def _device_width(self, width: LogicalPx | None) -> DevicePx | None:
        """An incoming logical wrap width in device pixels (floor)."""
        if width is None or self._scale == 1.0:
            return width
        return to_device_floor(width, self._scale)

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
        measurement that must not force a repaint (see the contract doc).
        `width` is logical, like all widget-facing measures."""
        width = self._device_width(width)
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
    ) -> tuple[RenderedText, Drawer]:
        width = self._device_width(width)
        assembled = self._lay_out(width, wrap_words, space_policy, align)
        out = paint_assembled(
            assembled,
            rasterizer=self._rasterizer,
            size=self._size,
            color=color,
            underline=underline,
            bold=self._bold,
            subpixel=self._subpixel,
            selection=selection,
        )
        if self._scale != 1.0:
            logical_view(out, self._scale)
        return assembled.rendered, out
