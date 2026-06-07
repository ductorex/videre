"""End-to-end bidi tests for `TextInput` on the SHAPED renderer.

These drive a real `TextInput` through `FakeUser` (click / arrows / backspace /
typing) on Arabic+Latin text. They live in `on_videre/` so the autouse
`_force_shaped` fixture routes `text_rendering()` through the shaped (HarfBuzz,
bidi-aware) pipeline — the legacy renderer has no bidi visual order, so these
would be meaningless against it.

Coverage:
- display of the mixed Arabic/Latin/CJK demo line (snapshot);
- visual cursor traversal, char and word, both directions (monotonic caret
  pixel, reaches both edges, forward/backward visit the same positions);
- selection by shift(+ctrl)+arrows (single on-screen ribbon) and select-all;
- editing that forces HarfBuzz to re-shape: deleting a space that rejoins two
  Arabic words, deleting a visual selection across a LTR/RTL boundary, and
  inserting Latin inside an Arabic word. Each asserts the resulting logical
  `value`, PROVES the re-shape at the glyph level (a neighbour's cluster
  glyphs change while distant ones stay), and snapshots the redisplay.
- Latin ligatures (`fi` -> one glyph): the inverse mapping (2 source chars ->
  1 glyph). The caret treats the ligature as one atomic unit (no slot between
  `f` and `i`), yet editing stays per source char and breaks the ligature.

The edit reshape proof uses `_clusters`: each Arabic letter rasterizes as a
base glyph (which encodes the joining form) plus its dots; a changed cluster
tuple means the letter genuinely re-shaped.
"""

import pygame
import pygame.freetype
import pytest

import videre
from videre.core.shaping.render import build_glyph_lines
from videre.core.shaping.rendering.layout import RenderedText
from videre.core.shaping.shaper import Shaper
from videre.testing.utils import TEXT_SAMPLES

# First line of the Arabic sample = what the demo's TextInput now starts with:
# Arabic (RTL) majority + Latin, CJK, IPA, digits, brackets.
ARABIC_LINE = TEXT_SAMPLES["arabic"].splitlines()[0]

# Five dual-joining Arabic letters: beh, teh, theh, jeem, hah.
BEH, TEH, THEH, JEEM, HAH = "بتثجح"

# Wide window so the long single line is fully visible / measurable.
_WIDE = {"width": 2300, "height": 120}


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


_SHAPER = Shaper()


def _clusters(text: str, size: int = 14) -> dict[int, tuple[int, ...]]:
    """source position -> tuple of glyph ids of its cluster (base + dots).

    The base glyph carries the Arabic joining form, so a changed tuple for a
    given source position means that letter re-shaped."""
    out: dict[int, list[int]] = {}
    for gl, _ in build_glyph_lines(text, _SHAPER, size):
        for g in gl.glyphs:
            out.setdefault(g.logical_position, []).append(g.glyph_id)
    return {k: tuple(v) for k, v in out.items()}


def _input(fake_win, text: str) -> videre.TextInput:
    ti = videre.TextInput(text)
    fake_win.controls = [videre.Container(ti, padding=videre.Padding.all(20))]
    fake_win.render()
    return ti


def _caret_x(ti: videre.TextInput) -> int:
    return ti._ensure_state().pixel.x


def _press(fake_win, ti, key: str, *, ctrl: bool = False, shift: bool = False) -> None:
    fake_win.user.keyboard_entry(key, ctrl=ctrl, shift=shift)
    fake_win.render()


def _click_source(fake_win, ti: videre.TextInput, source_pos: int) -> None:
    """Place the cursor at `source_pos` by clicking its caret pixel — the
    pattern `test_textinput` uses."""
    rendered = ti._text._rendered
    assert rendered is not None
    x = ti.global_x + rendered.visual_state(source_pos).pixel.x
    fake_win.user.click_at(x, ti.global_y + 1)
    fake_win.render()


def _traverse(fake_win, ti, key: str, *, ctrl: bool = False):
    """Press `key` until the caret stops moving; return the visited
    (caret_x, source_pos) list, including the start."""
    rendered = ti._text._rendered
    assert rendered is not None
    path = [(_caret_x(ti), ti._get_cursor())]
    for _ in range(rendered.total_visual_count() + 5):
        _press(fake_win, ti, key, ctrl=ctrl)
        step = (_caret_x(ti), ti._get_cursor())
        if step == path[-1]:
            break
        path.append(step)
    return path


def _focus_visual_start(fake_win, ti) -> None:
    """Focus the input and move the caret to the visual leftmost position."""
    fake_win.user.click_at(ti.global_x, ti.global_y + 1)
    fake_win.render()
    _traverse(fake_win, ti, "left")


# --------------------------------------------------------------------------
# 1. Display
# --------------------------------------------------------------------------


@pytest.mark.win_params(_WIDE)
def test_display_arabic_line(snap_win):
    """The mixed Arabic/Latin/CJK demo line renders through the widget."""
    _input(snap_win, ARABIC_LINE)


