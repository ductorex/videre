"""Caret / hit-test for the flat glyph model — implements `TextRenderingResult`.

`render_text` builds a `RenderedText` from the painted glyph lines: per display
line, a `baseline`-derived box and a list of `_Item`s (one per cluster / gap)
carrying source range + pixel range + direction. Navigation is entirely
glyph-cursor based: a `GlyphCursor(line, glyph_index)` indexes caret positions
in visual order, and every public method builds/moves/reads a `CursorState`
around it.

Simpler than the legacy `text_rendering/layout.py`:

- glyphs arrive already in visual order (post `reorder_line`), so there is no
  `_apply_l2_to_line` and no parallel word/run source-offset bookkeeping;
- source ranges are intrinsic to each glyph cluster, so invisible controls and
  multi-codepoint editing units never depend on the next painted glyph;
- the caret never needs `pos_to_pixel` / `pixel_to_pos` (those only backed the
  removed public contract) — the glyph-cursor path covers everything.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from cursword import get_next_word_end_position, get_previous_word_start_position

from videre.core.caret_position import CaretPosition
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import CursorState, TextRenderingResult
from videre.core.text_editing import EditUnit


@dataclass(slots=True, frozen=True)
class FontMetrics:
    """Reference-font metrics for sizing cursors and the surface-less path."""

    ascender: int
    descender: int
    height_delta: int
    line_spacing: int


@dataclass(slots=True)
class _Item:
    """One cluster (or gap) on a line. `source_start < source_end` regardless
    of direction; `x_start < x_end` in pixels relative to the line's
    `x_offset`. For a RTL cluster the source start sits at the visual right
    edge (`x_end`), the source end at the left edge (`x_start`)."""

    source_start: int
    source_end: int
    x_start: int
    x_end: int
    is_rtl: bool


@dataclass(slots=True, frozen=True)
class _LineLayout:
    y_top: int
    y_bottom: int
    x_offset: int
    source_offset: int
    source_length: int
    items: tuple[_Item, ...]
    terminator_at_end: bool


@dataclass(slots=True, frozen=True)
class GlyphCursor:
    """A caret position in visual order: `glyph_index` in `[0, len(items)]`
    on line `line_index`. Index `i` is the left edge of `items[i]` (or the
    right edge of `items[-1]` when `i == len(items)`)."""

    line_index: int
    glyph_index: int


@dataclass(slots=True, frozen=True)
class _CursorState(CursorState):
    glyph: GlyphCursor
    pos: int
    visual_pos: int
    pixel: CaretPosition


@dataclass(slots=True, frozen=True)
class RenderedText(TextRenderingResult):
    font_metrics: FontMetrics
    line_layouts: tuple[_LineLayout, ...]
    width: int = 0
    height: int = 0

    # -- size contract -------------------------------------------------------

    def get_width(self) -> int:
        return self.width

    def get_height(self) -> int:
        return self.height

    # -- state builders (contract) ------------------------------------------

    def visual_state(self, pos: int) -> CursorState:
        return self._make_state(self._source_to_glyph(pos))

    def visual_state_at(self, visual_pos: int) -> CursorState:
        if not self.line_layouts:
            return self._make_state(GlyphCursor(0, 0))
        remaining = max(0, visual_pos)
        for line_idx, line in enumerate(self.line_layouts):
            if remaining < len(line.items):
                return self._make_state(GlyphCursor(line_idx, remaining))
            if remaining == len(line.items):
                if line.terminator_at_end and line_idx + 1 < len(self.line_layouts):
                    return self._make_state(GlyphCursor(line_idx + 1, 0))
                return self._make_state(GlyphCursor(line_idx, remaining))
            remaining -= len(line.items)
        last = len(self.line_layouts) - 1
        return self._make_state(GlyphCursor(last, len(self.line_layouts[-1].items)))

    def visual_state_at_pixel(self, x: int, y: int) -> CursorState:
        return self._make_state(self._pixel_to_glyph(x, y))

    # -- navigation (contract) ----------------------------------------------

    def next_visual(self, state: CursorState) -> CursorState:
        return self._make_state(self._next_glyph(cast(_CursorState, state).glyph))

    def prev_visual(self, state: CursorState) -> CursorState:
        return self._make_state(self._prev_glyph(cast(_CursorState, state).glyph))

    def next_visual_word(self, state: CursorState, text: str) -> CursorState:
        word_ends = _collect_word_ends(text)
        glyph = cast(_CursorState, state).glyph
        while True:
            new_glyph = self._next_glyph(glyph)
            if new_glyph == glyph:
                return self._make_state(glyph)
            glyph = new_glyph
            if self._glyph_to_source(glyph) in word_ends:
                return self._make_state(glyph)

    def prev_visual_word(self, state: CursorState, text: str) -> CursorState:
        word_starts = _collect_word_starts(text)
        glyph = cast(_CursorState, state).glyph
        while True:
            new_glyph = self._prev_glyph(glyph)
            if new_glyph == glyph:
                return self._make_state(glyph)
            glyph = new_glyph
            if self._glyph_to_source(glyph) in word_starts:
                return self._make_state(glyph)

    # -- selection / count (contract) ---------------------------------------

    def visual_range_to_source_set(self, start: int, end: int) -> frozenset[int]:
        if start >= end:
            return frozenset()
        sources: set[int] = set()
        lo, hi = start, end
        for line in self.line_layouts:
            n = len(line.items)
            if lo >= n:
                lo -= n
                hi -= n
                continue
            for i in range(lo, min(hi, n)):
                item = line.items[i]
                sources.update(range(item.source_start, item.source_end))
            lo = 0
            hi -= n
            if hi <= 0:
                break
        return frozenset(sources)

    def total_visual_count(self) -> int:
        return sum(len(ln.items) for ln in self.line_layouts)

    # -- internal: selection rectangles (painted by render_text) ------------

    def _selection_rects(self, start: int, end: int) -> list[Rectangle]:
        """One pixel ribbon per line touched by the half-open visual range
        `[start, end)`. Items are in visual pixel order, so the span from the
        first to the last selected item is contiguous."""
        if start >= end:
            return []
        rects: list[Rectangle] = []
        lo, hi = start, end
        for line in self.line_layouts:
            n = len(line.items)
            if lo >= n:
                lo -= n
                hi -= n
                continue
            upper = min(hi, n)
            if upper > lo:
                x_start = line.x_offset + line.items[lo].x_start
                x_end = line.x_offset + line.items[upper - 1].x_end
                rects.append(
                    Rectangle(
                        x_start, line.y_top, x_end - x_start, line.y_bottom - line.y_top
                    )
                )
            lo = 0
            hi -= n
            if hi <= 0:
                break
        return rects

    # -- internal: glyph-cursor primitives ----------------------------------

    def _make_state(self, glyph: GlyphCursor) -> _CursorState:
        visual_pos = (
            sum(len(ln.items) for ln in self.line_layouts[: glyph.line_index])
            + glyph.glyph_index
        )
        return _CursorState(
            glyph=glyph,
            pos=self._glyph_to_source(glyph),
            visual_pos=visual_pos,
            pixel=self._glyph_caret_pixel(glyph),
        )

    def _glyph_caret_pixel(self, cursor: GlyphCursor) -> CaretPosition:
        if not self.line_layouts:
            return CaretPosition(x=0, y_top=0, y_bottom=self.font_metrics.line_spacing)
        line = self._clamp_line(cursor.line_index)
        if not line.items:
            return CaretPosition(
                x=line.x_offset, y_top=line.y_top, y_bottom=line.y_bottom
            )
        if cursor.glyph_index >= len(line.items):
            x = line.x_offset + line.items[-1].x_end
        else:
            x = line.x_offset + line.items[max(0, cursor.glyph_index)].x_start
        return CaretPosition(x=x, y_top=line.y_top, y_bottom=line.y_bottom)

    def _pixel_to_glyph(self, x: int, y: int) -> GlyphCursor:
        if not self.line_layouts:
            return GlyphCursor(0, 0)
        line_idx = self._line_index_at_y(y)
        line = self.line_layouts[line_idx]
        if not line.items:
            return GlyphCursor(line_idx, 0)
        rel_x = x - line.x_offset
        if rel_x <= line.items[0].x_start:
            return GlyphCursor(line_idx, 0)
        if rel_x >= line.items[-1].x_end:
            return GlyphCursor(line_idx, len(line.items))
        for gi, item in enumerate(line.items):
            if item.x_start <= rel_x <= item.x_end:
                if rel_x - item.x_start <= item.x_end - rel_x:
                    return GlyphCursor(line_idx, gi)
                return GlyphCursor(line_idx, gi + 1)
        return GlyphCursor(line_idx, len(line.items))

    def _glyph_to_source(self, cursor: GlyphCursor) -> int:
        if not self.line_layouts:
            return 0
        line = self._clamp_line(cursor.line_index)
        if not line.items:
            return line.source_offset
        if cursor.glyph_index >= len(line.items):
            return _right_edge_source(line.items[-1])
        return _left_edge_source(line.items[max(0, cursor.glyph_index)])

    def _source_to_glyph(self, pos: int) -> GlyphCursor:
        if not self.line_layouts:
            return GlyphCursor(0, 0)
        line_idx = 0
        for li, ln in enumerate(self.line_layouts):
            if ln.source_offset <= pos <= ln.source_offset + ln.source_length:
                line_idx = li
                if pos < ln.source_offset + ln.source_length:
                    break
        line = self.line_layouts[line_idx]
        if not line.items:
            return GlyphCursor(line_idx, 0)
        for gi, item in enumerate(line.items):
            if _left_edge_source(item) == pos:
                return GlyphCursor(line_idx, gi)
        if _right_edge_source(line.items[-1]) == pos:
            return GlyphCursor(line_idx, len(line.items))
        for gi, item in enumerate(line.items):
            if item.source_start <= pos <= item.source_end:
                left_dist = pos - item.source_start
                right_dist = item.source_end - pos
                if item.is_rtl:
                    return GlyphCursor(
                        line_idx, gi if right_dist <= left_dist else gi + 1
                    )
                return GlyphCursor(line_idx, gi if left_dist <= right_dist else gi + 1)
        return GlyphCursor(
            line_idx, 0 if pos <= line.source_offset else len(line.items)
        )

    def _next_glyph(self, cursor: GlyphCursor) -> GlyphCursor:
        if not self.line_layouts:
            return cursor
        line = self._clamp_line(cursor.line_index)
        if cursor.glyph_index < len(line.items):
            next_index = cursor.glyph_index + 1
            if (
                next_index == len(line.items)
                and line.terminator_at_end
                and cursor.line_index + 1 < len(self.line_layouts)
            ):
                return GlyphCursor(cursor.line_index + 1, 0)
            return GlyphCursor(cursor.line_index, next_index)
        if cursor.line_index + 1 < len(self.line_layouts):
            return GlyphCursor(cursor.line_index + 1, 0)
        return cursor

    def _prev_glyph(self, cursor: GlyphCursor) -> GlyphCursor:
        if not self.line_layouts:
            return cursor
        if cursor.glyph_index > 0:
            return GlyphCursor(cursor.line_index, cursor.glyph_index - 1)
        if cursor.line_index > 0:
            prev = self.line_layouts[cursor.line_index - 1]
            previous_index = (
                len(prev.items) - 1 if prev.terminator_at_end else len(prev.items)
            )
            return GlyphCursor(cursor.line_index - 1, previous_index)
        return cursor

    def _clamp_line(self, line_index: int) -> _LineLayout:
        if line_index < 0:
            return self.line_layouts[0]
        if line_index >= len(self.line_layouts):
            return self.line_layouts[-1]
        return self.line_layouts[line_index]

    def _line_index_at_y(self, y: int) -> int:
        for li, ln in enumerate(self.line_layouts):
            if ln.y_top <= y < ln.y_bottom:
                return li
            if y < ln.y_top:
                return max(0, li - 1) if li > 0 else 0
        return len(self.line_layouts) - 1


def _collect_word_ends(text: str) -> frozenset[int]:
    ends: set[int] = {len(text)}
    pos = 0
    while True:
        nxt = get_next_word_end_position(text, pos)
        if nxt <= pos:
            break
        ends.add(nxt)
        pos = nxt
    return frozenset(ends)


def _collect_word_starts(text: str) -> frozenset[int]:
    starts: set[int] = {0}
    pos = len(text)
    while True:
        prv = get_previous_word_start_position(text, pos)
        if prv >= pos:
            break
        starts.add(prv)
        pos = prv
    return frozenset(starts)


def _left_edge_source(item: _Item) -> int:
    """Source position at the visual left edge (`x_start`) of `item`."""
    return item.source_end if item.is_rtl else item.source_start


def _right_edge_source(item: _Item) -> int:
    """Source position at the visual right edge (`x_end`) of `item`."""
    return item.source_start if item.is_rtl else item.source_end


# ---------------------------------------------------------------------------
# Construction from painted lines
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RawLine:
    """A painted display line, as collected by `render_text`: its vertical box
    and explicit source and pixel ranges for every visual item."""

    y_top: int
    y_bottom: int
    x_offset: int
    clusters: list[tuple[int, int, int, int, bool]]
    source_start: int
    source_end: int
    terminator: EditUnit | None
    terminator_at_visual_start: bool


def build_rendered_text(
    raw_lines: list[RawLine], font_metrics: FontMetrics, width: int, height: int
) -> RenderedText:
    """Assemble a `RenderedText` from explicit source ranges."""
    line_layouts: list[_LineLayout] = []
    for rl in raw_lines:
        items = tuple(
            _Item(source_start, source_end, x_start, x_end, is_rtl)
            for source_start, source_end, x_start, x_end, is_rtl in rl.clusters
        )
        line_layouts.append(
            _LineLayout(
                y_top=rl.y_top,
                y_bottom=rl.y_bottom,
                x_offset=rl.x_offset,
                source_offset=rl.source_start,
                source_length=rl.source_end - rl.source_start,
                items=items,
                terminator_at_end=(
                    rl.terminator is not None and not rl.terminator_at_visual_start
                ),
            )
        )
    return RenderedText(font_metrics, tuple(line_layouts), width, height)
