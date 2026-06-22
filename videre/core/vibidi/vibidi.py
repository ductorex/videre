"""Pure-Python Unicode Bidirectional Algorithm (UAX#9): https://www.unicode.org/reports/tr9/

Resolves the embedding level of every character and reorders a display line
into visual order. It exists to provide the one rule python-bidi's pure-Python
path omits -- **N0**, paired brackets -- which is what makes mirrored brackets
(``[`` / ``]``) render correctly inside RTL text.

The primary entry points match the two places videre needs bidi:

* ``vibidi(text) -> VibidiText``: run once per paragraph. Each ``LogicalPosition``
  exposes ``is_rtl`` (the resolved direction), handed to HarfBuzz at segmentation
  time so it shapes -- and mirrors -- each run correctly.
* ``VibidiText.reorder(start, end)``: run per *display* line after wrapping, to
  put one wrapped interval in visual order (rule L2).

Scope / simplifications, all deliberate:

* **No L1.** L1 only resets trailing whitespace / separators to the base level,
  i.e. it repositions invisible blanks at a line end -- videre already handles
  that when it consumes wrap gaps. ``reorder`` therefore applies L2 uniformly,
  with no special-casing of spaces. The embedding *levels* stay internal
  (``_level``); nothing outside this module needs them.

The explicit phase is complete: X1-X8 maintain the directional-status stack,
X9 removes embeddings / overrides / BN characters from the bidi calculation,
and X10 runs W/N/I independently on each isolating run sequence. Removed
characters remain represented in ``logical_positions`` so source editing and
HarfBuzz shaping do not lose them; the public ``reorder`` omits them as UAX#9
requires, while ``reorder_retaining_controls`` is the rendering-pipeline hook.
"""

import functools
from dataclasses import dataclass
from enum import StrEnum, auto
from pathlib import Path
from typing import Sequence

from videre.core.textual import unicode_props


@dataclass(frozen=True, slots=True)
class LogicalPosition:
    is_rtl: bool
    logical: int


@dataclass(frozen=True, slots=True)
class LevelPosition(LogicalPosition):
    _level: int
    _removed: bool = False


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
        window = [
            position
            for position in self.logical_positions[logical_start:logical_end]
            if not position._removed
        ]
        return self._reorder_window(window)

    def reorder_retaining_controls(
        self, logical_start: int, logical_end: int
    ) -> Sequence[VisualPosition]:
        """Reorder while retaining X9 characters as zero-width source anchors."""
        return self._reorder_window(
            list(self.logical_positions[logical_start:logical_end])
        )

    def _reorder_window(self, window: list[LevelPosition]) -> Sequence[VisualPosition]:
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
    original = [
        unicode_props.bidirectional(c) or _default_class(c) for c in logical_text
    ]
    if rtl_policy is not RtlPolicy.RIGHT_TO_LEFT and not any(
        cls in _BIDI_NONTRIVIAL for cls in original
    ):
        # Fast path: no character forces RTL, a non-zero embedding level, or an
        # X9 removal, so the base direction is LTR and the full UAX#9 resolution
        # would leave every character at level 0 (W7 turns EN into L, neutrals
        # resolve to L), remove nothing, and keep visual order == logical order.
        return VibidiText(
            tuple(
                LevelPosition(is_rtl=False, logical=i, _level=0, _removed=False)
                for i in range(len(logical_text))
            ),
            base_is_rtl=False,
        )
    matching_pdi = _matching_isolates(original)
    base_level = _base_level(original, rtl_policy, matching_pdi)
    types, explicit_levels, removed = _resolve_explicit(
        original, base_level, matching_pdi
    )
    levels = list(explicit_levels)
    for sequence in _isolating_run_sequences(
        original, explicit_levels, removed, matching_pdi, base_level
    ):
        indices = sequence.indices
        sequence_original = [original[i] for i in indices]
        sequence_types = _resolve_weak(
            sequence_original, [types[i] for i in indices], sequence.sos
        )
        _resolve_brackets(
            "".join(logical_text[i] for i in indices),
            sequence_original,
            sequence_types,
            explicit_levels[indices[0]],
            sequence.sos,
        )
        sequence_levels = [explicit_levels[i] for i in indices]
        sequence_types = _resolve_neutral(
            sequence_types, sequence_levels, sequence.sos, sequence.eos
        )
        resolved_levels = _resolve_implicit(sequence_types, sequence_levels)
        for index, level in zip(indices, resolved_levels):
            levels[index] = level
    levels = _restore_removed_levels(levels, removed, base_level)
    positions = tuple(
        LevelPosition(
            is_rtl=bool(level & 1), logical=i, _level=level, _removed=removed[i]
        )
        for i, level in enumerate(levels)
    )
    return VibidiText(positions, bool(base_level & 1))


