"""UAX #29 conformance and Videre-profile tests for ``word_splitter``."""

from pathlib import Path

import pytest
from uniseg.wordbreak import words as uniseg_words

from videre.core.shaping.text_partition.word_splitter import (
    UNICODE_VERSION,
    GapSpan,
    WordSpan,
    split_word_spans,
    word_boundaries,
)

_DATA = Path(__file__).parent / "data" / "WordBreakTest.txt"


def _load_conformance_cases() -> list[tuple[int, str, tuple[int, ...]]]:
    cases = []
    for lineno, raw in enumerate(_DATA.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        chars: list[str] = []
        expected: list[int] = []
        position = 0
        for token in line.split():
            if len(token) == 1 and ord(token) == 0xF7:
                expected.append(position)
            elif len(token) == 1 and ord(token) == 0xD7:
                continue
            else:
                chars.append(chr(int(token, 16)))
                position += 1
        cases.append((lineno, "".join(chars), tuple(expected)))
    return cases


def _uniseg_boundaries(text: str) -> tuple[int, ...]:
    if not text:
        return ()
    out = [0]
    position = 0
    for segment in uniseg_words(text):
        position += len(segment)
        out.append(position)
    return tuple(out)


def _span_values(text: str) -> list[tuple[str, bool | None]]:
    return [
        (
            text[span.start : span.end],
            span.atomic if isinstance(span, WordSpan) else None,
        )
        for span in split_word_spans(text)
    ]


def test_word_break_conformance() -> None:
    failures = []
    cases = _load_conformance_cases()
    assert cases
    for lineno, text, expected in cases:
        actual = word_boundaries(text)
        reference = _uniseg_boundaries(text)
        if actual != expected or actual != reference:
            codepoints = " ".join(f"{ord(c):04X}" for c in text)
            failures.append(
                f"line {lineno} [{codepoints}]: "
                f"expected {expected}, uniseg {reference}, got {actual}"
            )
    assert not failures, (
        f"{len(failures)}/{len(cases)} WordBreakTest cases failed:\n"
        + "\n".join(failures[:20])
    )


def test_word_break_data_version() -> None:
    header = _DATA.read_text(encoding="utf-8").splitlines()[0]
    version = header.split("-", 1)[1].rsplit(".txt", 1)[0]
    assert version == UNICODE_VERSION


@pytest.mark.parametrize(
    "text",
    [
        "",
        "Open file",
        "The quick brown fox can't jump 32.3 feet.",
        '\u05d0\u05d1\u05d2"\u05d3\u05d4\u05d5',
        "\U0001f1e8\U0001f1e6\U0001f1fa\U0001f1f8",
        "\U0001f469\u200d\U0001f4bb",
        "\u4e2d\u6587\u6e2c\u8a66",
        "a\u0308b",
    ],
)
def test_word_boundaries_match_uniseg(text: str) -> None:
    assert word_boundaries(text) == _uniseg_boundaries(text)


def test_profile_returns_source_spans_and_explicit_gaps() -> None:
    text = "  hello  world "
    spans = split_word_spans(text)
    assert spans == [
        GapSpan(0, 2),
        WordSpan(2, 7, atomic=True),
        GapSpan(7, 9),
        WordSpan(9, 14, atomic=True),
        GapSpan(14, 15),
    ]
    assert "".join(text[span.start : span.end] for span in spans) == text


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("(hello)", [("(hello)", True)]),
        ("hello ((", [("hello", True), (" ", None), ("((", True)]),
        ("hello!?,", [("hello!?,", True)]),
        ('"hello"', [('"hello"', True)]),
        ("\u4e2d\u6587", [("\u4e2d\u6587", False)]),
        ("\u4e2d \u6587", [("\u4e2d", False), (" ", None), ("\u6587", False)]),
        ("((\u4e2d\u6587))", [("((\u4e2d\u6587))", False)]),
    ],
)
def test_videre_profile(text: str, expected: list[tuple[str, bool | None]]) -> None:
    assert _span_values(text) == expected
