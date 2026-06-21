"""Source-text segmentation into Unicode-aware editing units.

The raw Python string remains the only mutable source of truth. ``EditUnit``
objects are immutable half-open source ranges derived from it. They provide the
granularity used by cursor deletion and selection while leaving bidi and
shaping free to inspect the individual code points inside each range.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum, auto

from videre.core.textual import unicode_props

_GCB_CONTROL = frozenset({"Control", "CR", "LF"})
_GCB_EXTEND_OR_ZWJ = frozenset({"Extend", "ZWJ"})
_INCB_EXTEND_OR_LINKER = frozenset({"Extend", "Linker"})
_LINE_BREAK = frozenset({"BK", "CR", "LF", "NL"})

_BIDI_CONTROLS = frozenset(
    chr(codepoint)
    for codepoint in (
        0x061C,  # ALM
        0x200E,  # LRM
        0x200F,  # RLM
        0x202A,  # LRE
        0x202B,  # RLE
        0x202C,  # PDF
        0x202D,  # LRO
        0x202E,  # RLO
        0x2066,  # LRI
        0x2067,  # RLI
        0x2068,  # FSI
        0x2069,  # PDI
    )
)


class EditUnitKind(StrEnum):
    """How one source range participates in editing and layout."""

    TEXT = auto()
    LINE_BREAK = auto()
    TAB = auto()
    BIDI_CONTROL = auto()
    SOFT_HYPHEN = auto()
    BREAK_OPPORTUNITY = auto()
    NO_BREAK = auto()
    HIDDEN_CONTROL = auto()
    INVALID = auto()


@dataclass(slots=True, frozen=True)
class EditUnit:
    """One immutable editing unit in the original source string."""

    source_start: int
    source_end: int
    kind: EditUnitKind

    def __post_init__(self) -> None:
        if self.source_start < 0 or self.source_end <= self.source_start:
            raise ValueError(
                f"Invalid edit-unit range [{self.source_start}, {self.source_end})"
            )

    def source_text(self, source: str) -> str:
        return source[self.source_start : self.source_end]


def segment_edit_units(text: str) -> tuple[EditUnit, ...]:
    """Segment ``text`` into extended grapheme clusters and classify them.

    The grapheme boundaries implement UAX #29 Unicode 16 rules GB1-GB999,
    including emoji ZWJ sequences and Indic conjunct rule GB9c. Control-like
    graphemes are then classified for the downstream layout without being
    removed from the source.
    """
    boundaries = grapheme_boundaries(text)
    return tuple(
        EditUnit(start, end, _classify_unit(text[start:end]))
        for start, end in zip(boundaries, boundaries[1:])
    )


def segment_codepoints(text: str) -> tuple[EditUnit, ...]:
    """One edit unit per codepoint (still classified). The legacy renderer
    composes nothing — no shaping, no ligatures — so its natural editing
    granularity *is* the codepoint, not the grapheme. The legacy document uses
    this so its ``edit_units`` match its codepoint-by-codepoint visual
    navigation, letting ``TextInput`` drop its compatibility snapping layer.
    """
    return tuple(EditUnit(i, i + 1, _classify_unit(text[i])) for i in range(len(text)))


def grapheme_boundaries(text: str) -> tuple[int, ...]:
    """Return extended-grapheme boundary offsets for ``text``."""
    if not text:
        return (0,)

    gcb = [unicode_props.grapheme_cluster_break(c) for c in text]
    incb = [unicode_props.indic_conjunct_break(c) for c in text]
    pictographic = [unicode_props.is_extended_pictographic(c) for c in text]
    boundaries = [0]
    for i in range(1, len(text)):
        left = gcb[i - 1]
        right = gcb[i]
        should_break = True

        if left == "CR" and right == "LF":  # GB3
            should_break = False
        elif left in _GCB_CONTROL:  # GB4
            pass
        elif right in _GCB_CONTROL:  # GB5
            pass
        elif left == "L" and right in {"L", "V", "LV", "LVT"}:  # GB6
            should_break = False
        elif left in {"LV", "V"} and right in {"V", "T"}:  # GB7
            should_break = False
        elif left in {"LVT", "T"} and right == "T":  # GB8
            should_break = False
        elif right in _GCB_EXTEND_OR_ZWJ:  # GB9
            should_break = False
        elif right == "SpacingMark":  # GB9a
            should_break = False
        elif left == "Prepend":  # GB9b
            should_break = False
        elif _is_indic_conjunct_boundary(incb, i):  # GB9c
            should_break = False
        elif _is_emoji_zwj_boundary(gcb, pictographic, i):  # GB11
            should_break = False
        elif left == right == "Regional_Indicator" and _odd_ri_run(gcb, i):  # GB12/13
            should_break = False

        if should_break:  # GB999
            boundaries.append(i)
    boundaries.append(len(text))
    return tuple(boundaries)


def previous_edit_unit(
    units: tuple[EditUnit, ...], source_position: int
) -> EditUnit | None:
    """Unit immediately before, or containing the left side of, a cursor."""
    for unit in reversed(units):
        if unit.source_start < source_position:
            return unit
    return None


def next_edit_unit(
    units: tuple[EditUnit, ...], source_position: int
) -> EditUnit | None:
    """Unit immediately after, or containing the right side of, a cursor."""
    for unit in units:
        if unit.source_end > source_position:
            return unit
    return None


def expand_to_edit_units(
    units: tuple[EditUnit, ...], indices: Iterable[int]
) -> frozenset[int]:
    """Expand source ``indices`` to the full range of every edit unit they touch.

    Selection-based deletion and copy operate on a set of source indices that
    may, in bidi-mixed text, be non-contiguous. Mapping each index back to its
    edit unit and taking the whole unit range guarantees that an operation
    never keeps or removes only part of a grapheme cluster.
    """
    if not units:
        return frozenset()
    starts = [unit.source_start for unit in units]
    covered: set[int] = set()
    for index in indices:
        k = bisect.bisect_right(starts, index) - 1
        if 0 <= k < len(units):
            unit = units[k]
            if unit.source_start <= index < unit.source_end:
                covered.update(range(unit.source_start, unit.source_end))
    return frozenset(covered)


def _is_indic_conjunct_boundary(props: list[str], right_index: int) -> bool:
    if props[right_index] != "Consonant":
        return False
    i = right_index - 1
    saw_linker = False
    while i >= 0 and props[i] in _INCB_EXTEND_OR_LINKER:
        saw_linker = saw_linker or props[i] == "Linker"
        i -= 1
    return saw_linker and i >= 0 and props[i] == "Consonant"


def _is_emoji_zwj_boundary(
    gcb: list[str], pictographic: list[bool], right_index: int
) -> bool:
    if not pictographic[right_index] or gcb[right_index - 1] != "ZWJ":
        return False
    i = right_index - 2
    while i >= 0 and gcb[i] == "Extend":
        i -= 1
    return i >= 0 and pictographic[i]


def _odd_ri_run(props: list[str], right_index: int) -> bool:
    count = 0
    i = right_index - 1
    while i >= 0 and props[i] == "Regional_Indicator":
        count += 1
        i -= 1
    return count % 2 == 1


def _classify_unit(text: str) -> EditUnitKind:
    if any(unicode_props.category(c) == "Cs" for c in text):
        return EditUnitKind.INVALID
    if text == "\t":
        return EditUnitKind.TAB
    if all(unicode_props.line_break(c) in _LINE_BREAK for c in text):
        return EditUnitKind.LINE_BREAK
    if all(c in _BIDI_CONTROLS for c in text):
        return EditUnitKind.BIDI_CONTROL
    # Soft hyphen (U+00AD): a conditional-hyphenation point. Classified and
    # preserved here, but NOT yet consumed as a break opportunity by the shaping
    # pipeline \u2014 word_splitter's WB4 absorbs it (Word_Break=Format) before its
    # Line_Break=BA can apply, so the wrap treats the surrounding word as atomic.
    # This kind is the surviving hook to wire conditional hyphenation up later.
    if text == "\u00ad":
        return EditUnitKind.SOFT_HYPHEN
    if text == "\u200b":
        return EditUnitKind.BREAK_OPPORTUNITY
    if text in {"\u2060", "\ufeff"}:
        return EditUnitKind.NO_BREAK
    if all(unicode_props.category(c) in {"Cc", "Cf"} for c in text):
        return EditUnitKind.HIDDEN_CONTROL
    return EditUnitKind.TEXT
