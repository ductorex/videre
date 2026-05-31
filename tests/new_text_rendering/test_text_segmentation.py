"""Regression tests for the standalone bidi-lite direction segmenter
`videre/core/shaping/text_partition/text_segmentation.py`
(`compute_directed_segments` + `compute_segments_visual_order`).

This module is NOT yet wired into the live shaping pipeline (which
still resolves direction through `_split_by_bidi` / `_split_by_level`
on top of python-bidi). These tests pin the from-scratch segmenter
against python-bidi as the ORACLE while that transition is decided.

Method: for a given paragraph base direction (forced on BOTH sides,
since the segmenter takes `base_is_rtl` as an external parameter and
must work for any imposed base), we rebuild the visual string from the
directed segments and compare it to `get_display(text, base_dir=...)`.

State: the "look-both-ways" number rule (a number sticks LTR to a latin
reachable BACKWARD across spaces, or to a latin ADJACENT forward; else it
follows the base) matches python-bidi EXACTLY over the whole alphabet
{latin, arabic (AL), hebrew (R), european digits, space} for BOTH bases,
exhaustively up to length 6.

Known out-of-scope gaps (documented as xfail, see `_UNSUPPORTED_CASES`):
- Arabic-Indic digits (Bidi_Class AN, e.g. U+0661) are classified as plain
  NUMBER and routed through the European-number rule; UAX#9 treats AN
  differently (they bind to the Arabic context).
- A single separator between two digits (UAX#9 W4: `.`/`,` becomes part of
  the number, so `1.2` is one number) is not implemented; `.`/`,` are seen
  as neutrals, so `1.2` gets split.
See the `videre-shaping-simplification` project note for the analysis.
"""

import functools
import itertools

import pytest
from bidi import get_display

from videre.core.shaping.text_partition.text_segmentation import (
    compute_directed_segments,
    compute_segments_visual_order,
)

# -- test alphabet (ASCII-safe source via chr) ------------------------------
LATIN = "a"  # strong LTR
ARABIC = chr(0x0628)  # Arabic Ba - strong RTL (Bidi_Class AL)
HEBREW = chr(0x05D0)  # Hebrew Alef - strong RTL (Bidi_Class R)
DIGIT1 = "1"  # European number (EN)
DIGIT2 = "2"  # a DISTINCT digit, so internal/inter-number order is observable
SPACE = " "  # neutral (whitespace)
# out-of-scope characters (used only in `_UNSUPPORTED_CASES`)
AN1 = chr(0x0661)  # Arabic-Indic digit one (Bidi_Class AN)
AN2 = chr(0x0662)  # Arabic-Indic digit two (Bidi_Class AN)
DOT = "."  # common separator (Bidi_Class CS)
COMMA = ","  # common separator (Bidi_Class CS)


def _visual(text: str, base_rtl: bool) -> str:
    """Visual (left-to-right pixel) string produced by the segmenter."""
    segments = compute_directed_segments(text, base_rtl)
    ordered = compute_segments_visual_order(segments, base_rtl)
    out: list[str] = []
    for seg in ordered:
        chars = [dc.character.c for dc in seg.directed_characters]
        if seg.is_reversed:
            chars = chars[::-1]
        out.append("".join(chars))
    return "".join(out)


def _reference(text: str, base_rtl: bool) -> str:
    """python-bidi visual order, base direction forced to match."""
    result = get_display(text, base_dir="R" if base_rtl else "L")
    # get_display is typed str | bytes (it echoes its input type); a str
    # input always yields a str.
    assert isinstance(result, str)
    return result


_DISPLAY = {ARABIC: "R", HEBREW: "H", AN1: "@", AN2: "#", SPACE: "_"}


def _show(s: str) -> str:
    """ASCII rendering of a (possibly RTL) string for readable test ids and
    failure messages, so terminals that mangle Arabic/Hebrew stay legible."""
    return "".join(_DISPLAY.get(c, c) for c in s)


def _assert_matches(text: str, base_rtl: bool) -> None:
    base = "RTL" if base_rtl else "LTR"
    assert _visual(text, base_rtl) == _reference(text, base_rtl), (
        f"{base} {_show(text)!r}: got {_show(_visual(text, base_rtl))!r} "
        f"want {_show(_reference(text, base_rtl))!r}"
    )


# === explicit, named cases (documentation + targeted debugging) ============

# Base LTR: matches python-bidi exactly on every shape.
_LTR_CASES = [
    "abc",
    "a b c",
    ARABIC * 3,
    ARABIC + SPACE + ARABIC,
    "ab" + ARABIC + "cd",
    HEBREW + SPACE + "ab",
    "a1b",
    DIGIT1 + DIGIT2,
    ARABIC + DIGIT1 + DIGIT2,
    LATIN + ARABIC + DIGIT1,
    DIGIT1 + SPACE + DIGIT2,
    DIGIT1 + SPACE + LATIN,
    ARABIC + SPACE + DIGIT1,
]

