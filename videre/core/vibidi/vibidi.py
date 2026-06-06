"""Pure-Python Unicode Bidirectional Algorithm (UAX#9): https://www.unicode.org/reports/tr9/

Resolves the embedding level of every character and reorders a display line
into visual order. It exists to provide the one rule python-bidi's pure-Python
path omits -- **N0**, paired brackets -- which is what makes mirrored brackets
(``[`` / ``]``) render correctly inside RTL text.

Two entry points, matching the only two places videre needs bidi:

* ``vibidi(text) -> VibidiText``: run once per paragraph. Each ``LogicalPosition``
  exposes ``is_rtl`` (the resolved direction), handed to HarfBuzz at segmentation
  time so it shapes -- and mirrors -- each run correctly.
* ``VibidiText.reorder(start, end)``: run per *display* line after wrapping, to
  put one wrapped interval in visual order (rule L2).

Scope / simplifications, all deliberate:

* **Flat text.** Explicit formatting characters (embeddings / overrides /
  isolates, phases X1-X10) are assumed already stripped -- videre removes them
  upstream -- so every character starts at the paragraph level and the
  level-resolution phases (W, N, I) run over the whole text as a single run.
  Re-adding X1-X10 would be a layer *in front of* this core, leaving W/N/I/L2
  untouched.
* **No L1.** L1 only resets trailing whitespace / separators to the base level,
  i.e. it repositions invisible blanks at a line end -- videre already handles
  that when it consumes wrap gaps. ``reorder`` therefore applies L2 uniformly,
  with no special-casing of spaces. The embedding *levels* stay internal
  (``_level``); nothing outside this module needs them.
"""

import functools
import unicodedata
from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True, slots=True)
class LogicalPosition:
    is_rtl: bool
    logical: int


@dataclass(frozen=True, slots=True)
class LevelPosition(LogicalPosition):
    _level: int


@dataclass(frozen=True, slots=True)
class VisualPosition(LogicalPosition):
    visual: int


class RtlPolicy(StrEnum):
    LEFT_TO_RIGHT = auto()
    RIGHT_TO_LEFT = auto()
    INFER = auto()


@dataclass(frozen=True, slots=True)
class VibidiText:
    logical_positions: tuple[LevelPosition, ...]
    base_is_rtl: bool

    def reorder(self, logical_start: int, logical_end: int) -> Sequence[VisualPosition]:
        """
        Reorder text[logical_start:logical_end], i.e. interval [logical_start; logical_end).

        If text associated to this context is wrapped, we may need to compute local reorders,
        which still needs full text context, hence why this method is here.

        Return a sequence of VisualPosition objects, in **visual order**, matching given interval.
        Position in returned sequence match `visual` field for each position object. Not a problem,
        since this information can be used later to match visual to logical position, without
        having to rely on sequence indexes.
        """
        window = self.logical_positions[logical_start:logical_end]
        levels = [p._level for p in window]
        base_level = 1 if self.base_is_rtl else 0
        order = _l2_order(levels, base_level)
        return [
            VisualPosition(
                is_rtl=window[src].is_rtl, logical=window[src].logical, visual=visual
            )
            for visual, src in enumerate(order)
        ]


def vibidi(logical_text: str, rtl_policy: RtlPolicy = RtlPolicy.INFER) -> VibidiText:
    """
    Run the bidirectional algorithm on given text.

    Arguments:
        logical_text (str):
            Python text, containing characters in logical (reading) order.
        rtl_policy (RtlPolicy):
            RTL policy for given text. If "INFER", vibidi infers the base direction
            from the first strong character (UAX#9 P2/P3).
    Return:
        VibidiText
            VibidiText object containing all information required
            to display text visually and match visual to logical positions.
    """
    original = [unicodedata.bidirectional(c) or _default_class(c) for c in logical_text]
    base_level = _base_level(original, rtl_policy)
    types = _resolve_weak(original, base_level)  # W1-W7
    _resolve_brackets(logical_text, original, types, base_level)  # N0 (in place)
    types = _resolve_neutral(types, base_level)  # N1, N2
    levels = _resolve_implicit(types, base_level)  # I1, I2
    positions = tuple(
        LevelPosition(is_rtl=bool(level & 1), logical=i, _level=level)
        for i, level in enumerate(levels)
    )
    return VibidiText(positions, bool(base_level & 1))


# --- implementation details -------------------------------------------------
#
# Every helper traffics in UAX#9 bidi class strings ("L", "R", "AL", "EN", "AN",
# "WS", "ON", ...) as returned by `unicodedata.bidirectional`. The text being
# flat (single run at the base level), `sos` and `eos` -- the directions that
# bound the run -- are both the base direction.