# --------------------------------------------------------------------------
# 2. Visual cursor traversal (char + word, both directions)
# --------------------------------------------------------------------------


@pytest.mark.win_params(_WIDE)
def test_visual_cursor_char_traversal(fake_win):
    ti = _input(fake_win, ARABIC_LINE)
    rendered = ti._text._rendered
    assert rendered is not None
    width = rendered.get_width()
    _focus_visual_start(fake_win, ti)

    fwd = _traverse(fake_win, ti, "right")  # left edge -> right edge
    bwd = _traverse(fake_win, ti, "left")  # right edge -> left edge
    fx = [x for x, _ in fwd]
    bx = [x for x, _ in bwd]

    assert fx == sorted(fx), f"right-arrow caret not monotonic: {fx}"
    assert bx == sorted(bx, reverse=True), f"left-arrow caret not monotonic: {bx}"
    assert fx[0] <= 2, f"did not start at the visual left edge: {fx[0]}"
    assert fx[-1] >= width - 5, f"did not reach the visual right edge: {fx[-1]}/{width}"
    assert {p for _, p in fwd} == {p for _, p in bwd}, (
        "forward / backward visited different source positions"
    )


@pytest.mark.win_params(_WIDE)
def test_visual_cursor_word_traversal(fake_win):
    ti = _input(fake_win, ARABIC_LINE)
    rendered = ti._text._rendered
    assert rendered is not None
    width = rendered.get_width()
    _focus_visual_start(fake_win, ti)

    fwd = _traverse(fake_win, ti, "right", ctrl=True)
    bwd = _traverse(fake_win, ti, "left", ctrl=True)
    fx = [x for x, _ in fwd]
    bx = [x for x, _ in bwd]

    assert fx == sorted(fx), f"ctrl+right caret not monotonic: {fx}"
    assert bx == sorted(bx, reverse=True), f"ctrl+left caret not monotonic: {bx}"
    assert fx[-1] >= width - 5, "word traversal did not reach the right edge"
    assert bx[-1] <= 2, "word traversal did not return to the left edge"
    # Word jumps are coarser than per-character steps.
    assert len(fwd) < rendered.total_visual_count()


# --------------------------------------------------------------------------
# 3. Selection
# --------------------------------------------------------------------------


@pytest.mark.win_params(_WIDE)
def test_selection_shift_arrows_single_ribbon(fake_win):
    ti = _input(fake_win, ARABIC_LINE)
    _focus_visual_start(fake_win, ti)
    rendered = ti._text._rendered
    assert isinstance(rendered, RenderedText)  # narrow for `_selection_rects`

    for k in range(1, 8):
        _press(fake_win, ti, "right", shift=True)
        sel = ti._get_selection()
        assert sel is not None, "shift+right should create a selection"
        assert sel == (0, k), f"selection should be (0, {k}), got {sel}"
        # Visually contiguous: one ribbon even across bidi runs.
        assert len(rendered._selection_rects(*sel)) == 1
        # Each visual step adds exactly one covered source codepoint.
        assert len(ti._selection_source_indices()) == k

    # A word extension stays a single ribbon too.
    _press(fake_win, ti, "right", ctrl=True, shift=True)
    sel = ti._get_selection()
    assert sel is not None
    assert len(rendered._selection_rects(*sel)) == 1


@pytest.mark.win_params(_WIDE)
def test_select_all(fake_win):
    ti = _input(fake_win, ARABIC_LINE)
    fake_win.user.click_at(ti.global_x, ti.global_y + 1)
    fake_win.render()
    _press(fake_win, ti, "a", ctrl=True)
    rendered = ti._text._rendered
    assert isinstance(rendered, RenderedText)  # narrow for `_selection_rects`
    total = rendered.total_visual_count()
    assert ti._get_selection() == (0, total)
    assert len(rendered._selection_rects(0, total)) == 1


# --------------------------------------------------------------------------
# 4. Backspace inside Arabic re-joins neighbours (HarfBuzz re-shapes)
# --------------------------------------------------------------------------


def test_backspace_in_arabic_rejoins(fake_win):
    # Two Arabic words separated by a space. Deleting the space makes the two
    # touching letters adjacent, so they must re-shape (final/initial -> medial).
    text = BEH + TEH + " " + TEH + BEH  # word1=بت  space  word2=تب
    ti = _input(fake_win, text)
    before = _clusters(text)
    fake_win.check("before")

    _click_source(
        fake_win, ti, 3
    )  # caret just before word2 -> backspace eats the space
    assert ti._get_cursor() == 3
    _press(fake_win, ti, "backspace")

    after_text = BEH + TEH + TEH + BEH
    assert ti.value == after_text
    after = _clusters(after_text)
    assert before[1] != after[1], "end-of-word1 teh did not re-shape (final->medial)"
    assert before[3] != after[2], (
        "start-of-word2 teh did not re-shape (initial->medial)"
    )
    assert before[0] == after[0], "distant beh should be unchanged"
    fake_win.check("after")


