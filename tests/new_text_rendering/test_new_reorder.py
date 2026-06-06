"""Tests for the flat-model L2 reorder (`new_text_partition.reorder`).

`reorder_line` is exercised end-to-end (partition -> shape -> reorder) on
mixed-bidi cases, asserting the glyphs come out in visual (left-to-right) order
via their `logical_position`s. The L2 itself lives in vibidi (covered by
`tests/vibidi`), so it is not re-tested here.
"""

import pygame
import pygame.freetype
import pytest

from videre.core.shaping.new_text_partition.partitioner import partition_text
from videre.core.shaping.new_text_partition.reorder import reorder_line
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


def test_digits_in_rtl_run_use_real_levels(shaper: Shaper) -> None:
    """A European number inside a Hebrew run gets level 2 (not pseudo-0): in a
    base-LTR paragraph the digits render to the LEFT of the (reversed) Hebrew
    letters, not the right. The old pseudo-levels got this backwards; vibidi's
    real levels fix it."""
    text = "abc אבג 123 end"  # pos 4-6 Hebrew, 8-10 digits
    positions = _positions(text, shaper)
    assert positions.index(8) < positions.index(4)  # "123" visually before אבג
    assert [p for p in positions if p in (8, 9, 10)] == [8, 9, 10]  # digits LTR
    assert [p for p in positions if p in (4, 5, 6)] == [6, 5, 4]  # Hebrew reversed
