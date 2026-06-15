"""Apply a `TextSpacePolicy` to shaped lines.

`resolve_space_policy` turns `AUTO` into a concrete `COLLAPSE` / `PRESERVE`
from the wrap mode (AUTO = collapse only when wrapping by word).

`collapse_spaces` is the COLLAPSE pre-pass, run per shaped line BEFORE width
wrapping (so it applies even when there is no wrap): it shrinks every gap run to
a single space (n -> 1). It does NOT trim edges — dropping a gap at a line edge
is word-wrap-only (it lives in the wrap), since under char wrap / no wrap an edge
space is meaningful. PRESERVE needs no pre-pass (gaps are kept verbatim). See
`wrap` for the full start / inside / end table per (width x wrap_words x policy).
"""

from __future__ import annotations

from dataclasses import replace

from videre.core.constants import TextSpacePolicy
from videre.core.shaping.glyph_partition import (
    ShapedCluster,
    ShapedTextLine,
    measure_glyphs,
)


def resolve_space_policy(
    space_policy: TextSpacePolicy, wrap_words: bool
) -> TextSpacePolicy:
    """Resolve `AUTO` to `COLLAPSE` (wrapping by word) or `PRESERVE` (wrapping by
    char, or no wrap). A concrete policy is returned unchanged."""
    if space_policy is TextSpacePolicy.AUTO:
        return TextSpacePolicy.COLLAPSE if wrap_words else TextSpacePolicy.PRESERVE
    return space_policy


def collapse_spaces(line: ShapedTextLine) -> ShapedTextLine:
    """COLLAPSE pre-pass: shrink every gap run to a single space glyph (n -> 1).

    Edges are NOT trimmed here: dropping a gap at a line edge is exclusively a
    word-wrap behaviour (`wrap._strip_edge_glues` / the greedy), since with no
    wrap or char wrap an edge space is meaningful (it disambiguates a word
    boundary from a mid-word char break). So this only shrinks runs; every gap
    stays, shown as one space.

    Reducing keeps the gap's first glyph (its width = one space); the dropped
    spaces' source positions are folded into the retained glyph's explicit
    source range, so selection across a collapsed gap still covers them."""
    reduced: list[ShapedCluster] = []
    clusters = line.clusters
    n = len(clusters)
    i = 0
    while i < n:
        c = clusters[i]
        if not c.is_gap:
            reduced.append(c)
            i += 1
            continue
        # One gap unit = a run of gap clusters; only its first has `starts_unit`.
        j = i + 1
        while j < n and clusters[j].is_gap and not clusters[j].starts_unit:
            j += 1
        run = clusters[i:j]
        if len(run) > 1:
            glyph = replace(run[0].glyphs[0], source_end=run[-1].source_end)
            measure = measure_glyphs([glyph])
            reduced.append(
                replace(
                    run[0],
                    glyphs=(glyph,),
                    advance=measure.advance,
                    ink_left=measure.left,
                    ink_right=measure.right,
                    source_end=run[-1].source_end,
                )
            )
        else:
            reduced.append(c)
        i = j
    return ShapedTextLine(
        clusters=reduced,
        bidi=line.bidi,
        source_start=line.source_start,
        source_end=line.source_end,
        terminator=line.terminator,
    )
