"""Tests for the visual-navigation wiring through `TextRenderingResult`'s
protocol methods (`visual_state`, `next_visual`, `prev_visual`,
`next_visual_word`, `prev_visual_word`) and through `compute_key_x`.

Rather than spinning up a real `TextInput` widget (which would force
choosing a renderer backend via env var and complicate parallel test
execution), these tests probe the new behavior at the seams: the
shaped `ShapedRenderedText` implements the protocol, so we exercise
those methods directly and via `compute_key_x`.
"""

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.shaping import ShapedTextRendering
from videre.widgets.textinput.keyboard_handling import compute_key_x


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


ARAB = chr(0x0623) + chr(0x0628) + chr(0x062C)


def _render(text: str):
    return ShapedTextRendering(size=16).render_text(text, color=Color(0, 0, 0))


# -- compute_key_x with shaped rendered (visual movement) ------------------


def _compute(out, *, text: str, cursor: int, ctrl=False, shift=False, right=True):
    return compute_key_x(
        text=text,
        cursor_state=out.visual_state(cursor),
        selection=None,
        ctrl=ctrl,
        shift=shift,
        right=right,
        rendered=out,
    )


def test_compute_key_x_visual_right_in_ltr_matches_source_order() -> None:
    """LTR text: visual right == source+1 (no surprise)."""
    out, _ = _render("hello")
    ret = _compute(out, text="hello", cursor=0, right=True)
    assert ret.out_pos == 1


def test_compute_key_x_visual_right_in_pure_rtl_decreases_source() -> None:
    """In a pure-RTL Arabic word, visual right makes the source
    position DECREASE — visually the caret moves right, but the
    next glyph in visual order corresponds to a smaller source
    position. This is exactly what the user wants when typing arrow
    keys in Arabic text."""
    out, _ = _render(ARAB)
    # Start at source position 3 (visual leftmost). Visual right moves
    # to source 2 (one glyph to the right pixel-wise).
    ret = _compute(out, text=ARAB, cursor=3, right=True)
    assert ret.out_pos == 2


def test_compute_key_x_visual_left_in_pure_rtl_increases_source() -> None:
    """Symmetric: visual left in RTL increases source position."""
    out, _ = _render(ARAB)
    ret = _compute(out, text=ARAB, cursor=2, right=False)
    assert ret.out_pos == 3


# -- _mouse_to_pos behavior (via the protocol) -----------------------------


def test_visual_state_at_pixel_clicks_at_left_edge_yields_first_position() -> None:
    """Clicking at x=0 should return source position 0."""
    out, _ = _render("hello world")
    assert out.visual_state_at_pixel(0, 0).pos == 0


def test_visual_state_at_pixel_clicks_inside_rtl_run_picks_visual_glyph() -> None:
    """Clicking inside the visual middle of a 3-glyph Arabic word
    should yield a source position that's inside the run (1 or 2,
    not the endpoints 0 or 3)."""
    out, rendered = _render(ARAB)
    mid_x = rendered.surface.get_width() // 2
    pos = out.visual_state_at_pixel(mid_x, 0).pos
    assert 0 < pos < 3, f"middle click should hit run interior, got {pos}"


# -- Ctrl+arrow (visual word movement) -------------------------------------


def test_ctrl_right_visual_in_ltr_matches_source_order() -> None:
    """LTR text: visual word-end == source word-end."""
    text = "hello world"
    out, _ = _render(text)
    ret = _compute(out, text=text, cursor=0, ctrl=True, right=True)
    assert ret.out_pos == 5  # end of "hello"


def test_ctrl_right_visual_jumps_to_next_word_in_ltr_then_rtl() -> None:
    """Mixed LTR-RTL: starting at source 0, Ctrl+Right jumps to the
    end of "abc" (= 3) — the next word-end visually to the right."""
    text = "abc " + ARAB
    out, _ = _render(text)
    ret = _compute(out, text=text, cursor=0, ctrl=True, right=True)
    assert ret.out_pos == 3