def _restore_removed_levels(
    levels: list[int], removed: list[bool], base_level: int
) -> list[int]:
    """Give X9 characters a neighbouring level without creating shaping cuts."""
    active_indices = [i for i, is_removed in enumerate(removed) if not is_removed]
    if not active_indices:
        return [base_level] * len(levels)
    first_level = levels[active_indices[0]]
    restored: list[int] = []
    previous_level: int | None = None
    for index, level in enumerate(levels):
        if not removed[index]:
            previous_level = level
            restored.append(level)
        else:
            restored.append(
                previous_level if previous_level is not None else first_level
            )
    return restored


# --- implementation details -------------------------------------------------
#
# Every helper traffics in UAX#9 bidi class strings ("L", "R", "AL", "EN", "AN",
# "WS", "ON", ...) as returned by `unicode_props.bidirectional`.

_MAX_DEPTH = 125
_X9_REMOVED = frozenset({"RLE", "LRE", "RLO", "LRO", "PDF", "BN"})
_ISOLATE_INITIATORS = frozenset({"RLI", "LRI", "FSI"})
_NEUTRAL_ISOLATES = frozenset({"B", "S", "WS", "ON", "RLI", "LRI", "FSI", "PDI"})

# Bidi classes whose presence rules out the LTR fast path in `vibidi`: strong /
# number RTL, and the explicit embedding / override / isolate / BN controls.
# Their absence guarantees the full resolution leaves every level at 0.
_BIDI_NONTRIVIAL = (
    _X9_REMOVED | _ISOLATE_INITIATORS | frozenset({"R", "AL", "AN", "PDI"})
)


@dataclass(frozen=True, slots=True)
class _DirectionalStatus:
    level: int
    override: str | None
    isolate: bool


@dataclass(frozen=True, slots=True)
class _IsolatingRunSequence:
    indices: list[int]
    sos: str
    eos: str


