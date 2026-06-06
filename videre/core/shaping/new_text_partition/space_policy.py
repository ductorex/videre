"""Apply a `TextSpacePolicy` to shaped lines.

`resolve_space_policy` turns `AUTO` into a concrete `COLLAPSE` / `PRESERVE`
from the wrap mode (AUTO = collapse only when wrapping by word).

`collapse_spaces` is the COLLAPSE pre-pass, run per shaped line BEFORE width
wrapping (so it applies even when there is no wrap): it reduces every inner gap
to a single space and drops the line's leading / trailing gaps. PRESERVE needs
no pre-pass (gaps are kept verbatim); its line-edge handling lives in the wrap.
See `wrap` for the full start / inside / end table per
(width x wrap_words x policy).
"""

from __future__ import annotations

from videre.core.constants import TextSpacePolicy
from videre.core.shaping.new_text_partition.model import ShapedTextLine, ShapedUnit


def resolve_space_policy(
    space_policy: TextSpacePolicy, wrap_words: bool
) -> TextSpacePolicy:
    """Resolve `AUTO` to `COLLAPSE` (wrapping by word) or `PRESERVE` (wrapping by
    char, or no wrap). A concrete policy is returned unchanged."""
    if space_policy is TextSpacePolicy.AUTO:
        return TextSpacePolicy.COLLAPSE if wrap_words else TextSpacePolicy.PRESERVE
    return space_policy


def collapse_spaces(line: ShapedTextLine) -> ShapedTextLine:
    """COLLAPSE pre-pass: reduce every gap to a single space glyph and drop the
    line's leading / trailing gaps. An all-whitespace line collapses to empty.

    Reducing keeps the gap's first glyph (its width = one space); the dropped
    spaces' source positions are absorbed by the neighbouring cluster in the
    caret layer's source tiling (`build_rendered_text`), so selection across a
    collapsed gap still covers them."""
    reduced = [
        ShapedUnit(su.unit, su.glyphs[:1])
        if su.unit.is_gap and len(su.glyphs) > 1
        else su
        for su in line.units
    ]
    lo, hi = 0, len(reduced)
    while lo < hi and reduced[lo].unit.is_gap:
        lo += 1
    while hi > lo and reduced[hi - 1].unit.is_gap:
        hi -= 1
    return ShapedTextLine(units=reduced[lo:hi], bidi=line.bidi)
