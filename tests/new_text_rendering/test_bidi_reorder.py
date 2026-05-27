"""Tests for UAX#9 rule L2 visual reordering inside the shaped
rendering pipeline.

Three layers are exercised:

- `_l2_reorder(levels, base_level)`: the pure-function permutation,
  hit with edge cases (empty, all-same level, single isolated RTL run,
  nested levels).
- `_apply_l2_to_line(line)`: reorders words and intra-word runs of a
  `ShapedLine`, returning per-word and per-run source offsets so
  `_build_line_layout` can map source positions through the visual
  permutation.
- End-to-end via `ShapedTextRendering.render_text` on real mixed
  scripts: layout items must come back in visual (left-to-right)
  pixel order with `x_start` strictly increasing, even though their
  `source_start` ranges are non-monotonic in mixed bidi.
"""

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.shaping import ShapedTextRendering
from videre.core.shaping.pipeline import shape_text
from videre.core.shaping.shaped import ShapedLine
from videre.core.shaping.text_rendering import _apply_l2_to_line, _l2_reorder


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


ARAB = chr(0x0623) + chr(0x0628) + chr(0x062C)  # 3-codepoint Arabic word


# -- _l2_reorder ------------------------------------------------------------


def test_l2_reorder_empty_returns_empty() -> None:
    assert _l2_reorder([], 0) == []


def test_l2_reorder_pure_ltr_is_identity() -> None:
    assert _l2_reorder([0, 0, 0, 0], 0) == [0, 1, 2, 3]


def test_l2_reorder_single_rtl_atom_in_ltr_context_is_identity() -> None:
    """A single isolated RTL item in an LTR paragraph reverses a
    sub-sequence of length 1 — no-op. Matches the typical
    `<latin> <arabic> <latin>` case where the Arabic word stays in
    place; the per-glyph visual reversal is HarfBuzz's job, not L2's."""
    assert _l2_reorder([0, 1, 0], 0) == [0, 1, 2]


def test_l2_reorder_multiple_rtl_atoms_in_ltr_context_are_reversed() -> None:
    """Three contiguous RTL items embedded in an LTR paragraph get
    reversed as a block. Their source order is undone visually."""
    assert _l2_reorder([0, 1, 1, 1, 0], 0) == [0, 3, 2, 1, 4]


def test_l2_reorder_pure_rtl_paragraph_reverses_all() -> None:
    """In a RTL paragraph, every level >= 1 sub-sequence is reversed.
    For all-level-1 input the whole list flips."""
    assert _l2_reorder([1, 1, 1], 1) == [2, 1, 0]


def test_l2_reorder_rtl_context_with_ltr_run_inserts_two_passes() -> None:
    """RTL paragraph (base 1) with an LTR run (level 2) inserted: the
    inner level-2 sub-sequence is reversed first (no-op for single
    item), then the whole level >= 1 sub-sequence (= all of it) is
    reversed. Net: original order reversed."""
    assert _l2_reorder([1, 2, 1], 1) == [2, 1, 0]


def test_l2_reorder_rtl_context_with_multiple_ltr_runs_keeps_ltr_internal_order() -> (
    None
):
    """In a RTL paragraph, a sequence [RTL, LTR, LTR, RTL]: the inner
    [LTR, LTR] (level 2) is reversed first → [RTL, LTR2, LTR1, RTL],
    then the whole thing (level >= 1) is reversed →
    [RTL_last, LTR1, LTR2, RTL_first]. So adjacent LTR items inside a
    RTL paragraph keep their reading order relative to each other."""
    assert _l2_reorder([1, 2, 2, 1], 1) == [3, 1, 2, 0]


