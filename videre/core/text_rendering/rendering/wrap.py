"""Width-based wrapping of `ShapedTextLine`s on the flat model.

`wrap_lines(lines, width, wrap_words)` splits each shaped line into sub-lines
that fit within `width` pixels, in logical order (the L2 reorder runs later,
per sub-line).

One unified greedy pass over **atoms** (indivisible glyph chunks) and
consumable **glues** (gaps):

- an atomic unit (Latin/Arabic/... word) -> one atom that never splits;
- a breakable unit (CJK / SE-Asian), and every non-gap unit under
  `wrap_words=False`, -> one atom per cluster, so it may break between clusters;
- a gap -> under word wrap, one consumable glue (a break opportunity whose
  advance is dropped when the line breaks there, kept as spacing otherwise);
  under char wrap, one kept box per space so the gap splits like any cluster.

Word-wrap and cluster-wrap differ only in how units are atomized — same
algorithm. The complete ink envelope (`real_left` / `real_right`) is measured
from the rasterizer's exact bitmap bounds, so negative bearings and terminal
overhangs are both reserved at line edges.
No `ShapedWord` / `source_text` reconstruction: atoms carry their pre-measured
`ShapedCluster`s, so sub-lines rebuild directly (no glyph regrouping).

Gap (whitespace) policy
-----------------------
How a gap (a run of spaces) is treated at the start / inside / end of a line,
per (width x wrap_words x space_policy). See `TextSpacePolicy` for the CSS
mapping. "(n)" = the gap's n spaces kept verbatim.

  width   wrap_words  space_policy  start     inside    end
  ------  ----------  ------------  --------  --------  -------
  absent  char        collapse      1 space   1 space   1 space
  absent  char        preserve      kept(n)   kept(n)   kept(n)
  absent  word        collapse      1 space   1 space   1 space
  absent  word        preserve      kept(n)   kept(n)   kept(n)
  > 0     char        collapse      1 space   1 space   1 space
  > 0     char        preserve      kept[a]   kept(n)   kept[a]
  > 0     word        collapse      hidden    1 space   hidden
  > 0     word        preserve      kept[b]   kept(n)   kept[c]

`width` absent => no wrap => `wrap_words` is irrelevant (the char / word rows
coincide). start / end = edges of the source line when `width` is absent, of
the wrapped sub-line when `width > 0`.
  [a] char + preserve: a gap straddling the break is split character by
      character (part ends one line, part starts the next); total space count
      preserved. e.g. "a      b" wraps to "a   " / "   b".
  [b] word + preserve, start: a gap appears at the start only when it is the
      source line's leading whitespace; an inter-word break gap never moves
      to the head of the next line.
  [c] word + preserve, end: the break gap is KEPT ("hangs") at the line end
      instead of dropped; a gap wider than `width` ends the line whole
      (indivisible under word wrap). The gap's width still counts toward
      fitting (a minor deviation from CSS pre-wrap's true zero-cost hanging).

Edge trimming is exclusive to word wrap: only `> 0 + word + collapse` hides
gaps at line edges. Hidden gaps keep one zero-width source anchor for editing,
but contribute no paint or advance. With char wrap or no wrap an edge space is
kept (it disambiguates a word boundary from a mid-word char break) —
`collapse` merely shrinks runs to one space there. `preserve` never hides a
space.

`space_policy` (resolved upstream: AUTO -> COLLAPSE when wrapping by word, else
PRESERVE) and `wrap_words` select the behaviour:
- run shrinking (n spaces -> 1) is the COLLAPSE pre-pass
  (`space_policy.collapse_spaces`), run before the wrap so it applies even with
  no width; it never trims edges.
- char wrap (`preserve_char` in `_atomize`): every gap becomes kept per-space
  boxes regardless of policy, so gaps split and are never dropped.
- word wrap: a gap is one glue; COLLAPSE hides it at edges / breaks while
  retaining a zero-width source anchor (`_strip_edge_glues` + `_greedy`),
  PRESERVE hangs the break glue on the head.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Iterable, Iterator

from videre.core.constants import TextSpacePolicy
from videre.core.text_rendering.glyph_partition import (
    ShapedCluster,
    ShapedTextLine,
    measure_glyphs,
)


@dataclass(slots=True)
class _Atom:
    """An indivisible run of clusters (a whole atomic unit, or one cluster of a
    breakable one), or a consumable glue (`is_glue`, a gap). `can_break_before`
    marks a legal break opportunity right before this atom (a glue is itself
    always a break opportunity). The atom carries its `ShapedCluster`s straight
    through to `_rebuild` — the cluster flags replace the old `TextUnit` link."""

    clusters: list[ShapedCluster]
    advance: float
    real_left: float
    real_right: float
    is_glue: bool
    can_break_before: bool


def wrap_lines(
    lines: Iterable[ShapedTextLine],
    width: int,
    wrap_words: bool = False,
    space_policy: TextSpacePolicy = TextSpacePolicy.COLLAPSE,
) -> Iterator[ShapedTextLine]:
    """Subdivide each shaped line into sub-lines fitting within `width`.

    `width <= 0` makes no progress, so lines pass through unchanged (avoids an
    infinite loop). Empty lines pass through too. `space_policy` must be already
    resolved (COLLAPSE / PRESERVE — AUTO is resolved upstream); see the module
    docstring for the per-position gap behaviour.
    """
    if width <= 0:
        yield from lines
        return
    for line in lines:
        if not line.clusters:
            yield line
            continue
        yield from _wrap_line(line, width, wrap_words, space_policy)


def _wrap_line(
    line: ShapedTextLine, width: int, wrap_words: bool, space_policy: TextSpacePolicy
) -> Iterator[ShapedTextLine]:
    collapse = space_policy is TextSpacePolicy.COLLAPSE
    # Char wrap keeps gaps as splittable per-space boxes regardless of policy:
    # an edge space there is meaningful (word boundary vs mid-word break), so it
    # is never dropped. Edge trimming (strip / glue-consume) is word-wrap-only —
    # and in char wrap there are no glues, so `_strip_edge_glues` is a no-op.
    atoms = _atomize(line, wrap_words, preserve_char=not wrap_words)
    groups = _greedy(atoms, width, collapse)
    emitted: list[list[_Atom]] = []
    for group in groups:
        if collapse:
            group = _strip_edge_glues(group)
        if group:
            emitted.append(group)
    for index, group in enumerate(emitted):
        yield _rebuild(group, line, keep_terminator=index == len(emitted) - 1)


# ---------------------------------------------------------------------------
# Atomization
# ---------------------------------------------------------------------------


def _atomize(
    line: ShapedTextLine, wrap_words: bool, preserve_char: bool
) -> list[_Atom]:
    """Turn a shaped line into atoms + glues, marking break opportunities.

    A break is legal: at any glue; between clusters of a split unit; and before
    the first cluster of a unit iff a word boundary sits there — i.e. iff that
    unit or its predecessor is breakable/split (two adjacent atomic units with
    no gap are the same word, e.g. a Latin word served by two fonts, and must
    not break).

    A gap is one consumable glue, EXCEPT under `preserve_char` (char + preserve)
    where it is atomized per cluster into kept boxes (each a break opportunity,
    `is_glue=False`) so a gap can split across lines instead of being dropped.

    Consumes the shaper's pre-measured `ShapedCluster`s: a split unit yields one
    atom per cluster, taking geometry straight off the cluster (no re-cluster, no
    per-cluster re-measure). Multi-cluster atoms — a whole atomic unit, or a
    word-wrap gap glue — re-measure their glyphs for the exact ink envelope,
    since composing rounded per-cluster envelopes would not match."""
    atoms: list[_Atom] = []
    prev_was_box = False
    prev_split = False
    for unit_clusters in _by_unit(line.clusters):
        first = unit_clusters[0]
        if first.is_gap:
            if preserve_char:
                for c in unit_clusters:
                    atoms.append(
                        _Atom([c], c.advance, c.ink_left, c.ink_right, False, True)
                    )
                prev_was_box = True
                prev_split = True
            else:
                measure = measure_glyphs([g for c in unit_clusters for g in c.glyphs])
                atoms.append(
                    _Atom(
                        list(unit_clusters),
                        measure.advance,
                        measure.left,
                        measure.right,
                        True,
                        True,
                    )
                )
                prev_was_box = False
                prev_split = False
            continue
        split = first.unit_breakable or not wrap_words
        if split:
            for k, c in enumerate(unit_clusters):
                atoms.append(
                    _Atom(
                        [c],
                        c.advance,
                        c.ink_left,
                        c.ink_right,
                        False,
                        _cluster_break_before(c, k, prev_was_box, prev_split, split),
                    )
                )
                prev_was_box = True
        else:
            measure = measure_glyphs([g for c in unit_clusters for g in c.glyphs])
            atoms.append(
                _Atom(
                    list(unit_clusters),
                    measure.advance,
                    measure.left,
                    measure.right,
                    False,
                    _cluster_break_before(first, 0, prev_was_box, prev_split, split),
                )
            )
            prev_was_box = True
        prev_split = split
    return atoms


def _by_unit(clusters: list[ShapedCluster]) -> list[list[ShapedCluster]]:
    """Group a flat cluster list back into its source `TextUnit`s via
    `starts_unit` (set on each unit's first cluster). The wrap needs the
    per-unit grouping to mark break opportunities and to keep an atomic unit or
    a gap whole."""
    groups: list[list[ShapedCluster]] = []
    for cluster in clusters:
        if cluster.starts_unit or not groups:
            groups.append([cluster])
        else:
            groups[-1].append(cluster)
    return groups


def _cluster_break_before(
    c: ShapedCluster, k: int, prev_was_box: bool, prev_split: bool, split: bool
) -> bool:
    """`can_break_before` for cluster `k` of its unit — the break logic that
    lived inline in the old `_atomize`, reading the cluster's intrinsic flags
    and combining them with the wrap context."""
    if k > 0:
        cbb = True  # between clusters of a split unit
    elif not prev_was_box:
        # At line start this value is irrelevant. Right after a glue, the glue
        # itself owns the break opportunity.
        cbb = c.unit_can_break_before
    else:
        cbb = c.unit_can_break_before or split or prev_split  # word boundary
    if c.no_break_before:
        cbb = False
    return cbb


# ---------------------------------------------------------------------------
# Greedy line filling
# ---------------------------------------------------------------------------


def _greedy(atoms: list[_Atom], width: int, collapse: bool) -> list[list[_Atom]]:
    """Greedy line breaking. Accumulate atoms; on overflow, break at the last
    break opportunity inside the line, else right before the offending atom if
    it allows it, else keep going (the atom is glued to the current run and must
    overflow).

    A gap (glue) at a break is dropped under `collapse` (consumed) and kept
    ("hung" on the head line) under preserve."""
    queue = deque(atoms)
    lines: list[list[_Atom]] = []
    current: list[_Atom] = []
    cur_adv = 0.0
    cur_left = 0.0
    cur_right = 0.0
    last_break: int | None = None  # index in `current` to break before
    while queue:
        atom = queue[0]
        trial_left = min(cur_left, cur_adv + atom.real_left)
        trial_right = max(cur_right, cur_adv + atom.real_right)
        if not current or trial_right - trial_left <= width:
            if current and atom.can_break_before:
                last_break = len(current)
            current.append(atom)
            cur_adv += atom.advance
            cur_left = trial_left
            cur_right = trial_right
            queue.popleft()
            continue
        # Overflow, current non-empty.
        if atom.is_glue:
            # An overflowing glue (inter-word space) ends the line. collapse:
            # consume it (a trailing space never pushes the preceding word to
            # the next line), but retain a zero-width source anchor. preserve:
            # hang it on the line end (kept).
            if collapse:
                current.append(_source_anchor(atom))
            else:
                current.append(atom)
            lines.append(current)
            current, cur_adv, cur_left, cur_right, last_break = (
                [],
                0.0,
                0.0,
                0.0,
                None,
            )
            queue.popleft()
            continue
        if atom.can_break_before:
            # The overflowing atom is itself a legal break point, so break right
            # before it: `current` already fits by construction, so this keeps
            # every atom that fits (maximal greedy). This is preferred over an
            # earlier `last_break` — backing up there would needlessly drop a
            # fitting atom. That is the char-wrap off-by-one: there every atom is
            # a break opportunity, so `last_break` trails one atom behind the
            # fill front and would push a character that fits onto the next line.
            # A trailing glue left in `current` is dropped (collapse, by
            # `_strip_edge_glues`) or hung (preserve), exactly as via last_break.
            lines.append(current)
            current, cur_adv, cur_left, cur_right, last_break = (
                [],
                0.0,
                0.0,
                0.0,
                None,
            )
        elif last_break is not None:
            brk = current[last_break]
            if brk.is_glue and not collapse:
                head = current[: last_break + 1]  # preserve: hang it on the head
                tail = current[last_break + 1 :]
            elif brk.is_glue:
                # The gap has no painted width, but remains one selectable
                # source item attached to the preceding display line.
                head = [*current[:last_break], _source_anchor(brk)]
                tail = current[last_break + 1 :]
            else:
                head = current[:last_break]
                tail = current[last_break:]
            lines.append(head)
            # Push `tail` back to the front for the next line. `extendleft` adds
            # items one by one (reversing them), so feed `reversed(tail)` to land
            # them in original order — equivalent to the old `tail + queue`, O(len
            # tail) instead of O(len queue).
            queue.extendleft(reversed(tail))
            current, cur_adv, cur_left, cur_right, last_break = (
                [],
                0.0,
                0.0,
                0.0,
                None,
            )
        else:
            # Glued to the current run with no legal break: overflow it whole.
            current.append(atom)
            cur_adv += atom.advance
            cur_left = trial_left
            cur_right = trial_right
            queue.popleft()
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Reconstruction
# ---------------------------------------------------------------------------


def _strip_edge_glues(group: list[_Atom]) -> list[_Atom]:
    """Hide leading / trailing glues without dropping their source ranges.

    Each trimmed gap becomes a zero-width, non-painted anchor. This preserves a
    display line for all-whitespace input and lets caret / selection map the
    collapsed visual item back to every source space. Inter-word glues in the
    middle stay painted normally.
    """
    lo, hi = 0, len(group)
    while lo < hi and group[lo].is_glue:
        lo += 1
    while hi > lo and group[hi - 1].is_glue:
        hi -= 1
    if lo == hi:
        return [_source_anchor(atom) for atom in group]
    return [
        *(_source_anchor(atom) for atom in group[:lo]),
        *group[lo:hi],
        *(_source_anchor(atom) for atom in group[hi:]),
    ]


def _source_anchor(atom: _Atom) -> _Atom:
    """Turn a shaped gap into one invisible zero-width source item."""
    if not atom.clusters:
        return atom
    source_start = min(c.logical_position for c in atom.clusters)
    source_end = max(c.source_end for c in atom.clusters)
    first = atom.clusters[0]
    glyph = replace(
        first.glyphs[0],
        x_advance=0.0,
        x_offset=0.0,
        y_offset=0.0,
        ink_left=0.0,
        ink_right=0.0,
        is_gap=False,
        logical_position=source_start,
        source_end=source_end,
        paint=False,
    )
    anchor = ShapedCluster(
        glyphs=(glyph,),
        advance=0.0,
        ink_left=0.0,
        ink_right=0.0,
        logical_position=source_start,
        source_end=source_end,
        is_rtl=first.is_rtl,
        is_gap=True,
        paint=False,
        starts_unit=first.starts_unit,
        unit_breakable=first.unit_breakable,
        unit_can_break_before=first.unit_can_break_before,
        no_break_before=first.no_break_before,
    )
    return _Atom(
        clusters=[anchor],
        advance=0.0,
        real_left=0.0,
        real_right=0.0,
        is_glue=False,
        can_break_before=False,
    )


def _rebuild(
    group: list[_Atom], line: ShapedTextLine, *, keep_terminator: bool
) -> ShapedTextLine:
    """Collect the group's clusters into a wrapped sub-line. No `ShapedUnit`
    re-glue: the cluster is the carried unit, so a breakable unit split across
    sub-lines just lands its clusters on each. `bidi` rides along so the reorder
    can call `vibidi_text.reorder`."""
    clusters = [cluster for atom in group for cluster in atom.clusters]
    source_start = min((c.logical_position for c in clusters), default=0)
    source_end = max((c.source_end for c in clusters), default=source_start)
    return ShapedTextLine(
        clusters=clusters,
        bidi=line.bidi,
        source_start=source_start,
        source_end=source_end,
        terminator=line.terminator if keep_terminator else None,
    )
