"""UAX#9 rule L2 visual reordering, on the flat model.

`reorder_line(ShapedTextLine) -> GlyphLine` turns one wrapped sub-line (units
in logical order, glyphs already visual *within* each unit thanks to HarfBuzz)
into a flat list of glyphs in full visual (paint) order.

The visual order comes from vibidi (`LineBidi.vibidi_text.reorder`), which runs
the real UAX#9 L2 on the line's true embedding levels -- kept internal to
vibidi. We reorder at the GLYPH level, not the unit level: a unit is a run of
uniform *parity* but may still mix levels that are not visually contiguous (e.g.
a European number, level 2, glued to a Latin word, level 0, inside RTL text), so
moving whole-unit blocks could not reproduce the correct order. Instead each
glyph is ranked by the visual position of its source character; a stable sort
keeps HarfBuzz's intra-cluster order for glyphs that share a position.
"""

from __future__ import annotations

from videre.core.shaping.glyph_partition import GlyphLine, ShapedTextLine


def reorder_line(line: ShapedTextLine) -> GlyphLine:
    """Flatten `line` into a `GlyphLine` in visual order via vibidi's L2."""
    glyphs = [g for unit in line.units for g in unit.glyphs]
    if not glyphs:
        return GlyphLine(
            glyphs=[],
            edit_units=line.edit_units,
            source_start=line.source_start,
            source_end=line.source_end,
            terminator=line.terminator,
            base_is_rtl=line.base_is_rtl,
        )
    bidi = line.bidi
    # Glyphs carry their ORIGINAL-text position; vibidi indexes the filtered line
    # text. Invert `positions` to translate, then ask vibidi for the visual order
    # of this sub-line's interval and rank each glyph by it.
    orig_to_index = {orig: i for i, orig in enumerate(bidi.positions)}
    indices = [orig_to_index[g.logical_position] for g in glyphs]
    visual = bidi.vibidi_text.reorder_retaining_controls(min(indices), max(indices) + 1)
    rank = {pos.logical: pos.visual for pos in visual}
    order = sorted(range(len(glyphs)), key=lambda i: rank[indices[i]])
    return GlyphLine(
        glyphs=[glyphs[i] for i in order],
        edit_units=line.edit_units,
        source_start=line.source_start,
        source_end=line.source_end,
        terminator=line.terminator,
        base_is_rtl=line.base_is_rtl,
    )
