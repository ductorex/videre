"""Tests for `TextSpacePolicy` handling (`text_partition.space_policy` +
its wiring through `render.build_glyph_lines` / `wrap`).

Covers the 8-case spec table (width x wrap_words x policy) end to end on the
flat pipeline — checking the gap behaviour at the START, INSIDE and END of each
logical / wrapped line — plus the `collapse_spaces` pre-pass and
`resolve_space_policy` in isolation.
"""

import pygame
import pygame.freetype
import pytest

from videre.core.constants import TextSpacePolicy as SP
from videre.core.shaping.render import build_glyph_lines
from videre.core.shaping.rendering.space_policy import (
    collapse_spaces,
    resolve_space_policy,
)
from videre.core.shaping.shaper import Shaper, shape_line
from videre.core.shaping.text_partition.partitioner import partition_text

_SIZE = 16


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


# -- helpers -----------------------------------------------------------------


def _lines_chars(text: str, shaper: Shaper, **kw) -> list[str]:
    """Per display line, the source characters of its glyphs in visual order.
    For LTR text this is the rendered line verbatim, so a list of expected
    strings pins the start / inside / end gap behaviour exactly."""
    lines = build_glyph_lines(text, shaper, _SIZE, **kw)
    return ["".join(text[g.logical_position] for g in gl.glyphs) for gl, _ in lines]


def _adv(text: str, shaper: Shaper) -> float:
    """Natural pixel advance of `text` (single line, nothing collapsed)."""
    lines = build_glyph_lines(text, shaper, _SIZE, space_policy=SP.PRESERVE)
    return sum(g.x_advance for gl, _ in lines for g in gl.glyphs)


def _shaped(text: str, shaper: Shaper):
    (line,) = partition_text(text).lines
    return shape_line(line, shaper, _SIZE)


def _gap_glyphs(line) -> int:
    return sum(len(u.glyphs) for u in line.units if u.unit.is_gap)


# -- resolve_space_policy ----------------------------------------------------


def test_resolve_auto_picks_collapse_for_word_wrap() -> None:
    assert resolve_space_policy(SP.AUTO, wrap_words=True) is SP.COLLAPSE


def test_resolve_auto_picks_preserve_otherwise() -> None:
    assert resolve_space_policy(SP.AUTO, wrap_words=False) is SP.PRESERVE


def test_resolve_keeps_explicit_policy() -> None:
    assert resolve_space_policy(SP.COLLAPSE, wrap_words=False) is SP.COLLAPSE
    assert resolve_space_policy(SP.PRESERVE, wrap_words=True) is SP.PRESERVE


# -- collapse_spaces (pre-pass) ----------------------------------------------


def test_collapse_reduces_inner_gap_to_one_glyph(shaper: Shaper) -> None:
    line = collapse_spaces(_shaped("a   b", shaper))
    assert _gap_glyphs(line) == 1  # 3 spaces -> 1
    assert sum(len(u.glyphs) for u in line.units if not u.unit.is_gap) == 2


def test_collapse_keeps_edge_gaps_shrunk_to_one(shaper: Shaper) -> None:
    # Edges are NOT trimmed by the pre-pass (that is word-wrap-only); each gap
    # run, including leading / trailing, is just shrunk to one space.
    line = collapse_spaces(_shaped("  a  ", shaper))
    assert _gap_glyphs(line) == 2  # leading + trailing, one glyph each
    assert len(line.units) == 3  # gap, "a", gap
    assert line.units[0].unit.is_gap and line.units[-1].unit.is_gap


def test_collapse_all_whitespace_line_shrinks_to_one_space(shaper: Shaper) -> None:
    line = collapse_spaces(_shaped("   ", shaper))
    assert len(line.units) == 1
    assert line.units[0].unit.is_gap
    assert _gap_glyphs(line) == 1


# -- the 8-case table, end to end (start / inside / end) ----------------------
#
# Cases 1-4 (width absent): no wrap, so wrap_words is irrelevant and edges are
# never trimmed. One canonical string with spaces at the start (2), inside (3)
# and end (2) pins all three positions at once.


@pytest.mark.parametrize("wrap_words", [False, True])
@pytest.mark.parametrize(
    "policy, expected", [(SP.COLLAPSE, " a b "), (SP.PRESERVE, "  a   b  ")]
)
def test_no_wrap_start_inside_end(
    shaper: Shaper, wrap_words: bool, policy: SP, expected: str
) -> None:
    """Cases 1-4. COLLAPSE shrinks every run (start / inside / end) to one space
    but keeps them; PRESERVE keeps them verbatim. char == word here (width
    absent => wrap_words irrelevant)."""
    got = _lines_chars("  a   b  ", shaper, wrap_words=wrap_words, space_policy=policy)
    assert got == [expected]


