"""Tests for the glyph-based caret navigation helpers on
`ShapedRenderedText`.

The glyph cursor exposes a strictly visual view of the line: arrow
keys advance ``glyph_index`` by ±1 regardless of script direction, so
a right arrow in the middle of an Arabic run does NOT jump back in
source order — it moves the caret one glyph to the right visually.

Tests cover:
- `glyph_caret_pixel` / `pixel_to_glyph` round-trip on every boundary.
- `glyph_to_source` / `source_to_glyph` mapping for LTR, RTL, and the
  bidi-boundary case.
- `next_glyph` / `prev_glyph` traversal across the document, including
  wrap-around at line boundaries.
"""

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.shaping import GlyphCursor, ShapedTextRendering


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


ARAB = chr(0x0623) + chr(0x0628) + chr(0x062C)


def _render(fake_win, text: str, **kw) -> "tuple":
    return ShapedTextRendering(fake_win.backend, size=16).render_text(
        text, color=Color(0, 0, 0), **kw
    )


# -- glyph_caret_pixel ------------------------------------------------------


def test_glyph_caret_pixel_empty_layout_returns_origin(fake_win) -> None:
    out, _ = _render(fake_win, "")
    caret = out.glyph_caret_pixel(GlyphCursor(0, 0))
    assert caret.x == 0


def test_glyph_caret_pixel_ltr_first_is_left_edge(fake_win) -> None:
    """First glyph cursor sits at the visual left edge of items[0]."""
    out, _ = _render(fake_win, "hello")
    assert out.glyph_caret_pixel(GlyphCursor(0, 0)).x == 0


def test_glyph_caret_pixel_ltr_last_is_right_edge_of_last_item(fake_win) -> None:
    out, _ = _render(fake_win, "hello")
    n_items = len(out.line_layouts[0].items)
    caret = out.glyph_caret_pixel(GlyphCursor(0, n_items))
    last = out.line_layouts[0].items[-1]
    assert caret.x == out.line_layouts[0].x_offset + last.x_end


def test_glyph_caret_pixel_advances_left_to_right_along_glyph_index(fake_win) -> None:
    """`glyph_index` advances monotonically left-to-right in pixels,
    regardless of the underlying script directions on the line."""
    out, _ = _render(fake_win, "ab" + ARAB + "cd")
    n_items = len(out.line_layouts[0].items)
    xs = [out.glyph_caret_pixel(GlyphCursor(0, i)).x for i in range(n_items + 1)]
    for a, b in zip(xs, xs[1:]):
        assert a <= b, f"glyph_index pixels not monotone l-to-r: {xs}"


# -- pixel_to_glyph ---------------------------------------------------------


def test_pixel_to_glyph_at_origin_yields_first_position(fake_win) -> None:
    out, _ = _render(fake_win, "hello")
    assert out.pixel_to_glyph(0, 0) == GlyphCursor(0, 0)


def test_pixel_to_glyph_far_right_yields_last_position(fake_win) -> None:
    out, rendered = _render(fake_win, "hello")
    n_items = len(out.line_layouts[0].items)
    cursor = out.pixel_to_glyph(rendered.get_width() + 100, 0)
    assert cursor == GlyphCursor(0, n_items)


def test_pixel_to_glyph_round_trip_ltr(fake_win) -> None:
    """For every valid glyph_index, pixel_to_glyph ∘ glyph_caret_pixel
    is the identity in a pure-LTR text (no caret ambiguity)."""
    out, _ = _render(fake_win, "hello world")
    n_items = len(out.line_layouts[0].items)
    line = out.line_layouts[0]
    for gi in range(n_items + 1):
        caret = out.glyph_caret_pixel(GlyphCursor(0, gi))
        recovered = out.pixel_to_glyph(caret.x, line.y_top + 1)
        assert recovered == GlyphCursor(0, gi)


def test_pixel_to_glyph_round_trip_rtl(fake_win) -> None:
    """Same round-trip on a pure-RTL Arabic word."""
    out, _ = _render(fake_win, ARAB)
    n_items = len(out.line_layouts[0].items)
    line = out.line_layouts[0]
    for gi in range(n_items + 1):
        caret = out.glyph_caret_pixel(GlyphCursor(0, gi))
        recovered = out.pixel_to_glyph(caret.x, line.y_top + 1)
        assert recovered == GlyphCursor(0, gi)


def test_pixel_to_glyph_round_trip_mixed_ltr_rtl_ltr(fake_win) -> None:
    """And on a mixed line. The round-trip holds because the glyph
    cursor is purely visual: no source-ambiguity to resolve."""
    out, _ = _render(fake_win, "ab" + ARAB + "cd")
    n_items = len(out.line_layouts[0].items)
    line = out.line_layouts[0]
    for gi in range(n_items + 1):
        caret = out.glyph_caret_pixel(GlyphCursor(0, gi))
        recovered = out.pixel_to_glyph(caret.x, line.y_top + 1)
        assert recovered == GlyphCursor(0, gi)


# -- glyph_to_source / source_to_glyph --------------------------------------