def test_ctrl_left_visual_in_ltr_matches_source_order() -> None:
    """LTR text: Ctrl+Left (visual) == cursword's word-start."""
    text = "hello world"
    out, _ = _render(text)
    ret = _compute(out, text=text, cursor=11, ctrl=True, right=False)
    assert ret.out_pos == 6  # start of "world"


# -- Real-world traversal: Turkish Ottoman mixed bidi ----------------------
#
# A real sentence with a Latin prefix, an Arabic core (three words
# separated by spaces), a slash, and a Latin transliteration suffix.
# This is the actual content the user typed into the demo, and the one
# that surfaced the cursor-stall bug (loop at the LTR/RTL frontier when
# `source_to_glyph` lost the state-based context).

# "دولت" = state / dynasty
_AR_WORD_1 = chr(0x062F) + chr(0x0648) + chr(0x0644) + chr(0x062A)
# "عليه" = supreme
_AR_WORD_2 = chr(0x0639) + chr(0x0644) + chr(0x064A) + chr(0x0647)
# "عثمانیه" = Ottoman
_AR_WORD_3 = (
    chr(0x0639)
    + chr(0x062B)
    + chr(0x0645)
    + chr(0x0627)
    + chr(0x0646)
    + chr(0x06CC)
    + chr(0x0647)
)
TURK_OTTOMAN = (
    "en turc ottoman : "
    + _AR_WORD_1
    + " "
    + _AR_WORD_2
    + " "
    + _AR_WORD_3
    + " / devlet-i ʿaliyye-i"
)


def _forward_traversal(out, start: int, end: int) -> list[int]:
    """Walk visually right with `next_visual` until the cursor stops
    advancing. Threads the navigation state — the whole point of the
    state-based API is that consecutive arrow presses don't re-derive
    the cursor from the source pos, avoiding bidi-frontier loops."""
    state = out.visual_state(start)
    visited = [state.pos]
    bound = (end + 10) * 3  # generous safety
    for _ in range(bound):
        new_state = out.next_visual(state)
        if new_state == state:
            break  # no further visual right
        state = new_state
        visited.append(state.pos)
        if state.pos == end:
            break
    return visited


def _backward_traversal(out, start: int) -> list[int]:
    state = out.visual_state(start)
    visited = [state.pos]
    bound = (start + 10) * 3
    for _ in range(bound):
        new_state = out.prev_visual(state)
        if new_state == state:
            break
        state = new_state
        visited.append(state.pos)
        if state.pos == 0:
            break
    return visited


def test_turkish_ottoman_forward_traversal_reaches_end() -> None:
    """Arrow-right from source position 0 must land at `len(text)`."""
    out, _ = _render(TURK_OTTOMAN)
    visited = _forward_traversal(out, 0, len(TURK_OTTOMAN))
    final = visited[-1]
    assert final == len(TURK_OTTOMAN), (
        f"forward traversal stopped at {final} (expected {len(TURK_OTTOMAN)}); "
        f"path len={len(visited)}, last 10: {visited[-10:]}"
    )


def test_turkish_ottoman_backward_traversal_reaches_start() -> None:
    """Symmetric: arrow-left from `len(text)` must reach 0."""
    out, _ = _render(TURK_OTTOMAN)
    visited = _backward_traversal(out, len(TURK_OTTOMAN))
    final = visited[-1]
    assert final == 0, (
        f"backward traversal stopped at {final} (expected 0); "
        f"path len={len(visited)}, last 10: {visited[-10:]}"
    )


def test_turkish_ottoman_forward_then_backward_round_trip() -> None:
    """Stronger: a forward traversal followed by a backward one must
    visit exactly the same set of source positions."""
    out, _ = _render(TURK_OTTOMAN)
    forward = _forward_traversal(out, 0, len(TURK_OTTOMAN))
    backward = _backward_traversal(out, len(TURK_OTTOMAN))
    assert set(forward) == set(backward), (
        f"forward / backward visited different positions:\n"
        f"  only-fwd: {sorted(set(forward) - set(backward))}\n"
        f"  only-bwd: {sorted(set(backward) - set(forward))}"
    )


