"""UAX #29 conformance tests for source-text editing units."""

from pathlib import Path

from uniseg.graphemecluster import grapheme_cluster_boundaries

from videre.core.text_editing import grapheme_boundaries
from videre.core.textual.unicode_props import UNICODE_VERSION

_DATA = Path(__file__).parent / "data" / "GraphemeBreakTest.txt"


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
            if token == "\u00f7":
                expected.append(position)
            elif token != "\u00d7":
                chars.append(chr(int(token, 16)))
                position += 1
        cases.append((lineno, "".join(chars), tuple(expected)))
    return cases


def test_grapheme_break_conformance() -> None:
    failures = []
    cases = _load_conformance_cases()
    assert cases
    for lineno, text, expected in cases:
        actual = grapheme_boundaries(text)
        reference = tuple(grapheme_cluster_boundaries(text))
        if actual != expected or actual != reference:
            codepoints = " ".join(f"{ord(c):04X}" for c in text)
            failures.append(
                f"line {lineno} [{codepoints}]: "
                f"expected {expected}, uniseg {reference}, got {actual}"
            )
    assert not failures, (
        f"{len(failures)}/{len(cases)} GraphemeBreakTest cases failed:\n"
        + "\n".join(failures[:20])
    )


def test_grapheme_break_data_version() -> None:
    header = _DATA.read_text(encoding="utf-8").splitlines()[0]
    version = header.split("-", 1)[1].rsplit(".txt", 1)[0]
    assert version == UNICODE_VERSION