def test_glyph_to_source_ltr(fake_win) -> None:
    """In LTR text, glyph_index i maps to source position i (each
    Latin codepoint is its own cluster)."""
    text = "hello"
    out, _ = _render(fake_win, text)
    for gi in range(len(text) + 1):
        assert out.glyph_to_source(GlyphCursor(0, gi)) == gi


def test_glyph_to_source_rtl_pure(fake_win) -> None:
    """In pure RTL, glyph_index 0 (visual leftmost) corresponds to the
    source END of the run (source position 3 for a 3-char Arabic
    word), and glyph_index 3 (visual rightmost) to source position 0.
    """
    out, _ = _render(fake_win, ARAB)
    assert out.glyph_to_source(GlyphCursor(0, 0)) == 3
    assert out.glyph_to_source(GlyphCursor(0, 1)) == 2
    assert out.glyph_to_source(GlyphCursor(0, 2)) == 1
    assert out.glyph_to_source(GlyphCursor(0, 3)) == 0


def test_source_to_glyph_ltr_round_trip(fake_win) -> None:
    text = "hello"
    out, _ = _render(fake_win, text)
    for pos in range(len(text) + 1):
        cursor = out.source_to_glyph(pos)
        assert out.glyph_to_source(cursor) == pos


def test_source_to_glyph_rtl_round_trip(fake_win) -> None:
    """Every source position of an Arabic word round-trips through
    source -> glyph -> source."""
    text = ARAB
    out, _ = _render(fake_win, text)
    for pos in range(len(text) + 1):
        cursor = out.source_to_glyph(pos)
        assert out.glyph_to_source(cursor) == pos


# -- next_glyph / prev_glyph -------------------------------------------------


def test_next_glyph_advances_within_line(fake_win) -> None:
    out, _ = _render(fake_win, "hello")
    cur = GlyphCursor(0, 0)
    cur = out.next_glyph(cur)
    assert cur == GlyphCursor(0, 1)


def test_next_glyph_clamps_at_end_of_document(fake_win) -> None:
    out, _ = _render(fake_win, "hi")
    n = len(out.line_layouts[0].items)
    end = GlyphCursor(0, n)
    assert out.next_glyph(end) == end


def test_prev_glyph_recedes_within_line(fake_win) -> None:
    out, _ = _render(fake_win, "hello")
    n = len(out.line_layouts[0].items)
    cur = GlyphCursor(0, n)
    cur = out.prev_glyph(cur)
    assert cur == GlyphCursor(0, n - 1)


def test_prev_glyph_clamps_at_start_of_document(fake_win) -> None:
    out, _ = _render(fake_win, "hi")
    assert out.prev_glyph(GlyphCursor(0, 0)) == GlyphCursor(0, 0)


def test_next_glyph_wraps_to_next_line(fake_win) -> None:
    """At the end of line N (glyph_index == len(items)), next_glyph
    moves to glyph 0 of line N+1."""
    out, _ = _render(fake_win, "alpha\nbeta")
    assert len(out.line_layouts) == 2
    n_items_line0 = len(out.line_layouts[0].items)
    end_of_line0 = GlyphCursor(0, n_items_line0)
    assert out.next_glyph(end_of_line0) == GlyphCursor(1, 0)


def test_prev_glyph_wraps_to_previous_line(fake_win) -> None:
    out, _ = _render(fake_win, "alpha\nbeta")
    n_items_line0 = len(out.line_layouts[0].items)
    start_of_line1 = GlyphCursor(1, 0)
    assert out.prev_glyph(start_of_line1) == GlyphCursor(0, n_items_line0)


def test_next_glyph_in_rtl_run_decreases_source_position(fake_win) -> None:
    """Visually advancing the cursor inside an Arabic word makes the
    *source* position go DOWN (the visual leftmost glyph is the
    source-rightmost). This is the whole point of glyph-based
    navigation: arrow keys behave intuitively in RTL too."""
    out, _ = _render(fake_win, ARAB)
    # glyph 0 -> source 3 (rightmost source = leftmost visual).
    # next_glyph -> glyph 1 -> source 2.
    cur = GlyphCursor(0, 0)
    src0 = out.glyph_to_source(cur)
    cur = out.next_glyph(cur)
    src1 = out.glyph_to_source(cur)
    assert src1 < src0  # source pos decreased while caret moved right


# -- Mixed bidi end-to-end --------------------------------------------------


def test_glyph_navigation_traverses_mixed_line_left_to_right(fake_win) -> None:
    """On an LTR-RTL-LTR line, next_glyph from start to end visits
    every visual position with monotonically non-decreasing pixel x."""
    text = "ab" + ARAB + "cd"
    out, _ = _render(fake_win, text)
    n_items = len(out.line_layouts[0].items)
    cursor = GlyphCursor(0, 0)
    xs = [out.glyph_caret_pixel(cursor).x]
    for _ in range(n_items):
        cursor = out.next_glyph(cursor)
        xs.append(out.glyph_caret_pixel(cursor).x)
    assert cursor == GlyphCursor(0, n_items)
    for a, b in zip(xs, xs[1:]):
        assert a <= b, f"caret should march left-to-right: {xs}"