def _forward_pixels(out, start: int, end: int) -> list[int]:
    """Forward traversal, returning the pixel x of the caret at each
    step. The painted caret must move monotonically (left-to-right)
    in pixels: any jump betrays the bug where `pos_to_pixel(pos)`
    disagreed with where the state-based navigation thinks the caret
    is."""
    state = out.visual_state(start)
    xs = [state.pixel.x]
    bound = (end + 10) * 3
    for _ in range(bound):
        new_state = out.next_visual(state)
        if new_state == state:
            break
        state = new_state
        xs.append(state.pixel.x)
        if state.pos == end:
            break
    return xs


def _backward_pixels(out, start: int) -> list[int]:
    state = out.visual_state(start)
    xs = [state.pixel.x]
    bound = (start + 10) * 3
    for _ in range(bound):
        new_state = out.prev_visual(state)
        if new_state == state:
            break
        state = new_state
        xs.append(state.pixel.x)
        if state.pos == 0:
            break
    return xs


def test_turkish_ottoman_forward_caret_pixel_is_monotonic() -> None:
    """The painted caret must drift visually left-to-right as the
    user presses arrow-right; no jump backwards in pixels."""
    out, _ = _render(TURK_OTTOMAN)
    xs = _forward_pixels(out, 0, len(TURK_OTTOMAN))
    for a, b in zip(xs, xs[1:]):
        assert a <= b, (
            f"painted caret jumped left on a right-arrow press: "
            f"...{a} -> {b}; full path = {xs}"
        )


def test_turkish_ottoman_backward_caret_pixel_is_monotonic() -> None:
    """Symmetric: the painted caret must drift visually right-to-left
    as the user presses arrow-left."""
    out, _ = _render(TURK_OTTOMAN)
    xs = _backward_pixels(out, len(TURK_OTTOMAN))
    for a, b in zip(xs, xs[1:]):
        assert a >= b, (
            f"painted caret jumped right on a left-arrow press: "
            f"...{a} -> {b}; full path = {xs}"
        )


def test_hello_plus_turkish_ottoman_backward_caret_pixel_is_monotonic() -> None:
    """User-reported scenario: TextInput starts with "Hello!", user
    pastes the turkish-ottoman string at the end, then traverses
    backward with arrow-left. The painted caret must drift left
    monotonically — no jump across the Arabic run."""
    text = "Hello!" + TURK_OTTOMAN
    out, _ = _render(text)
    xs = _backward_pixels(out, len(text))
    for a, b in zip(xs, xs[1:]):
        assert a >= b, (
            f"painted caret jumped right on a left-arrow press: "
            f"...{a} -> {b}; full path = {xs}"
        )


# -- Selection / delete / copy in bidi-mixed text --------------------------


def test_visual_range_to_source_set_pure_ltr_is_contiguous_range() -> None:
    """LTR text: the source set is just `range(start, end)`."""
    out, _ = _render("hello world")
    assert out.visual_range_to_source_set(0, 5) == frozenset(range(0, 5))


def test_visual_range_to_source_set_pure_rtl_is_set_of_source_indices() -> None:
    """3-codepoint Arabic word: visual order is reversed in source.
    Selecting the whole word visually gives source set {0, 1, 2}."""
    out, _ = _render(ARAB)
    assert out.visual_range_to_source_set(0, 3) == frozenset({0, 1, 2})


def test_visual_range_to_source_set_partial_rtl_picks_visually_adjacent() -> None:
    """Selecting visual positions [0, 2) in a 3-char Arabic word
    picks the visual-leftmost 2 items, which in source order are
    the two LAST codepoints (largest source indices)."""
    out, _ = _render(ARAB)
    # ARAB has 3 codepoints (source 0, 1, 2). In visual order from
    # left to right: item[0] covers source 2, item[1] covers source 1,
    # item[2] covers source 0. Selection [0, 2) = items 0 and 1 =
    # source {2, 1}.
    assert out.visual_range_to_source_set(0, 2) == frozenset({1, 2})


