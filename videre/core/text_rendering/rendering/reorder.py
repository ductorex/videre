"""UAX#9 rule L2 visual reordering, on the flat model.

`reorder_line(ShapedTextLine) -> GlyphLine` turns one wrapped sub-line (clusters
in logical order, glyphs already visual *within* each cluster thanks to HarfBuzz)
into a flat list of glyphs in full visual (paint) order.

The visual order comes from vibidi (`LineBidi.vibidi_text.reorder`), which runs
the real UAX#9 L2 on the line's true embedding levels -- kept internal to
vibidi. We reorder at the CLUSTER level, not the unit level: a unit is a run of
uniform *parity* but may still mix levels that are not visually contiguous (e.g.
a European number, level 2, glued to a Latin word, level 0, inside RTL text), so
moving whole-unit blocks could not reproduce the correct order. A cluster, by
contrast, maps to one source position and hence one level, so it moves as a
block; glyphs keep HarfBuzz's order inside it.
"""

from __future__ import annotations

from videre.core.text_rendering.glyph_partition import GlyphLine, ShapedTextLine


def reorder_line(line: ShapedTextLine) -> GlyphLine:
    """Flatten `line` into a `GlyphLine` in visual order via vibidi's L2."""
    clusters = line.clusters
    if not clusters:
        return GlyphLine(
            clusters=[],
            source_start=line.source_start,
            source_end=line.source_end,
            terminator=line.terminator,
            base_is_rtl=line.base_is_rtl,
        )
    bidi = line.bidi
    # Reorder whole clusters: a cluster maps to one source position, hence one
    # bidi level, so moving it as a block is correct (unlike a unit, which may
    # mix levels). Clusters carry their ORIGINAL-text position; vibidi indexes
    # the filtered line text, so use `LineBidi`'s inverse mapping to translate,
    # ask vibidi for this sub-line's visual order, and rank each cluster by it.
    # Glyphs keep HarfBuzz order inside their cluster.
    indices = [bidi.orig_to_index[cluster.logical_position] for cluster in clusters]
    visual = bidi.vibidi_text.reorder_retaining_controls(min(indices), max(indices) + 1)
    rank = {pos.logical: pos.visual for pos in visual}
    order = sorted(range(len(clusters)), key=lambda i: rank[indices[i]])
    return GlyphLine(
        clusters=[clusters[i] for i in order],
        source_start=line.source_start,
        source_end=line.source_end,
        terminator=line.terminator,
        base_is_rtl=line.base_is_rtl,
    )