# --------------------------------------------------------------------------
# 5. Delete a visual selection across a LTR/RTL boundary
# --------------------------------------------------------------------------


def test_delete_selection_across_bidi_boundary(fake_win):
    # Latin + Arabic + Latin. A visual selection crossing the boundary maps to
    # a NON-contiguous source set; deleting it must remove exactly those source
    # codepoints and leave the rest correctly recombined.
    text = "ab" + BEH + TEH + THEH + "cd"
    ti = _input(fake_win, text)
    rendered = ti._text._rendered
    assert rendered is not None
    fake_win.check("before")

    _focus_visual_start(fake_win, ti)
    _press(fake_win, ti, "right")  # visual 0 -> 1 (past 'a')
    for _ in range(3):
        _press(fake_win, ti, "right", shift=True)  # select visual [1, 4)
    sel = ti._get_selection()
    assert sel == (1, 4)

    src_set = set(rendered.visual_range_to_source_set(1, 4))
    expected = "".join(c for i, c in enumerate(text) if i not in src_set)
    _press(fake_win, ti, "backspace")
    assert ti.value == expected
    assert ti._get_selection() is None
    fake_win.check("after")


# --------------------------------------------------------------------------
# 6. Insert Latin inside an Arabic word (neighbours re-shape, distant stable)
# --------------------------------------------------------------------------


def test_insert_latin_in_arabic(fake_win):
    text = BEH + TEH + THEH + JEEM + HAH  # 5 joined letters
    ti = _input(fake_win, text)
    before = _clusters(text)
    fake_win.check("before")

    _click_source(fake_win, ti, 2)  # caret between teh (src 1) and theh (src 2)
    assert ti._get_cursor() == 2
    fake_win.user.text_input("x")
    fake_win.render()

    after_text = BEH + TEH + "x" + THEH + JEEM + HAH
    assert ti.value == after_text
    after = _clusters(after_text)
    # The two letters now flanking the Latin 'x' re-shape...
    assert before[1] != after[1], "teh did not re-shape (medial->final)"
    assert before[2] != after[3], "theh did not re-shape (medial->initial)"
    # ...while letters away from the edit keep their glyphs.
    assert before[0] == after[0], "distant beh changed"
    assert before[3] == after[4], "distant jeem changed"
    assert before[4] == after[5], "distant hah changed"
    fake_win.check("after")


# --------------------------------------------------------------------------
# 7. Latin ligatures: 2 source chars -> 1 glyph (the inverse of the usual
#    1 char -> 1+ glyphs). The caret treats the ligature as one atomic unit.
# --------------------------------------------------------------------------


def test_latin_ligature_fuses_to_one_glyph(fake_win):
    # "fi" fuses into a single ligature glyph; 'i' gets no glyph of its own.
    fi = _clusters("fi")
    assert list(fi) == [0], "the fi ligature should be one cluster at source 0"
    assert _clusters("f")[0] != fi[0], "ligature glyph should differ from plain 'f'"
    # In context (a + fi + b) the ligature still counts as one visual item.
    ti = _input(fake_win, "afib")
    rendered = ti._text._rendered
    assert isinstance(rendered, RenderedText)
    assert rendered.total_visual_count() == 3  # a, [fi], b


def test_latin_ligature_cursor_is_atomic(fake_win):
    ti = _input(fake_win, "afib")  # a(0) f(1) i(2) b(3); "fi" -> 1 glyph
    rendered = ti._text._rendered
    assert rendered is not None
    # The mid-ligature source position has no caret slot of its own: it
    # collapses onto the ligature's left edge.
    assert rendered.visual_state(2).pixel.x == rendered.visual_state(1).pixel.x
    # Arrow-right steps OVER the ligature as a single unit (source 2 skipped),
    # and arrow-left mirrors it.
    _focus_visual_start(fake_win, ti)
    assert [p for _, p in _traverse(fake_win, ti, "right")] == [0, 1, 3, 4]
    assert [p for _, p in _traverse(fake_win, ti, "left")] == [4, 3, 1, 0]


def test_latin_ligature_selection_covers_both_chars(fake_win):
    # Selecting the single ligature item grabs BOTH source codepoints.
    ti = _input(fake_win, "afib")
    rendered = ti._text._rendered
    assert rendered is not None
    assert set(rendered.visual_range_to_source_set(1, 2)) == {1, 2}


def test_latin_ligature_backspace_breaks_it(fake_win):
    # Editing is per source char even though the caret is per ligature:
    # backspacing from the end of "fi" removes 'i', so the ligature breaks.
    ti = _input(fake_win, "fi")
    before = _clusters("fi")
    fake_win.check("ligature_before")
    _click_source(fake_win, ti, 2)  # caret after the ligature
    _press(fake_win, ti, "backspace")
    assert ti.value == "f"
    assert _clusters("f")[0] != before[0]  # re-shaped: ligature -> plain 'f'
    fake_win.check("ligature_after")
