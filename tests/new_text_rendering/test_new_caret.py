"""Tests for the flat-model caret (`text_partition.layout.RenderedText`),
obtained from `render_text`. Covers size, LTR states/navigation/hit-test/range,
RTL visual navigation, and the painted selection highlight.
"""

import pygame
import pygame.freetype
import pytest

from tests.common import pixels_blue, pixels_red
from videre.colors import Color
from videre.core.shaping.rasterizer import GlyphRasterizer
from videre.core.shaping.render import render_text
from videre.core.shaping.shaper import Shaper, shape_line
from videre.core.shaping.text_partition.partitioner import partition_text

BLACK = Color(0, 0, 0)
ARAB = "أبج"  # 3-codepoint Arabic chunk


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


@pytest.fixture
def rasterizer() -> GlyphRasterizer:
    return GlyphRasterizer()


def _render(text, fake_win, shaper, rasterizer, **kw):
    return render_text(
        text,
        backend=fake_win.backend,
        rasterizer=rasterizer,
        shaper=shaper,
        size=16,
        color=BLACK,
        **kw,
    )


# -- size --------------------------------------------------------------------


def test_size_matches_surface(fake_win, shaper, rasterizer) -> None:
    rendered, surf = _render("hello", fake_win, shaper, rasterizer)
    assert rendered.get_width() == surf.get_width()
    assert rendered.get_height() == surf.get_height()


# -- LTR ---------------------------------------------------------------------