def test_word_wrap_collapse_trims_every_edge(shaper: Shaper) -> None:
    """Case 7 (> 0, word, collapse): inner runs -> one space; EVERY wrapped-line
    edge is trimmed — logical leading / trailing and the break gap alike."""
    text = "  aa   bb  cc  "  # leading 2, inner 3, inner 2, trailing 2
    width = int(_adv(" aa bb", shaper)) + 8  # fits collapsed "aa bb", not "cc" after it
    lines = _lines_chars(
        text, shaper, width=width, wrap_words=True, space_policy=SP.COLLAPSE
    )
    assert lines == ["aa bb", "cc"]
    for ln in lines:  # every wrapped-line edge is clean
        assert not ln.startswith(" ")
        assert not ln.endswith(" ")


def test_word_wrap_preserve_keeps_leading_inner_and_hangs_end(shaper: Shaper) -> None:
    """Case 8 (> 0, word, preserve): leading kept (start), runs kept (inside),
    the break gap hangs at the line END and is not reported to the next line."""
    text = "  aa   bb  cc"  # leading 2, inner 3, 2-space break gap before cc
    width = (
        int(_adv("  aa   bb", shaper)) + 12
    )  # fits up to "bb", not "cc" after the gap
    lines = _lines_chars(
        text, shaper, width=width, wrap_words=True, space_policy=SP.PRESERVE
    )
    assert lines == ["  aa   bb  ", "cc"]
    assert lines[0].startswith("  ")  # leading kept (start)
    assert lines[0].endswith("  ")  # break gap hung (end)
    assert not lines[1].startswith(" ")  # not reported to the next line's start


def test_char_wrap_collapse_shrinks_but_keeps_every_edge(shaper: Shaper) -> None:
    """Case 5 (> 0, char, collapse): runs shrink to one, but NO space is dropped
    at any wrapped-line edge (a char break must stay distinguishable from a word
    boundary). start / inside / end all survive, shrunk."""
    text = "  aa   bb  "  # -> " aa bb " once runs are shrunk
    width = int(_adv("aa b", shaper))  # narrow -> several char breaks
    lines = _lines_chars(
        text, shaper, width=width, wrap_words=False, space_policy=SP.COLLAPSE
    )
    assert len(lines) >= 2  # actually wrapped
    assert "".join(lines) == " aa bb "  # every space kept (shrunk), none dropped
    assert lines[0].startswith(" ")  # leading space kept at the first edge
    assert lines[-1].endswith(" ")  # trailing space kept at the last edge


def test_char_wrap_preserve_keeps_everything_verbatim(shaper: Shaper) -> None:
    """Case 6 (> 0, char, preserve): no shrink, no trim; a gap straddling a
    break splits per character. start / inside / end all survive verbatim."""
    text = "  aa   bb  "  # leading 2, inner 3, trailing 2
    width = int(_adv("aa b", shaper))  # narrow -> several char breaks
    lines = _lines_chars(
        text, shaper, width=width, wrap_words=False, space_policy=SP.PRESERVE
    )
    assert len(lines) >= 2
    assert "".join(lines) == text  # nothing dropped, nothing shrunk
    assert lines[0].startswith(" ")  # leading run kept at the first edge
    assert lines[-1].endswith(" ")  # trailing run kept at the last edge


def test_char_wrap_preserve_splits_a_wide_gap(shaper: Shaper) -> None:
    """Case 6 detail: a single wide inner gap splits across lines (not consumed)
    — every space survives the break."""
    text = "a      b"  # 6 spaces
    width = int(_adv("a  ", shaper))  # break inside the gap
    lines = _lines_chars(
        text, shaper, width=width, wrap_words=False, space_policy=SP.PRESERVE
    )
    assert len(lines) >= 2
    assert "".join(lines) == text  # all 6 spaces preserved across the split


# -- AUTO end to end + all-whitespace edge case ------------------------------


def test_auto_resolves_end_to_end(shaper: Shaper) -> None:
    """AUTO + word wrap behaves as COLLAPSE; AUTO + no wrap (the widget's
    default for char / unwrapped text) behaves as PRESERVE."""
    width = int(_adv(" aa bb", shaper)) + 8
    assert _lines_chars("  aa   bb  cc  ", shaper, width=width, wrap_words=True) == [
        "aa bb",
        "cc",
    ]
    assert _lines_chars("  a   b  ", shaper) == ["  a   b  "]


def test_all_whitespace_line(shaper: Shaper) -> None:
    assert _lines_chars("   ", shaper, space_policy=SP.COLLAPSE) == [" "]  # shrunk
    assert _lines_chars("   ", shaper, space_policy=SP.PRESERVE) == ["   "]
