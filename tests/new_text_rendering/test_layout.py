"""Tests for the layout-info return of `ShapedTextRendering.render_text`.

Pins the public contract of `ShapedRenderedText`:

- `font_metrics` exposes ascender / descender / height_delta /
  line_spacing.
- `pos_to_pixel(pos)` and `pixel_to_pos(x, y)` round-trip on cluster
  boundaries; cursor position falls inside the right line and the
  right horizontal slot.
`ShapedTextRendering.render_text` returns that layout result alongside
the bitmap rendering result.
"""

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.constants import TextAlign
from videre.core.shaping import ShapedRenderedText, ShapedTextRendering


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


# -- Type / public surface --------------------------------------------------


def test_render_text_returns_shaped_rendered_text(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, rendered = r.render_text("Hello", color=Color(0, 0, 0))
    assert isinstance(out, ShapedRenderedText)
    assert rendered.get_width() > 0


def test_font_metrics_match_constructor(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16, height_delta=4)
    out, _ = r.render_text("Hello", color=Color(0, 0, 0))
    fm = out.font_metrics
    assert fm.ascender > 0
    assert fm.descender > 0
    assert fm.height_delta == 4
    assert fm.line_spacing > 0


def test_empty_text_reserves_one_empty_line_layout(fake_win) -> None:
    """Empty input still produces one line layout so consumers can
    place a caret at position 0 (`pos_to_pixel(0)` would otherwise
    have nothing to anchor on)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, rendered = r.render_text("", color=Color(0, 0, 0))
    assert len(out.line_layouts) == 1
    assert out.line_layouts[0].source_length == 0
    assert out.line_layouts[0].items == ()
    assert rendered.get_height() > 0
    # Caret at position 0 sits at the line's left edge.
    caret = out.pos_to_pixel(0)
    assert caret.x == 0
    # Inverse mapping on a line with no items returns the line's
    # source offset (defensive branch in `pixel_to_pos`).
    assert out.pixel_to_pos(50, 5) == 0


# -- pos_to_pixel ------------------------------------------------------------


def test_pos_to_pixel_first_position_is_left_edge(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text("Hello", color=Color(0, 0, 0))
    caret = out.pos_to_pixel(0)
    assert caret.x == 0
    assert caret.y_top < caret.y_bottom


def test_pos_to_pixel_last_position_is_right_edge(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    out, rendered = r.render_text(text, color=Color(0, 0, 0))
    caret = out.pos_to_pixel(len(text))
    # Caret at end is at or near the surface's right edge.
    assert caret.x >= rendered.get_width() - 4


def test_pos_to_pixel_middle_position_advances_monotonically(fake_win) -> None:
    """Caret x must increase as pos goes from 0 to len(text)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    out, _ = r.render_text(text, color=Color(0, 0, 0))
    xs = [out.pos_to_pixel(i).x for i in range(len(text) + 1)]
    for a, b in zip(xs, xs[1:]):
        assert a <= b


def test_pos_to_pixel_clamps_out_of_range(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    out, _ = r.render_text(text, color=Color(0, 0, 0))
    end_caret = out.pos_to_pixel(len(text))
    too_far = out.pos_to_pixel(len(text) + 100)
    too_negative = out.pos_to_pixel(-50)
    assert too_far.x == end_caret.x
    assert too_negative.x == out.pos_to_pixel(0).x


def test_pos_to_pixel_aligned_center_shifts_caret(fake_win) -> None:
    """CENTER alignment moves the line's left edge to the right;
    pos_to_pixel(0) must reflect that x_offset, not be 0."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text(
        "Hello",
        color=Color(0, 0, 0),
        width=200,
        wrap_words=True,
        align=TextAlign.CENTER,
    )
    caret = out.pos_to_pixel(0)
    assert caret.x > 0


# -- pixel_to_pos ------------------------------------------------------------


def test_pixel_to_pos_at_origin_yields_first_position(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text("Hello", color=Color(0, 0, 0))
    assert out.pixel_to_pos(0, 0) == 0


def test_pixel_to_pos_far_right_yields_last_position(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    out, rendered = r.render_text(text, color=Color(0, 0, 0))
    pos = out.pixel_to_pos(rendered.get_width() + 100, 0)
    assert pos == len(text)


def test_pixel_to_pos_below_clamps_to_last_line(fake_win) -> None:
    """A click below the surface picks the last line, not nothing."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "alpha\nbeta"
    out, _ = r.render_text(text, color=Color(0, 0, 0))
    pos = out.pixel_to_pos(0, 1000)
    # First position of line 2 is the offset of "beta", here right
    # after "alpha\n" — i.e. position 6 in source.
    assert pos == 6


def test_pixel_to_pos_above_clamps_to_first_line(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text("alpha\nbeta", color=Color(0, 0, 0))
    pos = out.pixel_to_pos(0, -50)
    assert pos == 0


# -- Round-trip --------------------------------------------------------------


def test_round_trip_at_cluster_boundaries(fake_win) -> None:
    """`pos_to_pixel` then `pixel_to_pos` returns the same source pos
    for every cluster boundary in a Latin text (each char is its own
    cluster, so every source pos is a boundary)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    out, _ = r.render_text(text, color=Color(0, 0, 0))
    for pos in range(len(text) + 1):
        caret = out.pos_to_pixel(pos)
        recovered = out.pixel_to_pos(caret.x, caret.y_top + 1)
        assert recovered == pos, f"round-trip failed for pos {pos}: got {recovered}"


# -- Multi-line / wrap -------------------------------------------------------


def test_pos_to_pixel_wrapped_lines_stack_vertically(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "alpha beta gamma delta"
    out, _ = r.render_text(text, color=Color(0, 0, 0), width=80, wrap_words=True)
    line0_caret = out.pos_to_pixel(0)
    last_caret = out.pos_to_pixel(len(text))
    assert last_caret.y_top > line0_caret.y_top


def test_pos_to_pixel_paragraph_break_position(fake_win) -> None:
    """The position of the explicit `\\n` (between paragraphs) sits at
    the end of the previous line, not at the start of the next one."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text("alpha\nbeta", color=Color(0, 0, 0))
    # Position 5 is the \n itself (after "alpha"); we want the caret
    # at end-of-line-0, not at start-of-line-1.
    caret_at_5 = out.pos_to_pixel(5)
    caret_at_0 = out.pos_to_pixel(0)
    assert caret_at_5.y_top == caret_at_0.y_top  # same line as "alpha"
    caret_at_6 = out.pos_to_pixel(6)
    assert caret_at_6.y_top > caret_at_0.y_top  # new line for "beta"


# -- Inter-word gaps ---------------------------------------------------------


def test_pos_to_pixel_in_inter_word_gap(fake_win) -> None:
    """A position pointing AT the source whitespace between two words
    sits in the inter-word pixel gap, between the previous word's end
    and the next word's start."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "a b"
    out, _ = r.render_text(text, color=Color(0, 0, 0))
    caret_a_end = out.pos_to_pixel(1)  # after 'a', before space
    caret_space = out.pos_to_pixel(2)  # after space, before 'b'
    # The caret should advance across the gap.
    assert caret_space.x > caret_a_end.x


# -- Defensive paths: empty layouts, multi-codepoint clusters ---------------
#
# These tests reach for the helpers' edge-case branches by building the
# layout structures by hand. Empty `line_layouts` is unreachable through
# `render_text` (which always emits at least one layout, possibly empty
# at the item level), but the helpers handle it defensively so a
# consumer can pass a degenerate result. Multi-codepoint clusters
# (ligatures, Indic conjuncts) are font-dependent and hard to provoke
# reliably from a real string; constructing the layout directly is the
# most determinist way to pin the linear-interpolation behavior.


def _make_empty_rendered() -> ShapedRenderedText:
    from videre.core.shaping.layout import FontMetrics

    return ShapedRenderedText(
        font_metrics=FontMetrics(
            ascender=10, descender=3, height_delta=2, line_spacing=15
        ),
        line_layouts=(),
    )


def _make_layout_with_one_ligature() -> ShapedRenderedText:
    """Build a layout where one cluster covers two source positions
    (the canonical ligature case): source [3, 5) maps to pixels
    [12, 24) — a 12-px-wide single glyph standing for two chars."""
    from videre.core.shaping.layout import FontMetrics, _LineItem, _LineLayout

    line = _LineLayout(
        y_top=0,
        y_bottom=15,
        x_offset=0,
        source_offset=0,
        source_length=5,
        items=(
            _LineItem(source_start=0, source_end=1, x_start=0, x_end=4),
            _LineItem(source_start=1, source_end=2, x_start=4, x_end=8),
            _LineItem(source_start=2, source_end=3, x_start=8, x_end=12),
            _LineItem(source_start=3, source_end=5, x_start=12, x_end=24),  # liga
        ),
    )
    return ShapedRenderedText(
        font_metrics=FontMetrics(
            ascender=10, descender=3, height_delta=2, line_spacing=15
        ),
        line_layouts=(line,),
    )


def test_pos_to_pixel_empty_layouts_returns_origin_caret() -> None:
    """Empty `line_layouts` is a defensive path: `pos_to_pixel`
    returns `(0, 0, line_spacing)` so consumers don't need to special-
    case the no-layout case."""
    out = _make_empty_rendered()
    caret = out.pos_to_pixel(0)
    assert caret.x == 0
    assert caret.y_top == 0
    assert caret.y_bottom == out.font_metrics.line_spacing


def test_pos_to_pixel_empty_layouts_with_arbitrary_pos() -> None:
    """`pos_to_pixel` on empty layouts ignores `pos` (no anchor to
    snap to)."""
    out = _make_empty_rendered()
    caret_42 = out.pos_to_pixel(42)
    caret_neg = out.pos_to_pixel(-7)
    assert caret_42.x == 0 == caret_neg.x


def test_pixel_to_pos_empty_layouts_returns_zero() -> None:
    out = _make_empty_rendered()
    assert out.pixel_to_pos(50, 50) == 0


def test_pos_to_pixel_inside_ligature_interpolates_linearly() -> None:
    """Caret strictly inside a 2-codepoint cluster sits at the
    fractional pixel position. For source [3, 5) → pixels [12, 24),
    `pos=4` (the midpoint) lands at x=18."""
    out = _make_layout_with_one_ligature()
    caret_left = out.pos_to_pixel(3)  # cluster start
    caret_mid = out.pos_to_pixel(4)  # inside cluster
    caret_right = out.pos_to_pixel(5)  # cluster end
    assert caret_left.x == 12
    assert caret_mid.x == 18
    assert caret_right.x == 24


def test_pixel_to_pos_in_ligature_snaps_to_nearer_boundary() -> None:
    """`pixel_to_pos` doesn't interpolate on the way back: a click
    inside the cluster snaps to whichever boundary is closer."""
    out = _make_layout_with_one_ligature()
    # cluster covers x=12..24 (mid=18), source 3..5
    assert out.pixel_to_pos(13, 0) == 3  # left half -> start
    assert out.pixel_to_pos(23, 0) == 5  # right half -> end
    assert out.pixel_to_pos(18, 0) == 3  # exact midpoint -> start (tie -> start)


def test_pixel_to_pos_past_last_item_returns_line_end() -> None:
    """When items don't cover the whole `source_length` (defensive
    branch in `_caret_x_in_line`) and pos is past the last item,
    `pos_to_pixel` clamps to the last item's right edge."""
    from videre.core.shaping.layout import FontMetrics, _LineItem, _LineLayout

    line = _LineLayout(
        y_top=0,
        y_bottom=15,
        x_offset=0,
        source_offset=0,
        source_length=10,  # claim 10 source positions
        items=(_LineItem(source_start=0, source_end=3, x_start=0, x_end=12),),
    )
    out = ShapedRenderedText(
        font_metrics=FontMetrics(
            ascender=10, descender=3, height_delta=2, line_spacing=15
        ),
        line_layouts=(line,),
    )
    # Pos 5 is in the [item.source_end, line.source_length] uncovered
    # tail; helpers must return the rightmost reachable x without
    # crashing.
    caret = out.pos_to_pixel(5)
    assert caret.x == 12


def _make_layout_with_gap_between_items() -> ShapedRenderedText:
    """Layout where two items leave a source-position gap between
    them — the kind of structure `_build_line_layout` never produces
    (it emits contiguous items), but the helpers handle defensively.
    Items: [0, 2) at pixels [0, 8); [4, 6) at pixels [16, 24); the
    source range [2, 4) and pixel range [8, 16) sit in the gap."""
    from videre.core.shaping.layout import FontMetrics, _LineItem, _LineLayout

    line = _LineLayout(
        y_top=0,
        y_bottom=15,
        x_offset=0,
        source_offset=0,
        source_length=6,
        items=(
            _LineItem(source_start=0, source_end=2, x_start=0, x_end=8),
            _LineItem(source_start=4, source_end=6, x_start=16, x_end=24),
        ),
    )
    return ShapedRenderedText(
        font_metrics=FontMetrics(
            ascender=10, descender=3, height_delta=2, line_spacing=15
        ),
        line_layouts=(line,),
    )


def test_pos_to_pixel_pos_at_gap_start_after_gap_resolves() -> None:
    """`pos_to_pixel(4)` lands exactly on the second item's
    `source_start`. Because the previous item's `source_end` (2) is
    strictly less than `pos`, the loop exits the first item without
    matching and reaches the second item, taking the
    `pos == item.source_start` branch (line 203 in `_caret_x_in_line`)."""
    out = _make_layout_with_gap_between_items()
    caret = out.pos_to_pixel(4)
    assert caret.x == 16  # second item's x_start


def test_pos_to_pixel_pos_inside_gap_clamps_to_next_item_start() -> None:
    """`pos_to_pixel(3)` falls strictly inside the source gap
    [2, 4); the `pos < item.source_start` branch in `_caret_x_in_line`
    sends the caret to the next item's left edge."""
    out = _make_layout_with_gap_between_items()
    caret = out.pos_to_pixel(3)
    assert caret.x == 16  # second item's x_start (gap snaps forward)


def test_pixel_to_pos_in_pixel_gap_falls_through_to_line_end() -> None:
    """`pixel_to_pos(12, 5)` hits the pixel gap [8, 16) — between the
    two items. The first guard (`<= items[0].x_start`) doesn't
    match (12 > 0), the last (`>= items[-1].x_end`) doesn't either
    (12 < 24), and the per-item loop never enters its body
    (12 sits outside both items' pixel ranges). The fallback returns
    `line.source_offset + line.source_length`."""
    out = _make_layout_with_gap_between_items()
    pos = out.pixel_to_pos(12, 5)
    assert pos == 6  # source_offset(0) + source_length(6)


# -- RTL (pure right-to-left) -----------------------------------------------
#
# Pure-RTL layouts have items sorted by source_start (logical order),
# but their pixel ranges run from right to left: the first source
# position sits at the largest x, and the last source position at x=0.
# The helpers must flip the LTR "source_start at x_start" assumption.


def _make_pure_rtl_layout() -> ShapedRenderedText:
    """3-codepoint pure-RTL run "ABC" (source order 0, 1, 2) laid out
    visually as "CBA" left-to-right:

      visual:   C  B  A
      pixel:   0..10..20..30
      source:  2..1..0..(end=3)

    Items sorted by source_start: A first (source 0..1, pixels
    20..30), then B (1..2, 10..20), then C (2..3, 0..10). All tagged
    `bidi_level=1`."""
    from videre.core.shaping.layout import FontMetrics, _LineItem, _LineLayout

    line = _LineLayout(
        y_top=0,
        y_bottom=15,
        x_offset=0,
        source_offset=0,
        source_length=3,
        items=(
            _LineItem(source_start=0, source_end=1, x_start=20, x_end=30, bidi_level=1),
            _LineItem(source_start=1, source_end=2, x_start=10, x_end=20, bidi_level=1),
            _LineItem(source_start=2, source_end=3, x_start=0, x_end=10, bidi_level=1),
        ),
    )
    return ShapedRenderedText(
        font_metrics=FontMetrics(
            ascender=10, descender=3, height_delta=2, line_spacing=15
        ),
        line_layouts=(line,),
    )


def test_rtl_pos_to_pixel_first_source_position_is_visual_right_edge() -> None:
    """Source pos 0 (logically first) sits at the visual right edge
    of the run — x=30 for the layout above."""
    out = _make_pure_rtl_layout()
    assert out.pos_to_pixel(0).x == 30


def test_rtl_pos_to_pixel_last_source_position_is_visual_left_edge() -> None:
    """Source pos 3 (logically past end) sits at the visual left edge
    of the run — x=0 for the layout above."""
    out = _make_pure_rtl_layout()
    assert out.pos_to_pixel(3).x == 0


def test_rtl_pos_to_pixel_advances_right_to_left() -> None:
    """In a pure-RTL layout, caret x must **decrease** as logical
    pos increases."""
    out = _make_pure_rtl_layout()
    xs = [out.pos_to_pixel(p).x for p in range(4)]
    for a, b in zip(xs, xs[1:]):
        assert a > b, f"caret x should decrease left-to-right in RTL: {xs}"


def test_rtl_pos_to_pixel_at_cluster_boundaries() -> None:
    """Each inter-cluster source boundary lands at the boundary's
    visual position. Between A (source 0..1) and B (source 1..2),
    pos 1 sits at A's visual left edge = B's visual right edge = x=20."""
    out = _make_pure_rtl_layout()
    assert out.pos_to_pixel(1).x == 20
    assert out.pos_to_pixel(2).x == 10


def test_rtl_pixel_to_pos_left_half_returns_source_end() -> None:
    """A click on the visual-left half of a RTL glyph means the
    caret should land at the glyph's source END (logically: after
    the glyph). On glyph C (pixels 0..10, source 2..3), a click at
    x=2 yields pos 3."""
    out = _make_pure_rtl_layout()
    assert out.pixel_to_pos(2, 0) == 3


def test_rtl_pixel_to_pos_right_half_returns_source_start() -> None:
    """Symmetric: visual-right half of a RTL glyph yields source
    START. On glyph C (pixels 0..10, source 2..3), a click at x=8
    yields pos 2."""
    out = _make_pure_rtl_layout()
    assert out.pixel_to_pos(8, 0) == 2


def test_rtl_pixel_to_pos_far_left_returns_run_end() -> None:
    """A click to the visual left of all items is past the run's end
    logically (the last cluster in source order is the visually
    leftmost), so it should return the run's source end (3)."""
    out = _make_pure_rtl_layout()
    assert out.pixel_to_pos(-50, 0) == 3


def test_rtl_pixel_to_pos_far_right_returns_run_start() -> None:
    """A click to the visual right of all items is before the run's
    start logically, so it should return the run's source start (0)."""
    out = _make_pure_rtl_layout()
    assert out.pixel_to_pos(1000, 0) == 0


def test_rtl_round_trip_at_cluster_boundaries() -> None:
    """`pos_to_pixel` then `pixel_to_pos` round-trips on every source
    boundary of a pure-RTL layout."""
    out = _make_pure_rtl_layout()
    for pos in range(4):
        caret = out.pos_to_pixel(pos)
        recovered = out.pixel_to_pos(caret.x, caret.y_top + 1)
        assert recovered == pos, f"round-trip failed for pos {pos}: got {recovered}"


# -- RTL integration via render_text ----------------------------------------
#
# These tests exercise `_build_line_layout` end-to-end with a real
# Arabic string. They check shape-invariant properties only (HarfBuzz's
# exact glyph count for a given font is not pinned).


_ARABIC_WORD = "سلام"  # "peace", 4 codepoints


def test_rtl_render_text_arabic_pos_to_pixel_advances_right_to_left(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text(_ARABIC_WORD, color=Color(0, 0, 0))
    xs = [out.pos_to_pixel(p).x for p in range(len(_ARABIC_WORD) + 1)]
    # First logical position should be visually rightmost; last should
    # be visually leftmost.
    assert xs[0] > xs[-1], f"expected RTL caret advance (decreasing x), got {xs}"


def test_rtl_render_text_arabic_round_trip_at_every_source_position(fake_win) -> None:
    """For each source position p in the Arabic word, the caret pixel
    returned by `pos_to_pixel(p)` round-trips back to p via
    `pixel_to_pos`. Validates the bidi-aware mapping end-to-end."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    out, _ = r.render_text(_ARABIC_WORD, color=Color(0, 0, 0))
    for p in range(len(_ARABIC_WORD) + 1):
        caret = out.pos_to_pixel(p)
        recovered = out.pixel_to_pos(caret.x, caret.y_top + 1)
        assert recovered == p, f"round-trip failed for Arabic pos {p}: got {recovered}"