def test_l2_reorder_deeply_nested_levels() -> None:
    """Levels [1, 2, 3, 2, 1] in a RTL paragraph: thresholds 3, 2, 1.
    Threshold 3: reverse [3] alone → no change.
    Threshold 2: reverse contiguous >= 2 = [2, 3, 2] block →
      original positions [1, 2, 3] become [3, 2, 1] in the permutation.
    Threshold 1: reverse the whole list."""
    out = _l2_reorder([1, 2, 3, 2, 1], 1)
    # After threshold 2 the working order is [0, 3, 2, 1, 4] (the
    # middle block reversed), then threshold 1 reverses everything
    # → [4, 1, 2, 3, 0].
    assert out == [4, 1, 2, 3, 0]


# -- _apply_l2_to_line ------------------------------------------------------


def _shape_one_line(text: str, split_words: bool = False) -> ShapedLine:
    lines = list(shape_text(text, 16, split_words=split_words))
    assert len(lines) == 1
    return lines[0]


def test_apply_l2_pure_ltr_line_is_identity() -> None:
    sl = _shape_one_line("hello world", split_words=True)
    new_line, word_offsets, run_offsets = _apply_l2_to_line(sl)
    assert new_line.words == sl.words
    # Word offsets in source order: "hello" at 0, "world" at 6.
    assert word_offsets == (0, 6)


def test_apply_l2_pure_rtl_line_reverses_words() -> None:
    """Two Arabic words in a RTL paragraph: visually the second one
    (source) sits at the visual left edge."""
    # Two-word Arabic text. `split_words=True` is required to get two
    # ShapedWords; with `False` the whole line collapses into one word
    # whose runs are reordered (covered by the next test).
    text = ARAB + " " + ARAB
    sl = _shape_one_line(text, split_words=True)
    assert len(sl.words) == 2
    new_line, word_offsets, _ = _apply_l2_to_line(sl)
    # In RTL paragraph, word order is reversed: word[1] (source) lands
    # visual first. The new ShapedWord is a fresh instance (its runs
    # may have been reordered too) so compare by source_text rather
    # than identity.
    assert new_line.words[0].runs[0].source_text == sl.words[1].runs[0].source_text
    assert new_line.words[1].runs[0].source_text == sl.words[0].runs[0].source_text
    # The source offset of word[1] (now visual first) is 4 (after
    # ARAB + " " in source), and word[0] is at 0.
    assert word_offsets == (4, 0)


def test_apply_l2_single_word_with_mixed_runs_reorders_runs() -> None:
    """Without `split_words`, a mixed text collapses to one ShapedWord
    holding several runs. L2 must reorder those runs within the word.

    Note on offsets: source-level splitting by bidi level absorbs the
    inter-word spaces into the adjacent same-level runs (the spaces
    inherit the RTL context level, so they bond to the surrounding
    Arabic chunks). So the runs cover [0..4) (ARAB+sp), [4..9) (Paris),
    [9..13) (sp+ARAB), not [0..3), [3..10), [10..13).
    """
    text = ARAB + " Paris " + ARAB
    sl = _shape_one_line(text, split_words=False)
    assert len(sl.words) == 1
    # Three runs by (level, script): ARAB+sp (RTL), Paris (LTR), sp+ARAB (RTL).
    assert len(sl.words[0].runs) == 3
    new_line, _, run_offsets = _apply_l2_to_line(sl)
    assert len(new_line.words) == 1
    # In RTL paragraph the runs flip in visual order.
    new_runs = new_line.words[0].runs
    assert new_runs[0].source_text == sl.words[0].runs[2].source_text
    assert new_runs[1].source_text == sl.words[0].runs[1].source_text
    assert new_runs[2].source_text == sl.words[0].runs[0].source_text
    # run_offsets are the SOURCE offsets (within the word) of each
    # visual run. Source order offsets: 0, 4, 9. Visual order: 9, 4, 0.
    assert run_offsets[0] == (9, 4, 0)


# -- End-to-end via render_text --------------------------------------------


def _items_of(fake_win, text: str) -> list:
    out, _ = ShapedTextRendering(fake_win.backend, size=16).render_text(
        text, color=Color(0, 0, 0)
    )
    assert len(out.line_layouts) == 1
    return list(out.line_layouts[0].items)


