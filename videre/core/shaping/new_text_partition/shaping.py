"""Shape a partition `Line` into glyphs via HarfBuzz, keeping the unit link.

Produces a `ShapedTextLine`: the line's `TextUnit`s in logical order, each
carrying its `PositionedGlyph`s. Within a unit the glyphs are in HarfBuzz
output order (visual left-to-right, so reversed vs logical for an RTL unit);
the units themselves stay in logical order until the L2 reorder (after wrap).

`logical_position` is read straight off the unit's `LogicalCharacter`s via the
HarfBuzz cluster index, so it is correct in both reading directions: for an
RTL unit the clusters decrease but each one still points at the right source
character. Several glyphs sharing a cluster (decomposition) get the same
position; a ligature glyph takes its cluster's first character's position.
"""

from __future__ import annotations

from videre.core.shaping.new_text_partition.model import (
    Line,
    PositionedGlyph,
    ShapedTextLine,
    ShapedUnit,
    TextUnit,
)
from videre.core.shaping.shaper import Shaper


def shape_line(
    line: Line,
    shaper: Shaper,
    size_px: int,
    *,
    bold: bool = False,
    italic: bool = False,
) -> ShapedTextLine:
    """Shape every component of `line` (gaps included) into a `ShapedTextLine`."""
    units = [
        _shape_unit(unit, shaper, size_px, bold=bold, italic=italic)
        for unit in line.components
    ]
    return ShapedTextLine(units=units, base_is_rtl=line.base_is_rtl)


def _shape_unit(
    unit: TextUnit, shaper: Shaper, size_px: int, *, bold: bool, italic: bool
) -> ShapedUnit:
    text = "".join(lc.character.c for lc in unit.characters)
    shaped = shaper.shape(
        text=text,
        font_path=unit.font_path,
        size_px=size_px,
        script=unit.script,
        right_to_left=unit.is_rtl,
        bold=bold,
        italic=italic,
    )
    glyphs = [
        PositionedGlyph(
            glyph_id=g.glyph_id,
            x_advance=g.x_advance,
            x_offset=g.x_offset,
            y_offset=g.y_offset,
            ink_left=g.ink_left,
            ink_right=g.ink_right,
            font_path=unit.font_path,
            bold=bold,
            italic=italic,
            is_rtl=unit.is_rtl,
            is_gap=unit.is_gap,
            logical_position=unit.characters[g.cluster].logical_position,
        )
        for g in shaped
    ]
    return ShapedUnit(unit=unit, glyphs=glyphs)