def test_visual_range_to_source_set_across_ltr_rtl_boundary_is_non_contiguous() -> None:
    """Selection that crosses a LTR/RTL boundary: source set is the
    union of the contiguous LTR slice and the contiguous RTL slice,
    which on its own may be non-contiguous in source order."""
    text = "ab" + ARAB + "cd"
    out, _ = _render(text)
    # Visual order: a, b, ARAB_visual_left (src 4), ARAB_mid (src 3),
    # ARAB_visual_right (src 2), c, d.
    # Selecting visual [1, 4) = items b, ARAB_visual_left, ARAB_mid
    # = source {1, 4, 3}.
    assert out.visual_range_to_source_set(1, 4) == frozenset({1, 3, 4})


def test_visual_selection_rects_pure_ltr_returns_one_contiguous_rect() -> None:
    """LTR text: one rectangle covering [item[start].x_start,
    item[end-1].x_end]."""
    out, _ = _render("hello world")
    rects = out.visual_selection_rects(0, 5)
    assert len(rects) == 1
    assert rects[0].width > 0


def test_visual_selection_rects_across_bidi_boundary_is_single_ribbon() -> None:
    """The whole point of the visual model: even on a bidi-mixed
    selection, the rectangle is a single ribbon (no gaps)."""
    text = "ab" + ARAB + "cd"
    out, _ = _render(text)
    rects = out.visual_selection_rects(1, 5)  # spans from 'b' to ARAB middle
    assert len(rects) == 1


def test_total_visual_count_matches_total_items() -> None:
    """The select-all upper bound equals the sum of items across all
    lines. For a single-line LTR text it equals len(text)."""
    text = "hello"
    out, _ = _render(text)
    assert out.total_visual_count() == len(text)


def test_total_visual_count_arabic_matches_codepoint_count() -> None:
    """For an Arabic word (one cluster per codepoint), total visual
    count equals the codepoint count."""
    out, _ = _render(ARAB)
    assert out.total_visual_count() == len(ARAB)


def test_visual_state_at_round_trips_with_state_visual_pos() -> None:
    """For every valid visual position, visual_state_at(v).visual_pos
    must equal v."""
    out, _ = _render("ab" + ARAB + "cd")
    total = out.total_visual_count()
    for v in range(total + 1):
        assert out.visual_state_at(v).visual_pos == v


def test_delete_visual_selection_across_ltr_rtl_boundary() -> None:
    """End-to-end behavior of `_delete_selection` (simulated): take
    a visual range, derive its source set, rebuild the string by
    filtering out those indices. Asserts the rebuilt string is what
    the user would expect."""
    text = "ab" + ARAB + "cd"
    out, _ = _render(text)
    # Select visual [1, 4) = source set {1, 3, 4}.
    indices = sorted(out.visual_range_to_source_set(1, 4))
    keep = set(indices)
    out_text = "".join(c for i, c in enumerate(text) if i not in keep)
    # Source 0, 2, 5, 6 kept = 'a', ARAB[0], 'c', 'd'.
    assert out_text == "a" + ARAB[0] + "cd"


def test_copy_visual_selection_preserves_source_order() -> None:
    """Copy uses source-order concatenation of selected codepoints
    (= what browsers / Word do). The clipboard payload, re-rendered
    in another app, reproduces the original visual look."""
    text = "ab" + ARAB + "cd"
    out, _ = _render(text)
    # Select visual [1, 4) = source set {1, 3, 4}.
    indices = sorted(out.visual_range_to_source_set(1, 4))
    copied = "".join(text[i] for i in indices)
    # Source order: text[1]='b', text[3]=ARAB[1], text[4]=ARAB[2].
    assert copied == "b" + ARAB[1] + ARAB[2]
