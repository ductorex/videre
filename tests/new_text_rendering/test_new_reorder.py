"""Tests for the flat-model L2 reorder (`new_text_partition.reorder`).

`_l2_reorder` / `_pseudo_level` are pinned as pure functions; `reorder_line`
is exercised end-to-end (partition -> shape -> reorder) on the same mixed-bidi
cases as the legacy `test_bidi_reorder`, asserting the glyphs come out in
visual (left-to-right) order via their `logical_position`s.
"""

import pygame
import pygame.freetype
import pytest

from videre.core.shaping.new_text_partition.partitioner import partition_text
from videre.core.shaping.new_text_partition.reorder import (
    _l2_reorder,
    _pseudo_level,
    reorder_line,
)
from videre.core.shaping.new_text_partition.shaping import shape_line
from videre.core.shaping.shaper import Shaper

ARAB = "أبج"  # 3-codepoint Arabic chunk


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


def _positions(text: str, shaper: Shaper) -> list[int]:
    """logical_position of each glyph after partition -> shape -> reorder of a
    single-line text, in visual order."""
    (line,) = partition_text(text).lines
    gl = reorder_line(shape_line(line, shaper, 16))
    return [g.logical_position for g in gl.glyphs]


# -- _pseudo_level -----------------------------------------------------------


def test_pseudo_level() -> None:
    assert _pseudo_level(False, False) == 0  # LTR unit, LTR base
    assert _pseudo_level(True, False) == 1  # RTL unit, LTR base
    assert _pseudo_level(True, True) == 1  # RTL unit, RTL base
    assert _pseudo_level(False, True) == 2  # LTR unit, RTL base


# -- _l2_reorder (copy of the pure function) ---------------------------------


def test_l2_reorder_pure_ltr_is_identity() -> None:
    assert _l2_reorder([0, 0, 0], 0) == [0, 1, 2]


def test_l2_reorder_single_rtl_in_ltr_is_identity() -> None:
    assert _l2_reorder([0, 1, 0], 0) == [0, 1, 2]


def test_l2_reorder_pure_rtl_reverses_all() -> None:
    assert _l2_reorder([1, 1, 1], 1) == [2, 1, 0]


def test_l2_reorder_rtl_base_with_ltr_run() -> None:
    # [RTL, LTR, RTL] in an RTL paragraph: net reversal.
    assert _l2_reorder([1, 2, 1], 1) == [2, 1, 0]


# -- reorder_line end-to-end -------------------------------------------------


def test_ltr_glyphs_in_source_order(shaper: Shaper) -> None:
    positions = _positions("hello", shaper)
    assert positions == [0, 1, 2, 3, 4]


def test_rtl_glyphs_reversed(shaper: Shaper) -> None:
    """Pure Arabic, base RTL: visual order is the reverse of source, so the
    glyph `logical_position`s come out non-increasing."""
    positions = _positions(ARAB, shaper)
    assert positions, "expected glyphs"
    assert positions == sorted(positions, reverse=True)


def test_ltr_context_rtl_word_keeps_run_order(shaper: Shaper) -> None:
    """`abc <arabic> def` (LTR base): the RTL word stays in place; visually
    the first glyph is 'a' (pos 0) and the last is the final 'f'."""
    text = "abc " + ARAB + " def"
    positions = _positions(text, shaper)
    assert positions[0] == 0
    assert positions[-1] == len(text) - 1


def test_rtl_context_ltr_word_inverts_run_order(shaper: Shaper) -> None:
    """`<arabic> Paris <arabic>` (RTL base): L2 reverses overall, so the
    visually-leftmost glyph comes from the LAST Arabic word (high source
    positions) and the rightmost from the FIRST (positions 0..2)."""
    text = ARAB + " Paris " + ARAB
    positions = _positions(text, shaper)
    assert positions[0] >= len(text) - 3  # leftmost from the last Arabic word
    assert positions[-1] <= 2  # rightmost from the first Arabic word


def test_empty_line_reorders_to_no_glyphs(shaper: Shaper) -> None:
    (line,) = partition_text("").lines
    gl = reorder_line(shape_line(line, shaper, 16))
    assert gl.glyphs == []