def _default_class(c: str) -> str:
    """Bidi class for a codepoint `unicodedata` doesn't know (unassigned).

    Implements the UAX#9 default ranges: unassigned codepoints in the Hebrew /
    RTL blocks default to R, those in the Arabic blocks to AL, currency symbols
    to ET, everything else to L. Assigned characters never reach here.
    """
    cp = ord(c)
    if (
        0x0590 <= cp <= 0x05FF
        or 0x07C0 <= cp <= 0x085F
        or 0xFB1D <= cp <= 0xFB4F
        or 0x10800 <= cp <= 0x10CFF
        or 0x1E800 <= cp <= 0x1EFFF
    ):
        return "R"
    if (
        0x0600 <= cp <= 0x07BF
        or 0x0860 <= cp <= 0x08FF
        or 0xFB50 <= cp <= 0xFDCF
        or 0xFDF0 <= cp <= 0xFDFF
        or 0xFE70 <= cp <= 0xFEFF
        or 0x1EC70 <= cp <= 0x1ECBF
        or 0x1ED00 <= cp <= 0x1ED4F
        or 0x1EE00 <= cp <= 0x1EEFF
    ):
        return "AL"
    if 0x20A0 <= cp <= 0x20CF:
        return "ET"
    return "L"


def _base_level(types: list[str], policy: RtlPolicy) -> int:
    """Paragraph embedding level (UAX#9 P2/P3), or forced by `policy`."""
    if policy == RtlPolicy.LEFT_TO_RIGHT:
        return 0
    if policy == RtlPolicy.RIGHT_TO_LEFT:
        return 1
    for t in types:  # P2: first strong character; P3: default to LTR
        if t == "L":
            return 0
        if t in ("R", "AL"):
            return 1
    return 0


def _resolve_weak(original: list[str], base_level: int) -> list[str]:
    """Phases W1-W7: resolve NSM, numbers and number separators, in order."""
    sos = "R" if base_level & 1 else "L"
    t = list(original)
    n = len(t)

    # W1: each NSM takes the type of the previous character (sos at the start).
    prev = sos
    for i in range(n):
        if t[i] == "NSM":
            t[i] = prev
        prev = t[i]

    # W2: EN becomes AN when the last strong type seen is AL.
    strong = sos
    for i in range(n):
        if t[i] in ("R", "L", "AL"):
            strong = t[i]
        elif t[i] == "EN" and strong == "AL":
            t[i] = "AN"

    # W3: AL becomes R.
    for i in range(n):
        if t[i] == "AL":
            t[i] = "R"

    # W4: a lone ES between two EN, or a lone CS between two numbers of the same
    # type, takes that number type.
    for i in range(1, n - 1):
        if t[i] == "ES" and t[i - 1] == "EN" and t[i + 1] == "EN":
            t[i] = "EN"
        elif t[i] == "CS" and t[i - 1] == t[i + 1] and t[i - 1] in ("EN", "AN"):
            t[i] = t[i - 1]

    # W5: a run of ET adjacent to an EN becomes EN.
    i = 0
    while i < n:
        if t[i] == "ET":
            j = i
            while j < n and t[j] == "ET":
                j += 1
            before = t[i - 1] if i > 0 else sos
            after = t[j] if j < n else sos
            if before == "EN" or after == "EN":
                for k in range(i, j):
                    t[k] = "EN"
            i = j
        else:
            i += 1

    # W6: any remaining ET, ES, CS becomes ON.
    for i in range(n):
        if t[i] in ("ET", "ES", "CS"):
            t[i] = "ON"

    # W7: EN becomes L when the last strong type seen is L.
    strong = sos
    for i in range(n):
        if t[i] in ("R", "L"):
            strong = t[i]
        elif t[i] == "EN" and strong == "L":
            t[i] = "L"

    return t


def _resolve_brackets(
    text: str, original: list[str], types: list[str], base_level: int
) -> None:
    """Phase N0: resolve each pair of matched brackets to a single direction.

    Mutates `types` in place. This is the rule python-bidi's pure-Python path
    skips, and the reason a ``[`` framing a latin island in RTL text was being
    mirrored to ``]``: a correctly resolved bracket keeps both sides consistent.
    `original` carries the pre-W1 classes, needed only for the NSM clause below.
    """
    e = "R" if base_level & 1 else "L"  # embedding direction
    o = "L" if e == "R" else "R"  # opposite direction
    for open_i, close_i in _bracket_pairs(text, types):
        inside = {_n0_strong(types[k]) for k in range(open_i + 1, close_i)}
        if e in inside:  # N0.b: a strong matching the embedding direction
            direction = e
        elif o in inside:  # N0.c: only the opposite strong direction inside
            prev = _prev_strong(types, open_i, base_level)
            direction = o if prev == o else e  # c.1 / c.2
        else:  # N0.d: no strong type inside -> leave the brackets as ON
            continue
        for bracket in (open_i, close_i):
            types[bracket] = direction
            # N0: NSM that originally followed a now-resolved bracket match it.
            k = bracket + 1
            while k < len(original) and original[k] == "NSM":
                types[k] = direction
                k += 1