def test_render_text_items_are_in_visual_pixel_order(fake_win) -> None:
    """The strongest invariant after L2: items must come back with
    `x_start` strictly non-decreasing — they describe the line left
    to right in painted pixel order, regardless of script or
    direction."""
    text = "abc " + ARAB + " def"
    items = _items_of(fake_win, text)
    xs = [it.x_start for it in items]
    assert xs == sorted(xs), f"items not in visual pixel order: {xs}"


def test_render_text_rtl_context_inverts_run_order_visually(fake_win) -> None:
    """RTL paragraph (`base=1`) with an LTR word inserted: the visual
    leftmost items must come from the LAST word in source order
    (highest source positions), demonstrating L2's overall reversal."""
    text = ARAB + " Paris " + ARAB
    items = _items_of(fake_win, text)
    leftmost = min(items, key=lambda it: it.x_start)
    rightmost = max(items, key=lambda it: it.x_end)
    # In source, the last codepoint is the last char of the second
    # Arabic word (position len(text) - 1). After L2 it must sit
    # visually on the left.
    assert leftmost.source_start >= len(text) - 4  # last Arabic word range
    # And the first codepoint (Arabic[0]) sits visually on the right.
    assert rightmost.source_end <= 4  # first Arabic word range


def test_render_text_ltr_context_with_rtl_word_keeps_run_order(fake_win) -> None:
    """LTR paragraph with a single RTL word inserted (the 'turkish
    ottoman' shape): visually the runs come out in source order
    (LTR → RTL → LTR); only the *internal* glyphs of the RTL run are
    flipped, which is HarfBuzz's job, not L2's."""
    text = "abc " + ARAB + " def"
    items = _items_of(fake_win, text)
    # Visually-leftmost item belongs to the first LTR chunk (source 'a').
    leftmost = min(items, key=lambda it: it.x_start)
    assert leftmost.source_start == 0
    # Visually-rightmost item belongs to the last LTR chunk
    # (last character of "def").
    rightmost = max(items, key=lambda it: it.x_end)
    assert rightmost.source_end == len(text)


def test_render_text_pure_ltr_round_trips_unchanged_by_l2(fake_win) -> None:
    """Pure-LTR text: L2 is the identity; pos_to_pixel / pixel_to_pos
    round-trip at every source position (no caret-ambiguity boundary).
    """
    text = "hello world"
    out, _ = ShapedTextRendering(fake_win.backend, size=16).render_text(
        text, color=Color(0, 0, 0)
    )
    for p in range(len(text) + 1):
        caret = out.pos_to_pixel(p)
        recovered = out.pixel_to_pos(caret.x, caret.y_top + 1)
        assert recovered == p, f"round-trip failed at pos {p}: got {recovered}"


def test_render_text_arabic_internal_carets_move_right_to_left(fake_win) -> None:
    """Inside an RTL Arabic run embedded in LTR context, advancing the
    source position should make the caret move LEFT visually. We probe
    INSIDE the run (positions 3, 4) to avoid the boundary ambiguity at
    positions 2 and 5 (those would need an affinity bit to disambiguate
    "after the last LTR char" from "before the first RTL char")."""
    text = "ab" + ARAB + "cd"
    out, _ = ShapedTextRendering(fake_win.backend, size=16).render_text(
        text, color=Color(0, 0, 0)
    )
    # Positions 3 and 4 sit strictly inside the Arabic run, between
    # two cluster boundaries — no LTR boundary, no ambiguity.
    x_at_3 = out.pos_to_pixel(3).x
    x_at_4 = out.pos_to_pixel(4).x
    assert x_at_3 > x_at_4, (
        f"caret should move LEFT as source advances in RTL run: "
        f"pos3={x_at_3}, pos4={x_at_4}"
    )
