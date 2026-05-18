"""Layout-info return type for `ShapedTextRendering.render_text`.

The legacy `PygameTextRendering` returned a `RenderedText` with the
char-level `lines` it had built during shaping, and `TextInput`
walked that tree (via the now-removed `cursor_event.py`) to map
between source positions and pixel coordinates. Both renderers now
expose `pos_to_pixel` / `pixel_to_pos` helpers directly on their
return type, so consumers no longer touch the internal layout.

The shaped pipeline produces clusters, not characters, so a literal
char-level mapping isn't always meaningful (a HarfBuzz cluster groups
either a base + combining marks, or several codepoints fused into one
glyph by a ligature substitution). Instead, this module exposes:

- `ShapedRenderedText` — the layout half of `render_text`'s return
  value. Carries the font metrics every consumer needs to size cursors
  / selection blocks, and the per-line layout used by the helpers.

- `pos_to_pixel(pos)` and `pixel_to_pos(x, y)` helpers that paper over
  the cluster vs character mismatch with linear interpolation: a caret
  inside a multi-codepoint cluster sits at a fractional pixel position
  proportional to how far the codepoint is from the cluster's start,
  matching what CSS / browsers / Word do for ligatures and complex
  scripts. Pixel-to-position snaps to the nearer boundary.

Source positions follow the `TextSequence` convention (printable
codepoints in source order, `\\n` between source lines, no
whitespace-collapse). The renderer translates `space_before`-driven
gaps into pseudo-items that occupy one source position and the
inter-word advance in pixels, so a cursor placed in the inter-word
slot lands visually inside the gap rather than snapping to either
adjacent word.
"""

from dataclasses import dataclass

from videre.core.caret_position import CaretPosition


@dataclass(slots=True, frozen=True)
class FontMetrics:
    """Reference-font metrics needed to size cursors and selection
    rectangles, mirroring the legacy `FontSizes` fields."""

    ascender: int
    descender: int
    height_delta: int
    line_spacing: int


@dataclass(slots=True, frozen=True)
class _LineItem:
    """One cluster (or one inter-word gap) on a line. `source_start`
    and `source_end` are positions in the post-printable-filter
    document (the same convention `TextSequence` indexes into), with
    `source_start < source_end` regardless of the item's visual
    direction. `x_start` / `x_end` are pixel positions within the
    line, relative to the line's `x_offset`, with
    `x_start < x_end`. For an inter-word gap, the source range
    has length 1 (the whitespace position) and the pixel range has
    width `space_advance` (plus any JUSTIFY extra).

    `bidi_level` is the UAX#9 resolved embedding level (even = LTR,
    odd = RTL). The `right_to_left` property derives from it. Caret /
    hit-test helpers use direction to flip the "source_start <->
    x_start" mapping that holds for LTR: in a RTL cluster the source's
    start sits at the visual right edge (`x_end`) and the source's end
    sits at the visual left edge (`x_start`). Inter-word gaps inherit
    the line's base level."""

    source_start: int
    source_end: int
    x_start: int
    x_end: int
    bidi_level: int = 0

    @property
    def right_to_left(self) -> bool:
        return self.bidi_level % 2 == 1


@dataclass(slots=True, frozen=True)
class _LineLayout:
    """Per-line layout info. `y_top` / `y_bottom` are the absolute
    pixel rows the line occupies in the rendered surface (top-inclusive,
    bottom-exclusive). `x_offset` is the line's left edge in surface
    coordinates after horizontal alignment (LEFT = 0, CENTER /
    RIGHT shift). `source_offset` is the first source position
    covered by this line."""

    y_top: int
    y_bottom: int
    x_offset: int
    source_offset: int
    source_length: int
    items: tuple[_LineItem, ...]


@dataclass(slots=True, frozen=True)
class GlyphCursor:
    """A caret position expressed in visual order: an index into a
    line's visually-ordered `items`. Used by glyph-based navigation
    (TextInput) where arrow keys move ``glyph_index`` by ±1 visually
    regardless of script direction.

    `glyph_index` ranges over ``[0, len(line.items)]``: index ``i``
    means "the gap to the *left* of items[i]" (or "to the *right* of
    items[-1]" when ``i == len(items)``). So a line with N items has
    N+1 valid caret positions.

    Two adjacent items belonging to runs of opposite direction define
    one visual position where ``glyph_index = i`` (right edge of
    items[i-1]) and ``glyph_index = i`` (left edge of items[i]) refer
    to the same pixel but typically different source positions — this
    is the "caret affinity" ambiguity of bidi text. The single
    ``glyph_index`` collapses both into the same value; consumers that
    need to disambiguate can inspect the surrounding items.
    """

    line_index: int
    glyph_index: int