def test_ltr_states_and_pixels_monotonic(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("hello", fake_win, shaper, rasterizer)
    assert rendered.total_visual_count() == 5
    xs = []
    for p in range(6):
        st = rendered.visual_state(p)
        assert st.pos == p  # no bidi -> source == visual
        assert st.visual_pos == p
        xs.append(st.pixel.x)
    assert xs == sorted(xs)  # caret moves right as pos grows
    assert xs[0] == 0


def test_ltr_hit_test_edges(fake_win, shaper, rasterizer) -> None:
    rendered, surf = _render("hello", fake_win, shaper, rasterizer)
    y = rendered.line_layouts[0].y_top + 1
    assert rendered.visual_state_at_pixel(0, y).pos == 0
    assert rendered.visual_state_at_pixel(surf.get_width() + 50, y).pos == 5


def test_ltr_navigation_clamps(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("hello", fake_win, shaper, rasterizer)
    st = rendered.visual_state(0)
    for expected in range(1, 6):
        st = rendered.next_visual(st)
        assert st.pos == expected
    assert rendered.next_visual(st).pos == 5  # clamps at end
    for expected in range(4, -1, -1):
        st = rendered.prev_visual(st)
        assert st.pos == expected
    assert rendered.prev_visual(st).pos == 0  # clamps at start


def test_ltr_range_to_source(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("hello", fake_win, shaper, rasterizer)
    assert rendered.visual_range_to_source_set(0, 5) == frozenset(range(5))
    assert rendered.visual_range_to_source_set(1, 3) == frozenset({1, 2})
    assert rendered.visual_range_to_source_set(3, 3) == frozenset()


# -- RTL ---------------------------------------------------------------------


def test_rtl_navigation_covers_every_position(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render(ARAB, fake_win, shaper, rasterizer)
    total = rendered.total_visual_count()
    assert total >= 1
    st = rendered.visual_state_at(0)
    visited = {st.visual_pos}
    for _ in range(total):
        st = rendered.next_visual(st)
        visited.add(st.visual_pos)
    assert visited == set(range(total + 1))


def test_rtl_first_source_char_is_on_the_right(fake_win, shaper, rasterizer) -> None:
    """Pure Arabic (RTL): source position 0 sits at the visual right edge,
    the end position at the left."""
    rendered, _ = _render(ARAB, fake_win, shaper, rasterizer)
    x_first = rendered.visual_state(0).pixel.x
    x_last = rendered.visual_state(len(ARAB)).pixel.x
    assert x_first > x_last


# -- Selection highlight -----------------------------------------------------


def test_selection_paints_blue_highlight(fake_win, shaper, rasterizer) -> None:
    _, surf = _render("hello world", fake_win, shaper, rasterizer, selection=(0, 5))
    blue = pixels_blue(surf).astype(int)
    red = pixels_red(surf).astype(int)
    # The translucent blue ribbon makes a band of pixels bluer than they are red.
    assert int((blue > red).sum()) > 0


def test_no_selection_no_blue(fake_win, shaper, rasterizer) -> None:
    _, surf = _render("hello world", fake_win, shaper, rasterizer)
    blue = pixels_blue(surf).astype(int)
    red = pixels_red(surf).astype(int)
    assert int((blue > red).sum()) == 0


# -- Round-trips / clamps / multi-line (was test_layout / test_glyph_cursor) --


def test_ltr_pixel_round_trips_at_every_position(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("hello world", fake_win, shaper, rasterizer)
    y = rendered.line_layouts[0].y_top + 1
    for p in range(len("hello world") + 1):
        x = rendered.visual_state(p).pixel.x
        assert rendered.visual_state_at_pixel(x, y).pos == p


def test_visual_state_clamps_out_of_range(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("hello", fake_win, shaper, rasterizer)
    assert rendered.visual_state(1000).pos == 5
    assert rendered.visual_state(-50).pos == 0


def test_wrapped_lines_stack_vertically(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render(
        "alpha beta gamma delta",
        fake_win,
        shaper,
        rasterizer,
        width=80,
        wrap_words=True,
    )
    assert len(rendered.line_layouts) > 1
    first_y = rendered.visual_state(0).pixel.y_top
    last_y = rendered.visual_state(len("alpha beta gamma delta")).pixel.y_top
    assert last_y > first_y


def test_paragraph_break_caret_on_second_line(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("alpha\nbeta", fake_win, shaper, rasterizer)
    assert len(rendered.line_layouts) == 2
    y_alpha = rendered.visual_state(0).pixel.y_top
    y_beta = rendered.visual_state(8).pixel.y_top  # inside "beta" (positions 6..9)
    assert y_beta > y_alpha


def test_explicit_newline_has_distinct_caret_positions_on_both_sides(
    fake_win, shaper, rasterizer
) -> None:
    text = "a\nb"
    rendered, _ = _render(text, fake_win, shaper, rasterizer)

    states = [rendered.visual_state(pos) for pos in range(len(text) + 1)]
    assert [state.pos for state in states] == list(range(len(text) + 1))
    assert rendered.total_visual_count() == len(text)
    assert states[1].pixel.y_top < states[2].pixel.y_top


def test_rtl_line_terminator_does_not_skip_the_visual_right_edge(
    fake_win, shaper, rasterizer
) -> None:
    text = f"{ARAB}\nb"
    rendered, _ = _render(text, fake_win, shaper, rasterizer)

    state = rendered.visual_state(len(ARAB))
    visited = []
    for _ in range(len(ARAB)):
        state = rendered.next_visual(state)
        visited.append(state.pos)

    assert visited == [2, 1, 0]
    assert rendered.next_visual(state).pos == len(ARAB) + 1


def test_crlf_is_one_editable_visual_item(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("a\r\nb", fake_win, shaper, rasterizer)

    assert rendered.total_visual_count() == 3
    assert rendered.visual_range_to_source_set(1, 2) == frozenset({1, 2})
    assert rendered.visual_state(1).pixel.y_top < rendered.visual_state(3).pixel.y_top


def test_vertical_tab_is_a_line_break(fake_win, shaper, rasterizer) -> None:
    rendered, _ = _render("a\vb", fake_win, shaper, rasterizer)

    assert len(rendered.line_layouts) == 2
    assert rendered.visual_range_to_source_set(1, 2) == frozenset({1})
    assert rendered.visual_state(1).pixel.y_top < rendered.visual_state(2).pixel.y_top


def test_hidden_controls_keep_source_slots_without_width(
    fake_win, shaper, rasterizer
) -> None:
    rendered, _ = _render("a\x01\u200eb", fake_win, shaper, rasterizer)

    assert rendered.total_visual_count() == 4
    assert rendered.visual_range_to_source_set(1, 2) == frozenset({1})
    assert rendered.visual_range_to_source_set(2, 3) == frozenset({2})
    assert rendered.visual_state(1).pixel.x == rendered.visual_state(2).pixel.x
    assert rendered.visual_state(2).pixel.x == rendered.visual_state(3).pixel.x


def test_tab_keeps_one_source_slot_and_has_advance(
    fake_win, shaper, rasterizer
) -> None:
    rendered, _ = _render("a\tb", fake_win, shaper, rasterizer)

    assert rendered.total_visual_count() == 3
    assert rendered.visual_range_to_source_set(1, 2) == frozenset({1})
    assert rendered.visual_state(2).pixel.x > rendered.visual_state(1).pixel.x


def test_invalid_surrogate_renders_as_replacement_without_losing_source(
    fake_win, shaper, rasterizer
) -> None:
    rendered, _ = _render("a\ud800b", fake_win, shaper, rasterizer)

    assert rendered.total_visual_count() == 3
    assert rendered.visual_range_to_source_set(1, 2) == frozenset({1})
    assert rendered.visual_state(2).pixel.x > rendered.visual_state(1).pixel.x


def test_collapsed_whitespace_line_keeps_one_selectable_source_item(
    fake_win, shaper, rasterizer
) -> None:
    rendered, _ = _render(
        "   ", fake_win, shaper, rasterizer, width=100, wrap_words=True
    )

    assert len(rendered.line_layouts) == 1
    assert rendered.total_visual_count() == 1
    assert rendered.visual_range_to_source_set(0, 1) == frozenset({0, 1, 2})
    assert rendered.visual_state(0).pos == 0
    assert rendered.visual_state(3).pos == 3
    assert rendered.visual_state(0).pixel.x == rendered.visual_state(3).pixel.x


def test_italic_overhang_padding_does_not_change_caret_advance(
    fake_win, shaper, rasterizer
) -> None:
    rendered, _ = _render("ff", fake_win, shaper, rasterizer, italic=True)
    (line,) = partition_text("ff").lines
    shaped = shape_line(line, shaper, 16, italic=True)
    advance = sum(glyph.x_advance for c in shaped.clusters for glyph in c.glyphs)

    x_start = rendered.visual_state(0).pixel.x
    x_end = rendered.visual_state(2).pixel.x
    assert x_end - x_start == round(advance)