def _default_class(c: str) -> str:
    """Bidi class for a codepoint `unicodedataplus` doesn't know (unassigned).

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


def _matching_isolates(types: list[str]) -> dict[int, int]:
    """Return both directions of every structurally matched isolate pair."""
    stack: list[int] = []
    matching: dict[int, int] = {}
    for index, bidi_type in enumerate(types):
        if bidi_type in _ISOLATE_INITIATORS:
            stack.append(index)
        elif bidi_type == "PDI" and stack:
            initiator = stack.pop()
            matching[initiator] = index
            matching[index] = initiator
    return matching


def _base_level(
    types: list[str], policy: RtlPolicy, matching_pdi: dict[int, int]
) -> int:
    """Paragraph embedding level (UAX#9 P2/P3), or forced by `policy`."""
    if policy == RtlPolicy.LEFT_TO_RIGHT:
        return 0
    if policy == RtlPolicy.RIGHT_TO_LEFT:
        return 1
    index = 0
    while index < len(types):  # P2 ignores text inside isolate initiators.
        bidi_type = types[index]
        if bidi_type in _ISOLATE_INITIATORS:
            matching = matching_pdi.get(index)
            if matching is None:
                break
            index = matching + 1
            continue
        if bidi_type == "L":
            return 0
        if bidi_type in ("R", "AL"):
            return 1
        index += 1
    return 0


def _fsi_type(index: int, types: list[str], matching_pdi: dict[int, int]) -> str:
    """Resolve one FSI to LRI/RLI using P2/P3 on its isolated contents."""
    end = matching_pdi.get(index, len(types))
    cursor = index + 1
    while cursor < end:
        bidi_type = types[cursor]
        if bidi_type in _ISOLATE_INITIATORS:
            matching = matching_pdi.get(cursor)
            if matching is None or matching >= end:
                break
            cursor = matching + 1
            continue
        if bidi_type == "L":
            return "LRI"
        if bidi_type in ("R", "AL"):
            return "RLI"
        cursor += 1
    return "LRI"


def _next_odd(level: int) -> int:
    return level + 1 if level & 1 == 0 else level + 2


def _next_even(level: int) -> int:
    return level + 2 if level & 1 == 0 else level + 1


def _resolve_explicit(
    original: list[str], base_level: int, matching_pdi: dict[int, int]
) -> tuple[list[str], list[int], list[bool]]:
    """Apply X1-X9 and return current types, explicit levels, and X9 mask."""
    types = list(original)
    levels = [base_level] * len(original)
    removed = [bidi_type in _X9_REMOVED for bidi_type in original]
    stack = [_DirectionalStatus(base_level, None, False)]
    overflow_isolate_count = 0
    overflow_embedding_count = 0
    valid_isolate_count = 0

    for index, bidi_type in enumerate(original):
        status = stack[-1]
        if bidi_type in ("RLE", "LRE", "RLO", "LRO"):
            levels[index] = status.level
            new_level = (
                _next_odd(status.level)
                if bidi_type in ("RLE", "RLO")
                else _next_even(status.level)
            )
            if (
                new_level <= _MAX_DEPTH
                and overflow_isolate_count == 0
                and overflow_embedding_count == 0
            ):
                override = (
                    "R" if bidi_type == "RLO" else "L" if bidi_type == "LRO" else None
                )
                stack.append(_DirectionalStatus(new_level, override, False))
            elif overflow_isolate_count == 0:
                overflow_embedding_count += 1
        elif bidi_type in _ISOLATE_INITIATORS:
            levels[index] = status.level
            if status.override is not None:
                types[index] = status.override
            isolate_type = (
                _fsi_type(index, original, matching_pdi)
                if bidi_type == "FSI"
                else bidi_type
            )
            new_level = (
                _next_odd(status.level)
                if isolate_type == "RLI"
                else _next_even(status.level)
            )
            if (
                new_level <= _MAX_DEPTH
                and overflow_isolate_count == 0
                and overflow_embedding_count == 0
            ):
                valid_isolate_count += 1
                stack.append(_DirectionalStatus(new_level, None, True))
            else:
                overflow_isolate_count += 1
        elif bidi_type == "PDI":
            if overflow_isolate_count > 0:
                overflow_isolate_count -= 1
            elif valid_isolate_count > 0:
                overflow_embedding_count = 0
                while not stack[-1].isolate:
                    stack.pop()
                stack.pop()
                valid_isolate_count -= 1
            status = stack[-1]
            levels[index] = status.level
            if status.override is not None:
                types[index] = status.override
        elif bidi_type == "PDF":
            levels[index] = status.level
            if overflow_isolate_count == 0:
                if overflow_embedding_count > 0:
                    overflow_embedding_count -= 1
                elif len(stack) >= 2 and not stack[-1].isolate:
                    stack.pop()
        elif bidi_type == "B":
            levels[index] = base_level
            stack = [_DirectionalStatus(base_level, None, False)]
            overflow_isolate_count = 0
            overflow_embedding_count = 0
            valid_isolate_count = 0
        else:
            levels[index] = status.level
            if status.override is not None:
                types[index] = status.override
    return types, levels, removed


def _isolating_run_sequences(
    original: list[str],
    levels: list[int],
    removed: list[bool],
    matching_pdi: dict[int, int],
    base_level: int,
) -> list[_IsolatingRunSequence]:
    """Build BD13 isolating run sequences and their X10 sos/eos values."""
    active = [index for index, is_removed in enumerate(removed) if not is_removed]
    if not active:
        return []

    runs: list[list[int]] = []
    for index in active:
        if not runs or levels[runs[-1][-1]] != levels[index]:
            runs.append([index])
        else:
            runs[-1].append(index)
    run_for_index = {
        index: run_index for run_index, run in enumerate(runs) for index in run
    }
    active_position = {index: position for position, index in enumerate(active)}
    sequences: list[_IsolatingRunSequence] = []
    visited: set[int] = set()

    starts = [
        run_index
        for run_index, run in enumerate(runs)
        if not (
            original[run[0]] == "PDI"
            and run[0] in matching_pdi
            and matching_pdi[run[0]] < run[0]
        )
    ]
    for start in [*starts, *range(len(runs))]:
        if start in visited:
            continue
        sequence_indices: list[int] = []
        run_index = start
        while run_index not in visited:
            visited.add(run_index)
            run = runs[run_index]
            sequence_indices.extend(run)
            last = run[-1]
            if original[last] not in _ISOLATE_INITIATORS:
                break
            pdi = matching_pdi.get(last)
            if pdi is None:
                break
            run_index = run_for_index[pdi]

        first = sequence_indices[0]
        first_position = active_position[first]
        previous_level = (
            levels[active[first_position - 1]] if first_position > 0 else base_level
        )
        sos = _direction(max(levels[first], previous_level))

        last = sequence_indices[-1]
        last_position = active_position[last]
        if original[last] in _ISOLATE_INITIATORS and matching_pdi.get(last) is None:
            following_level = base_level
        else:
            following_level = (
                levels[active[last_position + 1]]
                if last_position + 1 < len(active)
                else base_level
            )
        eos = _direction(max(levels[last], following_level))
        sequences.append(_IsolatingRunSequence(sequence_indices, sos, eos))
    return sequences


def _direction(level: int) -> str:
    return "R" if level & 1 else "L"


def _resolve_weak(original: list[str], current: list[str], sos: str) -> list[str]:
    """Phases W1-W7: resolve NSM, numbers and number separators, in order."""
    t = list(current)
    n = len(t)

    # W1: each NSM takes the type of the previous character (sos at the start).
    prev = sos
    for i in range(n):
        if t[i] == "NSM":
            t[i] = (
                "ON"
                if i > 0 and original[i - 1] in _ISOLATE_INITIATORS | {"PDI"}
                else prev
            )
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
    text: str, original: list[str], types: list[str], embedding_level: int, sos: str
) -> None:
    """Phase N0: resolve each pair of matched brackets to a single direction.

    Mutates `types` in place. This is the rule python-bidi's pure-Python path
    skips, and the reason a ``[`` framing a latin island in RTL text was being
    mirrored to ``]``: a correctly resolved bracket keeps both sides consistent.
    `original` carries the pre-W1 classes, needed only for the NSM clause below.
    """
    e = _direction(embedding_level)
    o = "L" if e == "R" else "R"  # opposite direction
    for open_i, close_i in _bracket_pairs(text, types):
        inside = {_n0_strong(types[k]) for k in range(open_i + 1, close_i)}
        if e in inside:  # N0.b: a strong matching the embedding direction
            direction = e
        elif o in inside:  # N0.c: only the opposite strong direction inside
            prev = _prev_strong(types, open_i, sos)
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


