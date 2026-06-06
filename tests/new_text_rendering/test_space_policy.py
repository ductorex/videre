"""Tests for `TextSpacePolicy` handling (`new_text_partition.space_policy` +
its wiring through `render.build_glyph_lines` / `wrap`).

Covers the spec table (width x wrap_words x policy -> start/inside/end gap
behaviour) end to end on the flat pipeline, plus the `collapse_spaces` pre-pass
and `resolve_space_policy` in isolation.
"""

import pygame
import pygame.freetype
import pytest

from videre.core.constants import TextSpacePolicy as SP
from videre.core.shaping.new_text_partition.partitioner import partition_text
from videre.core.shaping.new_text_partition.render import build_glyph_lines
from videre.core.shaping.new_text_partition.shaping import shape_line
from videre.core.shaping.new_text_partition.space_policy import (
    collapse_spaces,
    resolve_space_policy,
)
from videre.core.shaping.shaper import Shaper

_SIZE = 16


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


# -- helpers -----------------------------------------------------------------


def _lines_chars(text: str, shaper: Shaper, **kw) -> list[str]:
    """Per display line, the source characters of its glyphs in visual order."""
    lines = build_glyph_lines(text, shaper, _SIZE, **kw)
    return ["".join(text[g.logical_position] for g in gl.glyphs) for gl, _ in lines]


def _all_positions(text: str, shaper: Shaper, **kw) -> set[int]:
    lines = build_glyph_lines(text, shaper, _SIZE, **kw)
    return {g.logical_position for gl, _ in lines for g in gl.glyphs}


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


def test_collapse_drops_leading_and_trailing_gaps(shaper: Shaper) -> None:
    line = collapse_spaces(_shaped("  a  ", shaper))
    assert _gap_glyphs(line) == 0
    assert len(line.units) == 1
    assert not line.units[0].unit.is_gap


def test_collapse_all_whitespace_line_becomes_empty(shaper: Shaper) -> None:
    line = collapse_spaces(_shaped("   ", shaper))
    assert line.units == []


# -- end to end, no wrap (width absent) --------------------------------------


def test_no_wrap_collapse_inner_to_one_space(shaper: Shaper) -> None:
    assert _lines_chars("a   b", shaper, space_policy=SP.COLLAPSE) == ["a b"]


def test_no_wrap_collapse_drops_edges(shaper: Shaper) -> None:
    assert _lines_chars("  a   b  ", shaper, space_policy=SP.COLLAPSE) == ["a b"]


def test_no_wrap_preserve_keeps_everything(shaper: Shaper) -> None:
    assert _lines_chars("  a   b  ", shaper, space_policy=SP.PRESERVE) == ["  a   b  "]


def test_no_wrap_auto_is_preserve(shaper: Shaper) -> None:
    # AUTO + no wrap (wrap_words=False) -> PRESERVE.
    assert _lines_chars("a   b", shaper) == ["a   b"]


def test_collapse_all_whitespace_renders_empty_line(shaper: Shaper) -> None:
    assert _lines_chars("   ", shaper, space_policy=SP.COLLAPSE) == [""]
    assert _lines_chars("   ", shaper, space_policy=SP.PRESERVE) == ["   "]


# -- end to end, width wrap, collapse ----------------------------------------


def test_wrap_collapse_reduces_inner_runs(shaper: Shaper) -> None:
    # Wide enough to keep it all on one line; inner runs still collapse to one.
    chars = _lines_chars(
        "aa   bb   cc", shaper, width=10000, wrap_words=True, space_policy=SP.COLLAPSE
    )
    assert chars == ["aa bb cc"]


# -- end to end, width wrap, preserve + char ---------------------------------


def test_wrap_char_preserve_splits_gap_keeping_all_spaces(shaper: Shaper) -> None:
    text = "a      b"  # 6 spaces
    width = int(_adv("a  ", shaper))  # forces a break inside the gap
    lines = build_glyph_lines(
        text, shaper, _SIZE, width=width, wrap_words=False, space_policy=SP.PRESERVE
    )
    assert len(lines) >= 2  # the gap actually split across lines
    # Nothing dropped: every source position survives (gap scinded, not consumed).
    assert _all_positions(
        text, shaper, width=width, wrap_words=False, space_policy=SP.PRESERVE
    ) == set(range(len(text)))


# -- end to end, width wrap, preserve + word vs collapse ---------------------


def test_wrap_word_preserve_hangs_break_gap_collapse_drops_it(shaper: Shaper) -> None:
    text = "alpha beta"  # the inter-word space is source position 5
    width = int(_adv("alpha", shaper)) + 1  # "beta" cannot fit -> break at the gap
    common = dict(width=width, wrap_words=True)

    collapse_pos = _all_positions(text, shaper, **common, space_policy=SP.COLLAPSE)
    preserve_pos = _all_positions(text, shaper, **common, space_policy=SP.PRESERVE)

    full = set(range(len(text)))
    assert collapse_pos == full - {5}  # collapse consumes the break space
    assert preserve_pos == full  # preserve keeps it (hung at the line end)

    # The hung space sits at the end of the first display line.
    first_line = _lines_chars(text, shaper, **common, space_policy=SP.PRESERVE)[0]
    assert first_line.endswith(" ")
