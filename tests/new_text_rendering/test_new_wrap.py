"""Tests for the flat-model width wrap (`text_partition.wrap`).

Builds real `ShapedTextLine`s via partition_text + shape_line, then wraps and
checks: content preservation/order, width respected for multi-word lines,
atomic overflow stays whole, breakable (CJK) splits, gap consumption at
breaks, and passthrough edge cases.
"""

import pygame
import pygame.freetype
import pytest

from videre.core.shaping.rendering.wrap import wrap_lines
from videre.core.shaping.shaper import Shaper, shape_line
from videre.core.shaping.text_partition.partitioner import partition_text


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


def _shaped(text: str, shaper: Shaper, size: int = 16):
    (line,) = partition_text(text).lines
    return shape_line(line, shaper, size)


def _nongap_positions(line) -> list[int]:
    return [
        g.logical_position for u in line.units if not u.unit.is_gap for g in u.glyphs
    ]


def _advance(line) -> float:
    return sum(g.x_advance for u in line.units for g in u.glyphs)


# -- Passthrough edge cases --------------------------------------------------


def test_width_zero_passes_through(shaper: Shaper) -> None:
    sline = _shaped("hello world", shaper)
    out = list(wrap_lines([sline], width=0, wrap_words=True))
    assert len(out) == 1
    assert out[0] is sline


def test_empty_line_passes_through(shaper: Shaper) -> None:
    (line,) = partition_text("").lines
    sline = shape_line(line, shaper, 16)
    out = list(wrap_lines([sline], width=100, wrap_words=True))
    assert len(out) == 1
    assert not out[0].units


# -- Word wrap ---------------------------------------------------------------


def test_word_wrap_preserves_content_in_order(shaper: Shaper) -> None:
    """Every non-gap glyph survives the wrap, in the same order: word wrap
    never loses or reorders content, only inserts line breaks."""
    sline = _shaped("alpha beta gamma delta epsilon zeta", shaper)
    out = list(wrap_lines([sline], width=100, wrap_words=True))
    assert len(out) > 1
    flat = [p for sl in out for p in _nongap_positions(sl)]
    assert flat == _nongap_positions(sline)


def test_word_wrap_multi_word_lines_fit_width(shaper: Shaper) -> None:
    sline = _shaped("alpha beta gamma delta epsilon zeta", shaper)
    width = 120
    out = list(wrap_lines([sline], width=width, wrap_words=True))
    for sl in out:
        nongap = [u for u in sl.units if not u.unit.is_gap]
        if len(nongap) > 1:  # a line that packed several words must fit
            assert _advance(sl) <= width


def test_atomic_word_too_long_stays_on_one_line(shaper: Shaper) -> None:
    """An atomic word wider than `width` is emitted whole (overflow), never
    split mid-word."""
    sline = _shaped("supercalifragilisticexpialidocious", shaper)
    out = list(wrap_lines([sline], width=40, wrap_words=True))
    assert len(out) == 1
    assert _advance(out[0]) > 40  # genuinely overflows


# -- Breakable (CJK) ---------------------------------------------------------


def test_breakable_cjk_splits_under_word_wrap(shaper: Shaper) -> None:
    """A breakable CJK run splits at cluster boundaries even under word wrap."""
    sline = _shaped("你好世界你好世界你好世界", shaper)
    out = list(wrap_lines([sline], width=80, wrap_words=True))
    assert len(out) > 1
    # Content preserved in order.
    flat = [p for sl in out for p in _nongap_positions(sl)]
    assert flat == _nongap_positions(sline)


def test_cjk_wrap_does_not_leave_parentheses_alone(shaper: Shaper) -> None:
    text = "(\u4e2d\u6587)"
    sline = _shaped(text, shaper)
    ideograph_width = int(_advance(_shaped("\u4e2d", shaper)))
    out = list(wrap_lines([sline], width=ideograph_width, wrap_words=True))

    lines = [_nongap_positions(line) for line in out]
    assert len(lines) > 1
    assert all(positions != [0] for positions in lines)
    assert all(positions != [len(text) - 1] for positions in lines)


def test_word_wrap_can_break_after_hyphen(shaper: Shaper) -> None:
    text = "porte-monnaie"
    sline = _shaped(text, shaper)
    prefix_end = text.index("-") + 1
    prefix_width = int(_advance(_shaped(text[:prefix_end], shaper)))
    out = list(wrap_lines([sline], width=prefix_width, wrap_words=True))

    assert len(out) == 2
    assert max(_nongap_positions(out[0])) == prefix_end - 1
    assert min(_nongap_positions(out[1])) == prefix_end


# -- Cluster wrap ------------------------------------------------------------


def test_cluster_wrap_can_break_inside_latin_word(shaper: Shaper) -> None:
    """`wrap_words=False` breaks at any cluster, so even one long Latin word
    splits across lines instead of overflowing."""
    sline = _shaped("supercalifragilisticexpialidocious", shaper)
    out = list(wrap_lines([sline], width=80, wrap_words=False))
    assert len(out) > 1
    for sl in out:
        assert _advance(sl) <= 80
    flat = [p for sl in out for p in _nongap_positions(sl)]
    assert flat == _nongap_positions(sline)


# -- Gap consumption ---------------------------------------------------------


def test_wrap_break_consumes_inter_word_gap(shaper: Shaper) -> None:
    """A break gap contributes no painted space or width at a line edge.

    Its source range may remain as an invisible gap unit for caret/selection.
    """
    sline = _shaped("alpha beta gamma delta epsilon zeta", shaper)
    out = list(wrap_lines([sline], width=120, wrap_words=True))
    for sl in out:
        painted = [
            unit for unit in sl.units if any(glyph.paint for glyph in unit.glyphs)
        ]
        assert not painted[0].unit.is_gap
        assert not painted[-1].unit.is_gap
        for unit in sl.units:
            if unit.unit.is_gap and not any(glyph.paint for glyph in unit.glyphs):
                assert all(glyph.x_advance == 0 for glyph in unit.glyphs)


def test_inter_word_gap_kept_when_not_breaking(shaper: Shaper) -> None:
    """Two words that fit on one line keep the gap between them."""
    sline = _shaped("hi bye", shaper)
    out = list(wrap_lines([sline], width=500, wrap_words=True))
    assert len(out) == 1
    kinds = [u.unit.is_gap for u in out[0].units]
    assert kinds == [False, True, False]


def test_trailing_gap_does_not_strand_last_fitting_word(shaper: Shaper) -> None:
    """Regression: a word that fits must stay on the line; the inter-word
    space that follows it must not push it to the next line (a trailing space
    is consumed at the line end). The previous greedy backed up to the gap
    *before* the last word when the gap *after* it overflowed."""
    two = _advance(_shaped("alpha beta", shaper))
    # Width fits "alpha beta" comfortably but not the following "gamma".
    out = list(
        wrap_lines(
            [_shaped("alpha beta gamma", shaper)], int(two) + 10, wrap_words=True
        )
    )
    # "beta" (source positions 6..9) must be on the first line, with "alpha".
    assert max(_nongap_positions(out[0])) >= 9