@dataclass(slots=True, frozen=True)
class ShapedRenderedText:
    """Return type of `ShapedTextRendering.render_text`.

    Carries font metrics that consumers need to size cursors /
    selection rectangles, and the per-line layout used by the
    `pos_to_pixel` / `pixel_to_pos` helpers. The rendered bitmap is
    returned as the second item from `render_text`.
    """

    font_metrics: FontMetrics
    line_layouts: tuple[_LineLayout, ...]

    def pos_to_pixel(self, pos: int) -> CaretPosition:
        """Caret position for a logical source `pos`.

        `pos` is clamped to ``[first_line.source_offset,
        last_line.source_offset + last_line.source_length]``. When
        `pos` falls strictly inside a multi-codepoint cluster (a
        ligature, an Indic conjunct), the x is interpolated linearly
        between the cluster's pixel `x_start` and `x_end` — the
        cluster's only glyph is not split, only the caret sits at a
        fractional position. Empty layouts return a caret at (0, 0,
        line_spacing) so consumers don't have to special-case empty
        text.
        """
        if not self.line_layouts:
            return CaretPosition(x=0, y_top=0, y_bottom=self.font_metrics.line_spacing)
        first = self.line_layouts[0]
        last = self.line_layouts[-1]
        first_pos = first.source_offset
        last_pos = last.source_offset + last.source_length
        pos = max(first_pos, min(pos, last_pos))
        # Pick the line whose [source_offset, source_offset + length]
        # range contains `pos`. When `pos` lies on a boundary shared by
        # the end of line N and the start of line N+1 (eg. an explicit
        # newline between two paragraphs) we keep the caret on line N
        # — matches what editors do for "end of line" cursoring.
        line = first
        for ln in self.line_layouts:
            if ln.source_offset <= pos <= ln.source_offset + ln.source_length:
                line = ln
                if pos < ln.source_offset + ln.source_length:
                    break
                # else keep scanning in case the next line also matches
                # at its start — but we'll fall back to this one below.
                # (We don't break: if no later line strictly contains
                # `pos`, we've already picked the right one.)
        return CaretPosition(
            x=_caret_x_in_line(line, pos), y_top=line.y_top, y_bottom=line.y_bottom
        )

    def pixel_to_pos(self, x: int, y: int) -> int:
        """Source position closest to a pixel coordinate.

        `y` clamps to the nearest line (above-first → first line,
        below-last → last line). Within a line, `x` snaps to the
        nearest item boundary. For a LTR item, the left half yields
        `source_start` and the right half `source_end`; for a RTL
        item the mapping is flipped (left half = `source_end`,
        right half = `source_start`) so the source position the
        caret lands on always matches the visual edge the click
        was closer to. Empty layouts always return 0.
        """
        if not self.line_layouts:
            return 0
        line = self.line_layouts[0]
        for ln in self.line_layouts:
            if ln.y_top <= y < ln.y_bottom:
                line = ln
                break
            if y < ln.y_top:
                # `y` is above this line; if it's also above the first
                # line, stick with the first; otherwise keep what we
                # had (the previous line).
                if ln is self.line_layouts[0]:
                    line = ln
                break
            line = ln  # tentative, will be overwritten if a later line catches y
        rel_x = x - line.x_offset
        if not line.items:
            return line.source_offset
        # Items are sorted by source_start, but their pixel ranges may
        # run right-to-left for RTL content, so the visually-leftmost /
        # rightmost items can sit anywhere in the list. Scan all items
        # and pick by pixel extent.
        leftmost = min(line.items, key=lambda it: it.x_start)
        rightmost = max(line.items, key=lambda it: it.x_end)
        if rel_x <= leftmost.x_start:
            return _left_edge_source(leftmost)
        if rel_x >= rightmost.x_end:
            return _right_edge_source(rightmost)
        for item in line.items:
            if item.x_start <= rel_x <= item.x_end:
                if rel_x - item.x_start <= item.x_end - rel_x:
                    return _left_edge_source(item)
                return _right_edge_source(item)
        return line.source_offset + line.source_length

    # ------------------------------------------------------------------
    # Glyph-based navigation (visual order)
    # ------------------------------------------------------------------

    def glyph_caret_pixel(self, cursor: GlyphCursor) -> CaretPosition:
        """Pixel caret for a glyph cursor: x sits at the *visual* left
        edge of ``items[glyph_index]``, or at the right edge of
        ``items[-1]`` when ``glyph_index == len(items)``. Empty layouts
        / empty lines park the caret at the line's left edge."""
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

    def pixel_to_glyph(self, x: int, y: int) -> GlyphCursor:
        """Snap a pixel coordinate to the nearest glyph-cursor
        position. `y` selects the line (same clamping as
        `pixel_to_pos`); within a line, `x` snaps to the nearest
        boundary between two items in visual order. Independent of
        script direction — `glyph_index` is purely a visual index."""
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
        # Defensive: items are emitted contiguously so this should not
        # be reached. Clamp to end of line.
        return GlyphCursor(line_idx, len(line.items))

    def glyph_to_source(self, cursor: GlyphCursor) -> int:
        """Source position associated with a glyph cursor. Convention:
        the cursor sits *before* ``items[glyph_index]`` visually, so
        we return the source position at the visual *left* edge of
        that item (which is `source_start` for LTR, `source_end` for
        RTL). For ``glyph_index == len(items)`` we take the right edge
        of the last item."""
        if not self.line_layouts:
            return 0
        line = self._clamp_line(cursor.line_index)
        if not line.items:
            return line.source_offset
        if cursor.glyph_index >= len(line.items):
            return _right_edge_source(line.items[-1])
        return _left_edge_source(line.items[max(0, cursor.glyph_index)])

    def source_to_glyph(self, pos: int) -> GlyphCursor:
        """Map a source position back to a glyph cursor. Two visual
        positions can map to the same source pos at a bidi boundary;
        we return the first match in visual order (the cursor whose
        item-to-the-right has the matching source edge)."""
        if not self.line_layouts:
            return GlyphCursor(0, 0)
        # Find the line containing pos, preferring "end of line N" over
        # "start of line N+1" for boundary positions (matches the
        # convention used by `pos_to_pixel`).
        line_idx = 0
        for li, ln in enumerate(self.line_layouts):
            if ln.source_offset <= pos <= ln.source_offset + ln.source_length:
                line_idx = li
                if pos < ln.source_offset + ln.source_length:
                    break
        line = self.line_layouts[line_idx]
        if not line.items:
            return GlyphCursor(line_idx, 0)
        # Look for an item whose left visual edge matches pos exactly.
        for gi, item in enumerate(line.items):
            if _left_edge_source(item) == pos:
                return GlyphCursor(line_idx, gi)
        # Otherwise, pos may be at the right visual edge of the last item.
        if _right_edge_source(line.items[-1]) == pos:
            return GlyphCursor(line_idx, len(line.items))
        # `pos` falls strictly inside a multi-codepoint cluster (e.g. a
        # ligature). Snap to the nearer source edge.
        for gi, item in enumerate(line.items):
            if item.source_start <= pos <= item.source_end:
                left_dist = pos - item.source_start
                right_dist = item.source_end - pos
                if item.right_to_left:
                    # RTL: left visual edge = source_end, right = source_start.
                    return GlyphCursor(
                        line_idx, gi if right_dist <= left_dist else gi + 1
                    )
                return GlyphCursor(line_idx, gi if left_dist <= right_dist else gi + 1)
        # Last-resort clamp.
        return GlyphCursor(
            line_idx, 0 if pos <= line.source_offset else len(line.items)
        )

    def next_glyph(self, cursor: GlyphCursor) -> GlyphCursor:
        """Move one glyph boundary to the right visually. Wraps to the
        start of the next line when at the end of the current line;
        clamps at the end of the document."""
        if not self.line_layouts:
            return cursor
        line = self._clamp_line(cursor.line_index)
        if cursor.glyph_index < len(line.items):
            return GlyphCursor(cursor.line_index, cursor.glyph_index + 1)
        if cursor.line_index + 1 < len(self.line_layouts):
            return GlyphCursor(cursor.line_index + 1, 0)
        return cursor

    def prev_glyph(self, cursor: GlyphCursor) -> GlyphCursor:
        """Move one glyph boundary to the left visually. Wraps to the
        end of the previous line when at the start of the current
        line; clamps at the start of the document."""
        if not self.line_layouts:
            return cursor
        if cursor.glyph_index > 0:
            return GlyphCursor(cursor.line_index, cursor.glyph_index - 1)
        if cursor.line_index > 0:
            prev_line = self.line_layouts[cursor.line_index - 1]
            return GlyphCursor(cursor.line_index - 1, len(prev_line.items))
        return cursor

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clamp_line(self, line_index: int) -> "_LineLayout":
        if line_index < 0:
            return self.line_layouts[0]
        if line_index >= len(self.line_layouts):
            return self.line_layouts[-1]
        return self.line_layouts[line_index]

    def _line_index_at_y(self, y: int) -> int:
        """Find the line index containing pixel y, clamping above /
        below to first / last line."""
        for li, ln in enumerate(self.line_layouts):
            if ln.y_top <= y < ln.y_bottom:
                return li
            if y < ln.y_top:
                # Above this line — if it's above the first too, clamp
                # to first; otherwise the previous iteration's `li` is
                # the last that satisfied y >= y_top.
                return max(0, li - 1) if li > 0 else 0
        # y is at or past the last line.
        return len(self.line_layouts) - 1


