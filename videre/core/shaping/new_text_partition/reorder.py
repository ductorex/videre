"""UAX#9 rule L2 visual reordering, on the flat model.

`reorder_line(ShapedTextLine) -> GlyphLine` turns one wrapped sub-line (units
in logical order, glyphs already visual *within* each unit thanks to HarfBuzz)
into a flat list of glyphs in full visual (paint) order.

The reorder runs in a SINGLE pass over the units — not the legacy two
granularities (runs-within-word then words) — because the flat model has no
`ShapedWord`/`ShapedRun` nesting. Each unit's direction is turned into a
pseudo bidi level derived from `(is_rtl, base_is_rtl)`; the full UAX#9 levels
are never carried here (see the project's bidi decision). This covers the
2-level cases (pure LTR/RTL, a single opposite-direction run); deeper nesting
is the known, isolated limitation that can be refined in this step alone.
"""

from __future__ import annotations

from videre.core.shaping.new_text_partition.model import (
    GlyphLine,
    PositionedGlyph,
    ShapedTextLine,
)


def reorder_line(line: ShapedTextLine) -> GlyphLine:
    """Flatten `line` into a `GlyphLine` in visual order via UAX#9 L2."""
    base = 1 if line.base_is_rtl else 0
    levels = [_pseudo_level(u.unit.is_rtl, line.base_is_rtl) for u in line.units]
    glyphs: list[PositionedGlyph] = []
    for i in _l2_reorder(levels, base):
        glyphs.extend(line.units[i].glyphs)
    return GlyphLine(glyphs=glyphs)


def _pseudo_level(is_rtl: bool, base_is_rtl: bool) -> int:
    """Map a unit's direction to a 2-level bidi level for the reorder.

    LTR base: LTR unit -> 0, RTL unit -> 1.
    RTL base: RTL unit -> 1, LTR unit -> 2 (one above the base, so an LTR run
    inside an RTL paragraph reads left-to-right while sitting in the reversed
    flow). Gaps carry the base direction, so they get the base level.
    """
    if base_is_rtl:
        return 1 if is_rtl else 2
    return 1 if is_rtl else 0


def _l2_reorder(levels: list[int], base_level: int) -> list[int]:
    """Apply UAX#9 rule L2 to a sequence of items identified by their bidi
    levels. Returns the permutation (source indices in visual order) that
    reorders the items left-to-right.

    L2: from the highest level present down to ``min(base_level | 1,
    lowest_odd_level)``, reverse every maximal sub-sequence whose levels are
    >= that threshold. Levels at or below `base_level` are never reversed. For
    a pure-LTR paragraph with all-zero levels the result is the identity; for a
    single isolated RTL run it is also the identity (reversing one element is a
    no-op); only when several items share a level >= the threshold does the
    order change.
    """
    n = len(levels)
    if n == 0:
        return []
    order = list(range(n))
    highest = max(levels)
    odd_levels = [lv for lv in levels if lv % 2 == 1]
    if not odd_levels:
        return order
    lowest_odd = min(odd_levels)
    floor = max(lowest_odd, base_level | 1)
    for threshold in range(highest, floor - 1, -1):
        i = 0
        while i < n:
            if levels[order[i]] >= threshold:
                j = i
                while j + 1 < n and levels[order[j + 1]] >= threshold:
                    j += 1
                order[i : j + 1] = reversed(order[i : j + 1])
                i = j + 1
            else:
                i += 1
    return order
