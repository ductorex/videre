"""Tests for `shape_line`: a partition `Line` -> `ShapedTextLine` (glyphs).

Focus: the unit/glyph structure and the `logical_position` mapping in both
reading directions — the crux clarified during design (HarfBuzz takes logical
order in, emits visual order within a run, so an RTL unit's first glyph
maps to its last logical character).
"""

import pygame
import pygame.freetype
import pytest

from videre.core.shaping.new_text_partition.partitioner import partition_text
from videre.core.shaping.new_text_partition.shaping import shape_line
from videre.core.shaping.shaper import Shaper

ARAB = "أبج"  # 3-codepoint Arabic chunk


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


def _shape(text: str, shaper: Shaper, size: int = 16):
    part = partition_text(text)
    return part, [shape_line(line, shaper, size) for line in part.lines]


def _all_glyphs(sline):
    return [g for u in sline.units for g in u.glyphs]


def test_unit_count_matches_components(shaper: Shaper) -> None:
    part, lines = _shape("hi world", shaper)
    for line, sline in zip(part.lines, lines):
        assert len(sline.units) == len(line.components)


def test_base_direction_propagated(shaper: Shaper) -> None:
    _, (ltr,) = _shape("hello", shaper)
    _, (rtl,) = _shape(ARAB, shaper)
    assert ltr.base_is_rtl is False
    assert rtl.base_is_rtl is True


def test_ltr_logical_positions_increase(shaper: Shaper) -> None:
    _, (sline,) = _shape("hi", shaper)
    glyphs = _all_glyphs(sline)
    assert [g.logical_position for g in glyphs] == [0, 1]
    assert all(g.is_rtl is False for g in glyphs)


def test_rtl_glyphs_are_visual_order_with_correct_logical_positions(
    shaper: Shaper,
) -> None:
    """Pure Arabic (base RTL): HarfBuzz emits glyphs visual L->R, so
    `logical_position` is non-increasing across the glyph list, yet every
    one still points at a real Arabic source character."""
    part, (sline,) = _shape(ARAB, shaper)
    glyphs = _all_glyphs(sline)
    assert glyphs, "expected at least one glyph"
    assert all(g.is_rtl is True for g in glyphs)
    positions = [g.logical_position for g in glyphs]
    assert all(positions[i] >= positions[i + 1] for i in range(len(positions) - 1))
    for g in glyphs:
        assert part.text[g.logical_position] in ARAB


def test_logical_position_points_into_owning_unit(shaper: Shaper) -> None:
    """Every glyph's `logical_position` indexes a character of the unit it
    came from, across a mixed LTR/RTL line."""
    text = "hi " + ARAB + " world"
    part, lines = _shape(text, shaper)
    for sline in lines:
        for unit in sline.units:
            unit_chars = "".join(lc.character.c for lc in unit.unit.characters)
            for g in unit.glyphs:
                assert part.text[g.logical_position] in unit_chars


def test_glyphs_carry_raster_context(shaper: Shaper) -> None:
    _, (sline,) = _shape("A", shaper)
    (g,) = sline.units[0].glyphs
    assert g.font_path
    assert g.bold is False and g.italic is False
    assert g.x_advance > 0


def test_bold_italic_flagged_on_glyphs(shaper: Shaper) -> None:
    part = partition_text("A")
    sline = shape_line(part.lines[0], shaper, 16, bold=True, italic=True)
    (g,) = sline.units[0].glyphs
    assert g.bold is True and g.italic is True