def _left_edge_source(item: _LineItem) -> int:
    """Source position at the visual left edge (`x_start`) of `item`."""
    return item.source_end if item.right_to_left else item.source_start


def _right_edge_source(item: _LineItem) -> int:
    """Source position at the visual right edge (`x_end`) of `item`."""
    return item.source_start if item.right_to_left else item.source_end


def _caret_x_in_line(line: _LineLayout, pos: int) -> int:
    """Compute the absolute pixel x for caret position `pos` known to
    fall inside `line`'s source range. Empty lines park the caret at
    the line's left edge.

    Items may be in any order (after UAX#9 L2 visual reorder, the
    sequence is in *visual* order, which doesn't match source order
    for mixed bidi). So the helpers don't rely on `items[0]` being
    the source-minimum item: they look up the item whose
    `source_start` matches the line's `source_offset` (the visual
    edge of the logical-first cluster), and symmetrically for the
    source-maximum end.
    """
    if not line.items:
        return line.x_offset
    line_src_start = line.source_offset
    line_src_end = line.source_offset + line.source_length
    if pos <= line_src_start:
        first = min(line.items, key=lambda it: it.source_start)
        edge = first.x_end if first.right_to_left else first.x_start
        return line.x_offset + edge
    if pos >= line_src_end:
        last = max(line.items, key=lambda it: it.source_end)
        edge = last.x_start if last.right_to_left else last.x_end
        return line.x_offset + edge
    for item in line.items:
        if item.source_start <= pos <= item.source_end:
            if pos == item.source_start:
                edge = item.x_end if item.right_to_left else item.x_start
                return line.x_offset + edge
            if pos == item.source_end:
                edge = item.x_start if item.right_to_left else item.x_end
                return line.x_offset + edge
            # Strictly inside a multi-codepoint cluster: linear
            # interpolation between the cluster's pixel ends. For a
            # RTL cluster the interpolation runs from x_end (source
            # start) down to x_start (source end).
            span = item.source_end - item.source_start
            frac = (pos - item.source_start) / span
            if item.right_to_left:
                interp = item.x_end - frac * (item.x_end - item.x_start)
            else:
                interp = item.x_start + frac * (item.x_end - item.x_start)
            return line.x_offset + int(round(interp))
    # `pos` sits in a gap between items in source order (defensive —
    # `_build_line_layout` emits contiguous items, but a hand-built
    # layout might not). Snap to the next item after `pos` in source
    # order, using its visual leading edge.
    after = [it for it in line.items if it.source_start > pos]
    if after:
        next_item = min(after, key=lambda it: it.source_start)
        edge = next_item.x_end if next_item.right_to_left else next_item.x_start
        return line.x_offset + edge
    # Past every item in source order: clamp to the source-max edge.
    last = max(line.items, key=lambda it: it.source_end)
    edge = last.x_start if last.right_to_left else last.x_end
    return line.x_offset + edge