def _resolve_neutral(
    types: list[str], levels: list[int], sos: str, eos: str
) -> list[str]:
    """Phases N1-N2: resolve runs of neutral / isolate-formatting characters."""
    t = list(types)
    n = len(t)
    i = 0
    while i < n:
        if t[i] in _NEUTRAL_ISOLATES:
            j = i
            while j < n and t[j] in _NEUTRAL_ISOLATES:
                j += 1
            before = _neutral_side(t[i - 1]) if i > 0 else sos
            after = _neutral_side(t[j]) if j < n else eos
            for k in range(i, j):
                t[k] = before if before == after else _direction(levels[k])
            i = j
        else:
            i += 1
    return t


def _resolve_implicit(types: list[str], explicit_levels: list[int]) -> list[int]:
    """Phases I1-I2: raise each character's level from its resolved type."""
    levels: list[int] = []
    for tp, explicit_level in zip(types, explicit_levels):
        level = explicit_level
        if explicit_level & 1 == 0:  # I1: even (LTR) level
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


def _prev_strong(types: list[str], idx: int, sos: str) -> str:
    """Strong direction (N0 sense) preceding `idx`, or sos if none."""
    for k in range(idx - 1, -1, -1):
        s = _n0_strong(types[k])
        if s is not None:
            return s
    return sos


def _neutral_side(tp: str) -> str:
    """Direction a non-neutral neighbour contributes to N1. Numbers count as R."""
    return "L" if tp == "L" else "R"


# Bundled Unicode data: the Bidi_Paired_Bracket property (BidiBrackets.txt),
# parsed once and cached. Kept as the official file rather than transcribed by
# hand, so it is the single source of truth. Its Unicode version must match
# `unicodedataplus` (via `unicode_props`); `tests/vibidi` enforces that.
_BRACKETS_FILE = Path(__file__).parent / "BidiBrackets.txt"


@functools.lru_cache(maxsize=1)
def _bracket_tables() -> tuple[dict[str, str], frozenset[str], dict[str, str]]:
    """Parse BidiBrackets.txt -> (opening->closing, closing chars, canonical map).

    The canonical map covers BD16's canonical-equivalence clause (U+2329 / U+232A
    aliasing U+3008 / U+3009); it is derived from `unicodedataplus` canonical
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
        decomp = unicode_props.decomposition(bracket).split()
        if len(decomp) == 1:  # a single canonical equivalent (no <compat> tag)
            canon[bracket] = chr(int(decomp[0], 16))
    return open_to_close, close_set, canon
