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
algorithm. `real_right` (ink overhang past the advance) is measured exactly as
the legacy wrap, so italics / `f` / `T` at a line edge are never clipped.
No `ShapedWord` / `source_text` reconstruction: atoms carry their glyphs and
point back at their `TextUnit`, so sub-lines rebuild directly.

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
  > 0     word        collapse      dropped   1 space   dropped
  > 0     word        preserve      kept[b]   kept(n)   kept[c]

`width` absent => no wrap => `wrap_words` is irrelevant (the char / word rows
coincide). start / end = edges of the logical line when `width` is absent, of
the wrapped sub-line when `width > 0`.
  [a] char + preserve: a gap straddling the break is split character by
      character (part ends one line, part starts the next); total space count
      preserved. e.g. "a      b" wraps to "a   " / "   b".
  [b] word + preserve, start: a gap appears at the start only when it is the
      logical line's leading whitespace; an inter-word break gap never moves
      to the head of the next line.
  [c] word + preserve, end: the break gap is KEPT ("hangs") at the line end
      instead of dropped; a gap wider than `width` ends the line whole
      (indivisible under word wrap). The gap's width still counts toward
      fitting (a minor deviation from CSS pre-wrap's true zero-cost hanging).

Edge trimming (drop) is exclusive to word wrap: only `> 0 + word + collapse`
drops gaps at line edges. With char wrap or no wrap an edge space is kept (it
disambiguates a word boundary from a mid-word char break) — `collapse` merely
shrinks runs to one space there. `preserve` never drops a space anywhere.

`space_policy` (resolved upstream: AUTO -> COLLAPSE when wrapping by word, else
PRESERVE) and `wrap_words` select the behaviour:
- run shrinking (n spaces -> 1) is the COLLAPSE pre-pass
  (`space_policy.collapse_spaces`), run before the wrap so it applies even with
  no width; it never trims edges.
- char wrap (`preserve_char` in `_atomize`): every gap becomes kept per-space
  boxes regardless of policy, so gaps split and are never dropped.
- word wrap: a gap is one glue; COLLAPSE drops it at edges / breaks
  (`_strip_edge_glues` + `_greedy`), PRESERVE hangs the break glue on the head.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from videre.core.constants import TextSpacePolicy
from videre.core.shaping.glyph_partition import (
    PositionedGlyph,
    ShapedTextLine,
    ShapedUnit,
)
from videre.core.shaping.text_partition.model import LineBidi, TextUnit


@dataclass(slots=True)
class _Atom:
    """An indivisible run of glyphs (a whole atomic unit, or one cluster of a
    breakable one), or a consumable glue (`is_glue`, a gap). `unit` is the
    source `TextUnit` (identity used to regroup atoms into `ShapedUnit`s).
    `can_break_before` marks a legal break opportunity right before this atom
    (a glue is itself always a break opportunity)."""

    unit: TextUnit
    glyphs: list[PositionedGlyph]
    advance: float
    real_right: float
    is_glue: bool
    can_break_before: bool


def wrap_lines(
    lines: Iterable[ShapedTextLine],
    width: int,
    wrap_words: bool = True,
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
        if not line.units:
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
    for group in _greedy(atoms, width, collapse):
        if collapse:
            group = _strip_edge_glues(group)
        if group:
            yield _rebuild(group, line.bidi)


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
    where it is atomized per character into kept boxes (each a break
    opportunity, `is_glue=False`) so a gap can split across lines instead of
    being dropped."""
    atoms: list[_Atom] = []
    prev_was_box = False
    prev_split = False
    for su in line.units:
        unit = su.unit
        if not su.glyphs:
            continue
        if unit.is_gap:
            if preserve_char:
                for chunk in _clusters(su.glyphs):
                    adv, rr = _measure(chunk)
                    atoms.append(_Atom(unit, chunk, adv, rr, False, True))
                prev_was_box = True
                prev_split = True
            else:
                adv, rr = _measure(su.glyphs)
                atoms.append(_Atom(unit, su.glyphs, adv, rr, True, True))
                prev_was_box = False
                prev_split = False
            continue
        split = unit.is_breakable or not wrap_words
        chunks = _clusters(su.glyphs) if split else [su.glyphs]
        for k, chunk in enumerate(chunks):
            if k > 0:
                cbb = True
            elif not prev_was_box:
                cbb = False  # line start, or right after a glue (the glue breaks)
            else:
                cbb = split or prev_split  # word boundary between adjacent units
            adv, rr = _measure(chunk)
            atoms.append(_Atom(unit, chunk, adv, rr, False, cbb))
            prev_was_box = True
        prev_split = split
    return atoms


def _clusters(glyphs: list[PositionedGlyph]) -> list[list[PositionedGlyph]]:
    """Group consecutive glyphs sharing one `logical_position` (= one HarfBuzz
    cluster: a base plus its marks, or a ligature). Breaking inside a cluster
    would corrupt the rendering, so these are the smallest splittable chunks.
    Works for RTL too (positions decrease, but equal ones stay adjacent)."""
    out: list[list[PositionedGlyph]] = []
    i = 0
    n = len(glyphs)
    while i < n:
        j = i + 1
        lp = glyphs[i].logical_position
        while j < n and glyphs[j].logical_position == lp:
            j += 1
        out.append(glyphs[i:j])
        i = j
    return out


def _measure(glyphs: list[PositionedGlyph]) -> tuple[float, float]:
    """Return `(advance, real_right)` for a chunk, mirroring the legacy wrap:
    `advance` is the cumulative `x_advance`; `real_right` is the rightmost ink
    edge from the chunk's left, using the same `int(round(...))` rounding as
    the rasterizer so wrap and paint agree on whether a glyph fits."""
    pen = 0.0
    real_right = 0.0
    for g in glyphs:
        draw_x = int(round(pen + g.x_offset + g.ink_left))
        ink_width = g.ink_right - g.ink_left
        real_right = max(real_right, draw_x + ink_width)
        pen += g.x_advance
    return pen, max(real_right, pen)


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
    queue = list(atoms)
    lines: list[list[_Atom]] = []
    current: list[_Atom] = []
    cur_adv = 0.0
    cur_rr = 0.0
    last_break: int | None = None  # index in `current` to break before
    while queue:
        atom = queue[0]
        trial_rr = max(cur_rr, cur_adv + atom.real_right)
        if not current or trial_rr <= width:
            if current and atom.can_break_before:
                last_break = len(current)
            current.append(atom)
            cur_adv += atom.advance
            cur_rr = trial_rr
            queue.pop(0)
            continue
        # Overflow, current non-empty.
        if atom.is_glue:
            # An overflowing glue (inter-word space) ends the line. collapse:
            # consume it (a trailing space never pushes the preceding word to
            # the next line). preserve: hang it on the line end (kept).
            if not collapse:
                current.append(atom)
            lines.append(current)
            current, cur_adv, cur_rr, last_break = [], 0.0, 0.0, None
            queue.pop(0)
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
            current, cur_adv, cur_rr, last_break = [], 0.0, 0.0, None
        elif last_break is not None:
            brk = current[last_break]
            if brk.is_glue and not collapse:
                head = current[: last_break + 1]  # preserve: hang it on the head
                tail = current[last_break + 1 :]
            elif brk.is_glue:
                head = current[:last_break]  # collapse: drop the break glue
                tail = current[last_break + 1 :]
            else:
                head = current[:last_break]
                tail = current[last_break:]
            lines.append(head)
            queue = tail + queue
            current, cur_adv, cur_rr, last_break = [], 0.0, 0.0, None
        else:
            # Glued to the current run with no legal break: overflow it whole.
            current.append(atom)
            cur_adv += atom.advance
            cur_rr = trial_rr
            queue.pop(0)
    if current:
        lines.append(current)
    return lines


# ---------------------------------------------------------------------------
# Reconstruction
# ---------------------------------------------------------------------------


def _strip_edge_glues(group: list[_Atom]) -> list[_Atom]:
    """Drop leading / trailing glues of a sub-line: an inter-word space that
    lands at a line edge after wrapping is not rendered (matches the legacy
    drop of leading/trailing whitespace, and CSS line-edge trimming).
    Inter-word glues in the middle stay."""
    lo, hi = 0, len(group)
    while lo < hi and group[lo].is_glue:
        lo += 1
    while hi > lo and group[hi - 1].is_glue:
        hi -= 1
    return group[lo:hi]


def _rebuild(group: list[_Atom], bidi: LineBidi) -> ShapedTextLine:
    """Regroup consecutive atoms of the same `TextUnit` back into `ShapedUnit`s.
    A breakable unit split across sub-lines yields one `ShapedUnit` per
    sub-line, each holding its slice of glyphs. `bidi` is the line's context,
    carried through so the reorder can call `vibidi_text.reorder`."""
    units: list[ShapedUnit] = []
    cur_unit: TextUnit | None = None
    cur_glyphs: list[PositionedGlyph] = []
    for atom in group:
        if atom.unit is not cur_unit:
            if cur_unit is not None:
                units.append(ShapedUnit(cur_unit, cur_glyphs))
            cur_unit = atom.unit
            cur_glyphs = list(atom.glyphs)
        else:
            cur_glyphs.extend(atom.glyphs)
    if cur_unit is not None:
        units.append(ShapedUnit(cur_unit, cur_glyphs))
    return ShapedTextLine(units=units, bidi=bidi)
