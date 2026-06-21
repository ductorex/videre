"""Fast UAX #29 word boundaries plus Videre's shaping-oriented profile.

The strict layer, :func:`word_boundaries`, implements the Unicode 16.0
default word-boundary rules WB1-WB999. The profiled layer,
:func:`split_word_spans`, then applies Videre's UAX #14-based policy:

- whitespace becomes explicit gap spans;
- adjacent CJK/Hangul/complex-context fragments are coalesced so a shared
  direction/script/font run reaches HarfBuzz in one call, while remaining
  breakable by glyph cluster during word wrapping;
- opening/trailing punctuation is attached to its neighbouring word;
- quotes choose a side from adjacent separators.

All outputs are source offsets. No intermediate substring needs to be found
again by the partitioner.

Not handled — conditional hyphenation: a soft hyphen (U+00AD) is
``Word_Break=Format``, so WB4 absorbs it into the surrounding word and no break
opportunity is emitted at its position, even though its UAX #14 ``Line_Break=BA``
would allow one (hard hyphens, ZWSP and CJK edges still do). Wiring it up would
mean re-injecting the break here — ``EditUnitKind.SOFT_HYPHEN`` preserves the
information — and drawing a hyphen glyph at the break in the renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import TypeAlias

import unicodedataplus as unicode_data  # ty: ignore

_NEWLINES = frozenset({"Newline", "CR", "LF"})
_IGNORED = frozenset({"Extend", "Format", "ZWJ"})
_AHLETTER = frozenset({"ALetter", "Hebrew_Letter"})
_MIDNUMLETQ = frozenset({"MidNumLet", "Single_Quote"})
_LETTER_MID = frozenset({"MidLetter", *_MIDNUMLETQ})
_NUMBER_MID = frozenset({"MidNum", *_MIDNUMLETQ})
_HEBREW = frozenset({"Hebrew_Letter"})
_NUMERIC = frozenset({"Numeric"})
_EXTENDNUMLET_LEFT = frozenset({*_AHLETTER, "Numeric", "Katakana", "ExtendNumLet"})
_EXTENDNUMLET_RIGHT = frozenset({"ExtendNumLet"})
_AFTER_EXTENDNUMLET = frozenset({*_AHLETTER, "Numeric", "Katakana"})

# UAX #14 classes used by the Videre profile.
_LB_BREAKABLE = frozenset({"ID", "H2", "H3", "JL", "JV", "JT", "SA"})
_LB_TRAILING = frozenset({"EX", "IS", "CL", "CP", "BA", "NS", "IN", "HY"})
_LB_LEADING = frozenset({"OP"})
_LB_AMBIGUOUS = frozenset({"QU"})
_LB_WHITESPACE = frozenset({"SP", "BK", "CR", "LF", "NL", "ZW"})
_LB_COMBINING = frozenset({"CM", "ZWJ"})
_LB_COMBINING_RESET = frozenset({"BK", "CR", "LF", "NL", "SP", "ZW"})
_LB_BREAK_AFTER = frozenset({"HY"})


@dataclass(slots=True, frozen=True)
class WordSpan:
    start: int
    end: int
    atomic: bool
    break_before: bool = False
    no_break_before: tuple[int, ...] = ()


@dataclass(slots=True, frozen=True)
class GapSpan:
    start: int
    end: int


TextSpan: TypeAlias = WordSpan | GapSpan


@lru_cache(maxsize=4096)
def _word_property(c: str) -> str:
    return unicode_data.word_break(c)


@lru_cache(maxsize=4096)
def _line_property(c: str) -> str:
    return unicode_data.line_break(c)


@lru_cache(maxsize=4096)
def _is_extended_pictographic(c: str) -> bool:
    return unicode_data.is_extended_pictographic(c)


def word_boundaries(text: str) -> tuple[int, ...]:
    """Return all Unicode 16.0 default word-boundary offsets in ``text``.

    The implementation evaluates WB3-WB4 on adjacent source characters, then
    WB5-WB16 on a compact index of significant characters. This is the
    "Replacing Ignore Rules" formulation from UAX #29 section 6.2, without
    Uniseg's general-purpose mutable ``Run`` abstraction.
    """
    n = len(text)
    if not n:
        return ()

    props = [_word_property(c) for c in text]
    breaks = [True] * (n + 1)

    # WB3-WB4 operate on adjacent source characters. A value set here is final:
    # later rules only inspect boundaries still left at WB999's default break.
    for i in range(1, n):
        left = props[i - 1]
        right = props[i]
        if left == "CR" and right == "LF":  # WB3
            breaks[i] = False
        elif left in _NEWLINES:  # WB3a
            continue
        elif right in _NEWLINES:  # WB3b
            continue
        elif left == "ZWJ" and _is_extended_pictographic(text[i]):  # WB3c
            breaks[i] = False
        elif left == right == "WSegSpace":  # WB3d
            breaks[i] = False
        elif right in _IGNORED:  # WB4
            breaks[i] = False

    significant = [i for i, prop in enumerate(props) if prop not in _IGNORED]
    significant_rank = {source: rank for rank, source in enumerate(significant)}

    for i in range(1, n):
        if not breaks[i] or props[i] in _IGNORED:
            continue

        right_index = i
        rank = significant_rank[right_index]
        if rank == 0:
            continue
        left_index = significant[rank - 1]
        left = props[left_index]
        right = props[right_index]

        # WB3c after ignored characters: WB4 replaces the ignored sequence by
        # its preceding character for the remaining boundary rules.
        if left == "ZWJ" and _is_extended_pictographic(text[right_index]):
            breaks[i] = False
        elif left in _AHLETTER and right in _AHLETTER:  # WB5
            breaks[i] = False
        elif (
            left in _AHLETTER
            and right in _LETTER_MID
            and _next_significant_is(props, significant, rank, _AHLETTER)
        ):  # WB6
            breaks[i] = False
        elif (
            right in _AHLETTER
            and left in _LETTER_MID
            and _previous_significant_is(props, significant, rank - 1, _AHLETTER)
        ):  # WB7
            breaks[i] = False
        elif left == "Hebrew_Letter" and right == "Single_Quote":  # WB7a
            breaks[i] = False
        elif (
            left == "Hebrew_Letter"
            and right == "Double_Quote"
            and _next_significant_is(props, significant, rank, _HEBREW)
        ):  # WB7b
            breaks[i] = False
        elif (
            right == "Hebrew_Letter"
            and left == "Double_Quote"
            and _previous_significant_is(props, significant, rank - 1, _HEBREW)
        ):  # WB7c
            breaks[i] = False
        elif left == right == "Numeric":  # WB8
            breaks[i] = False
        elif left in _AHLETTER and right == "Numeric":  # WB9
            breaks[i] = False
        elif left == "Numeric" and right in _AHLETTER:  # WB10
            breaks[i] = False
        elif (
            right == "Numeric"
            and left in _NUMBER_MID
            and _previous_significant_is(props, significant, rank - 1, _NUMERIC)
        ):  # WB11
            breaks[i] = False
        elif (
            left == "Numeric"
            and right in _NUMBER_MID
            and _next_significant_is(props, significant, rank, _NUMERIC)
        ):  # WB12
            breaks[i] = False
        elif left == right == "Katakana":  # WB13
            breaks[i] = False
        elif left in _EXTENDNUMLET_LEFT and right in _EXTENDNUMLET_RIGHT:  # WB13a
            breaks[i] = False
        elif left == "ExtendNumLet" and right in _AFTER_EXTENDNUMLET:  # WB13b
            breaks[i] = False
        elif left == right == "Regional_Indicator" and _odd_ri_run(
            props, significant, rank
        ):  # WB15/WB16
            breaks[i] = False

    return tuple(i for i, is_break in enumerate(breaks) if is_break)


def split_word_spans(text: str) -> list[TextSpan]:
    """Return Videre-profiled word/gap spans in source order."""
    if not text:
        return []

    boundaries = word_boundaries(text)
    line_props = _resolve_line_properties([_line_property(c) for c in text])
    raw = list(zip(boundaries, boundaries[1:]))
    parts: list[tuple[int, int, str, bool]] = []
    sep_pending = True

    for idx, (start, end) in enumerate(raw):
        if _is_whitespace_span(line_props, start, end):
            sep_pending = True
            continue
        sep_right = idx == len(raw) - 1 or _is_whitespace_span(
            line_props, *raw[idx + 1]
        )
        kind = _classify_span(line_props, start, end, sep_pending, sep_right)
        parts.append((start, end, kind, sep_pending))
        sep_pending = False

    words = _merge_profiled_words(parts)
    spans: list[TextSpan] = []
    cursor = 0
    for word in words:
        if cursor < word.start:
            spans.append(GapSpan(cursor, word.start))
        spans.append(word)
        cursor = word.end
    if cursor < len(text):
        spans.append(GapSpan(cursor, len(text)))
    return spans


def _next_significant_is(
    props: list[str], significant: list[int], rank: int, expected: frozenset[str]
) -> bool:
    next_rank = rank + 1
    return next_rank < len(significant) and props[significant[next_rank]] in expected


def _previous_significant_is(
    props: list[str], significant: list[int], rank: int, expected: frozenset[str]
) -> bool:
    previous_rank = rank - 1
    return previous_rank >= 0 and props[significant[previous_rank]] in expected


def _odd_ri_run(props: list[str], significant: list[int], right_rank: int) -> bool:
    count = 0
    rank = right_rank - 1
    while rank >= 0 and props[significant[rank]] == "Regional_Indicator":
        count += 1
        rank -= 1
    return count % 2 == 1


def _is_whitespace_span(props: list[str], start: int, end: int) -> bool:
    return all(prop in _LB_WHITESPACE for prop in props[start:end])


def _resolve_line_properties(props: list[str]) -> list[str]:
    """Apply UAX #14 LB9 inheritance for combining marks and ZWJ.

    A variation selector has Line_Break=CM. It inherits the preceding base
    character's class, so an ideograph plus selector remains an ID fragment
    for Videre's CJK shaping profile.
    """
    resolved: list[str] = []
    for prop in props:
        if prop not in _LB_COMBINING:
            resolved.append(prop)
        elif not resolved or resolved[-1] in _LB_COMBINING_RESET:
            resolved.append("AL")
        else:
            resolved.append(resolved[-1])
    return resolved


def _classify_span(
    props: list[str], start: int, end: int, sep_left: bool, sep_right: bool
) -> str:
    classes = set(props[start:end])
    if classes <= _LB_BREAKABLE:
        return "cjk"
    if classes <= _LB_BREAK_AFTER:
        return "trail_break"
    if classes <= _LB_TRAILING:
        return "trail"
    if classes <= _LB_LEADING:
        return "lead"
    if classes <= _LB_AMBIGUOUS:
        return "lead" if sep_left and not sep_right else "trail"
    return "word"


def _merge_profiled_words(parts: list[tuple[int, int, str, bool]]) -> list[WordSpan]:
    result: list[WordSpan] = []
    i = 0
    break_next = False
    while i < len(parts):
        start, end, kind, sep_before = parts[i]
        if sep_before:
            break_next = False
        break_before = break_next
        break_next = False
        if kind == "cjk":
            j = i + 1
            while j < len(parts) and parts[j][2] == "cjk" and not parts[j][3]:
                end = parts[j][1]
                j += 1
            result.append(WordSpan(start, end, atomic=False, break_before=break_before))
            i = j
            continue
        if kind in {"trail", "trail_break"} and result and not sep_before:
            previous = result[-1]
            no_break_before = previous.no_break_before
            if not previous.atomic:
                no_break_before += tuple(range(start, end))
            result[-1] = WordSpan(
                previous.start,
                end,
                previous.atomic,
                previous.break_before,
                no_break_before,
            )
            break_next = kind == "trail_break"
            i += 1
            continue
        if kind == "lead":
            j = i + 1
            while j < len(parts) and parts[j][2] == "lead" and not parts[j][3]:
                j += 1
            if j < len(parts) and not parts[j][3]:
                end = parts[j][1]
                next_kind = parts[j][2]
                if next_kind == "cjk":
                    k = j + 1
                    while k < len(parts) and parts[k][2] == "cjk" and not parts[k][3]:
                        end = parts[k][1]
                        k += 1
                    result.append(
                        WordSpan(
                            start,
                            end,
                            atomic=False,
                            break_before=break_before,
                            no_break_before=tuple(range(start + 1, parts[j][0] + 1)),
                        )
                    )
                    i = k
                else:
                    result.append(
                        WordSpan(start, end, atomic=True, break_before=break_before)
                    )
                    i = j + 1
                continue
            result.append(
                WordSpan(start, parts[j - 1][1], atomic=True, break_before=break_before)
            )
            i = j
            continue
        result.append(WordSpan(start, end, atomic=True, break_before=break_before))
        i += 1
    return result