def _bracket_pairs(text: str, types: list[str]) -> list[tuple[int, int]]:
    """Identify matched bracket pairs (UAX#9 BD16), returned sorted by opening.

    Only characters still typed ON are considered (resolved brackets aren't
    re-paired). Uses the 63-deep stack the spec mandates; canonical equivalence
    covers the angle-bracket aliases U+2329 / U+232A.
    """
    open_to_close, close_set, canon = _bracket_tables()
    stack: list[tuple[str, int]] = []  # (expected closing char, opening index)
    pairs: list[tuple[int, int]] = []
    for i, ch in enumerate(text):
        if types[i] != "ON":
            continue
        closing = open_to_close.get(ch)
        if closing is not None:  # opening bracket
            if len(stack) >= 63:  # BD16: no room left -> stop pairing entirely
                break
            stack.append((closing, i))
        elif ch in close_set:  # closing bracket
            wanted = canon.get(ch, ch)
            for k in range(len(stack) - 1, -1, -1):
                if canon.get(stack[k][0], stack[k][0]) == wanted:
                    pairs.append((stack[k][1], i))
                    del stack[k:]
                    break
    pairs.sort()
    return pairs


def _resolve_neutral(types: list[str], base_level: int) -> list[str]:
    """Phases N1-N2: resolve runs of neutral / isolate-formatting characters."""
    e = "R" if base_level & 1 else "L"
    sos = e
    t = list(types)
    n = len(t)
    neutral = {"B", "S", "WS", "ON"}
    i = 0
    while i < n:
        if t[i] in neutral:
            j = i
            while j < n and t[j] in neutral:
                j += 1
            before = _neutral_side(t[i - 1]) if i > 0 else sos
            after = _neutral_side(t[j]) if j < n else e  # eos == e
            fill = before if before == after else e  # N1 if equal, else N2
            for k in range(i, j):
                t[k] = fill
            i = j
        else:
            i += 1
    return t


def _resolve_implicit(types: list[str], base_level: int) -> list[int]:
    """Phases I1-I2: raise each character's level from its resolved type.

    The text is flat, so every character sits at `base_level` going in; only the
    bumps differ by parity.
    """
    levels: list[int] = []
    for tp in types:
        level = base_level
        if base_level & 1 == 0:  # I1: even (LTR) level
            if tp == "R":
                level += 1
            elif tp in ("AN", "EN"):
                level += 2
        else:  # I2: odd (RTL) level
            if tp in ("L", "EN", "AN"):
                level += 1
        levels.append(level)
    return levels


def _l2_order(levels: list[int], base_level: int) -> list[int]:
    """Rule L2: permutation of indices putting `levels` into visual order.

    From the highest level down to the lowest odd level (floored at the base
    direction), reverse every maximal run of levels at or above the threshold.
    A pure run (all even, or a single RTL element) is left untouched.
    """
    n = len(levels)
    order = list(range(n))
    odd = [lv for lv in levels if lv & 1]
    if not odd:
        return order
    floor = max(min(odd), base_level | 1)
    for threshold in range(max(levels), floor - 1, -1):
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


def _n0_strong(tp: str) -> str | None:
    """Strong direction of a type for N0, or None. Numbers count as R."""
    if tp == "L":
        return "L"
    if tp in ("R", "EN", "AN"):
        return "R"
    return None


def _prev_strong(types: list[str], idx: int, base_level: int) -> str:
    """Strong direction (N0 sense) preceding `idx`, or sos if none."""
    for k in range(idx - 1, -1, -1):
        s = _n0_strong(types[k])
        if s is not None:
            return s
    return "R" if base_level & 1 else "L"


def _neutral_side(tp: str) -> str:
    """Direction a non-neutral neighbour contributes to N1. Numbers count as R."""
    return "L" if tp == "L" else "R"


# Bundled Unicode data: the Bidi_Paired_Bracket property (BidiBrackets.txt),
# parsed once and cached. Kept as the official file rather than transcribed by
# hand, so it is the single source of truth. Its Unicode version must match
# `unicodedata`; `tests/vibidi` enforces that.
_BRACKETS_FILE = Path(__file__).parent / "BidiBrackets.txt"


@functools.lru_cache(maxsize=1)
def _bracket_tables() -> tuple[dict[str, str], frozenset[str], dict[str, str]]:
    """Parse BidiBrackets.txt -> (opening->closing, closing chars, canonical map).

    The canonical map covers BD16's canonical-equivalence clause (U+2329 / U+232A
    aliasing U+3008 / U+3009); it is derived from `unicodedata` canonical
    decompositions, so there is nothing to hand-maintain.
    """
    open_to_close: dict[str, str] = {}
    for raw in _BRACKETS_FILE.read_text(encoding="utf-8").splitlines():
        row = raw.split("#", 1)[0].strip()
        if not row:
            continue
        fields = [f.strip() for f in row.split(";")]
        if len(fields) >= 3 and fields[2] == "o":  # an opening bracket
            open_to_close[chr(int(fields[0], 16))] = chr(int(fields[1], 16))
    close_set = frozenset(open_to_close.values())
    canon: dict[str, str] = {}
    for bracket in open_to_close.keys() | close_set:
        decomp = unicodedata.decomposition(bracket).split()
        if len(decomp) == 1:  # a single canonical equivalent (no <compat> tag)
            canon[bracket] = chr(int(decomp[0], 16))
    return open_to_close, close_set, canon