# Base RTL: also matches exactly, INCLUDING the number patterns that the old
# backward-only "pocket" rule used to miss (now fixed by look-both-ways).
_RTL_CASES = [
    ARABIC * 3,
    ARABIC + SPACE + ARABIC,
    HEBREW + SPACE + HEBREW,
    "abc",
    "ab" + ARABIC + "cd",
    LATIN + SPACE + DIGIT1,  # number after latin (sticks)
    ARABIC + SPACE + DIGIT1,  # single number after arabic
    DIGIT1,
    DIGIT1 + DIGIT2,  # adjacent digits keep internal order
    LATIN + DIGIT1,  # latin+number glued
    DIGIT1 + SPACE + DIGIT2,  # two numbers split by a space -> reordered
    DIGIT1 + SPACE + LATIN,  # number, space, latin
    ARABIC + DIGIT1 + SPACE + DIGIT2 + ARABIC,  # numbers between arabic
    DIGIT1 + SPACE + DIGIT1 + DIGIT1,
    HEBREW + DIGIT1 + SPACE + DIGIT2 + HEBREW,  # same with hebrew (R)
]


@pytest.mark.parametrize("text", _LTR_CASES, ids=[_show(t) for t in _LTR_CASES])
def test_explicit_ltr_matches_reference(text: str) -> None:
    _assert_matches(text, False)


@pytest.mark.parametrize("text", _RTL_CASES, ids=[_show(t) for t in _RTL_CASES])
def test_explicit_rtl_matches_reference(text: str) -> None:
    _assert_matches(text, True)


# === known out-of-scope gaps (Arabic-Indic AN digits + W4 separators) ======

# (text, base_rtl). These intentionally diverge from python-bidi until/unless
# AN handling and the W4 number-separator rule are implemented.
_UNSUPPORTED_CASES = [
    (AN1 + ARABIC, False),  # AN before arabic (LTR): @R, want R@
    (LATIN + SPACE + AN1, True),  # AN after latin+space (RTL): a_@, want @_a
    (DIGIT1 + DOT + DIGIT2, True),  # decimal in RTL: 1.2 -> 2.1, want 1.2
    (ARABIC + DIGIT1 + DOT + DIGIT2, True),  # R1.2 -> 2.1R, want 1.2R
    (DIGIT1 + COMMA + DIGIT2, True),  # thousands sep in RTL: 1,2 -> 2,1
]


@pytest.mark.xfail(
    reason="Out of scope: Arabic-Indic digits (AN) are routed through the "
    "European-number rule, and the W4 single-separator-in-number rule is not "
    "implemented. Flips to xpass if these get handled.",
    strict=False,
)
@pytest.mark.parametrize(
    "text,base_rtl",
    _UNSUPPORTED_CASES,
    ids=[f"{_show(t)}-{'RTL' if b else 'LTR'}" for t, b in _UNSUPPORTED_CASES],
)
def test_known_unsupported_cases(text: str, base_rtl: bool) -> None:
    _assert_matches(text, base_rtl)


# === exhaustive sweep over all short strings ===============================

_SCAN_ALPHABET = (LATIN, ARABIC, HEBREW, DIGIT1, DIGIT2, SPACE)
_SCAN_MAXLEN = 6


@functools.lru_cache(maxsize=None)
def _scan(base_rtl: bool, max_len: int) -> tuple[int, tuple[tuple[str, str, str], ...]]:
    """Every string over the alphabet up to `max_len`. Returns
    (total, failures) where each failure is (text, got, want)."""
    total = 0
    fails: list[tuple[str, str, str]] = []
    for n in range(1, max_len + 1):
        for combo in itertools.product(_SCAN_ALPHABET, repeat=n):
            text = "".join(combo)
            total += 1
            got = _visual(text, base_rtl)
            want = _reference(text, base_rtl)
            if got != want:
                fails.append((text, got, want))
    return total, tuple(fails)


def _sample(fails: tuple[tuple[str, str, str], ...], k: int = 15) -> str:
    return ", ".join(
        f"{_show(t)}->{_show(g)}(want {_show(w)})" for t, g, w in fails[:k]
    )


def test_exhaustive_ltr_matches_reference() -> None:
    """LTR base must match python-bidi on EVERY string up to length 6."""
    total, fails = _scan(False, _SCAN_MAXLEN)
    assert not fails, f"{len(fails)}/{total} LTR divergences: {_sample(fails)}"


def test_exhaustive_rtl_matches_reference() -> None:
    """RTL base must match python-bidi on EVERY string up to length 6
    (the look-both-ways number rule reaches 100% over this alphabet)."""
    total, fails = _scan(True, _SCAN_MAXLEN)
    assert not fails, f"{len(fails)}/{total} RTL divergences: {_sample(fails)}"
