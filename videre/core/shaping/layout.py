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
    document (the same convention `TextSequence` indexes into).
    `x_start` / `x_end` are pixel positions within the line, relative
    to the line's `x_offset`. For an inter-word gap, the source range
    has length 1 (the whitespace position) and the pixel range has
    width `space_advance` (plus any JUSTIFY extra)."""

    source_start: int
    source_end: int
    x_start: int
    x_end: int


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
        nearest item boundary: a click on the left half of a cluster
        yields the cluster's start position, on the right half its
        end position. Empty layouts always return 0.
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
        if rel_x <= line.items[0].x_start:
            return line.items[0].source_start
        if rel_x >= line.items[-1].x_end:
            return line.items[-1].source_end
        for item in line.items:
            if item.x_start <= rel_x <= item.x_end:
                if rel_x - item.x_start <= item.x_end - rel_x:
                    return item.source_start
                return item.source_end
        return line.source_offset + line.source_length


def _caret_x_in_line(line: _LineLayout, pos: int) -> int:
    """Compute the absolute pixel x for caret position `pos` known to
    fall inside `line`'s source range. Empty lines park the caret at
    the line's left edge; positions before the first item or after the
    last clamp to the corresponding edge."""
    if not line.items:
        return line.x_offset
    if pos <= line.items[0].source_start:
        return line.x_offset + line.items[0].x_start
    if pos >= line.items[-1].source_end:
        return line.x_offset + line.items[-1].x_end
    for item in line.items:
        if item.source_start <= pos <= item.source_end:
            if pos == item.source_start:
                return line.x_offset + item.x_start
            if pos == item.source_end:
                return line.x_offset + item.x_end
            # Strictly inside a multi-codepoint cluster: linear
            # interpolation between the cluster's pixel ends.
            span = item.source_end - item.source_start
            frac = (pos - item.source_start) / span
            interp = item.x_start + frac * (item.x_end - item.x_start)
            return line.x_offset + int(round(interp))
        if pos < item.source_start:
            # Hit a gap between items (shouldn't happen if items cover
            # the line contiguously, but stay safe).
            return line.x_offset + item.x_start
    # Past the last item.
    return line.x_offset + line.items[-1].x_end
