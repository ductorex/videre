"""Structural inspection of the flat shaping pipeline — no pixels.

Instead of freezing a PNG, these walk `RenderedTextGlyphMap.wrapped_glyph_lines`
(the `PositionedGlyph`s after partition -> shape -> wrap -> reorder) and assert
how glyphs map back to source characters. That checks two things a snapshot
can't tell apart:

- **wrapping** — which source character lands on which display line, that none
  is lost or duplicated, and that only inter-word spaces vanish at break points;
- **bidi** — per-glyph direction / mirroring (an RTL run reverses visual order;
  a mirror char shaped RTL swaps glyph id).

A pixel snapshot only guarantees "unchanged since baseline"; these encode
"correct". The bracket case (UAX#9 N0) is the bug vibidi fixed; this test pins it.

`RenderedTextGlyphMap` is defined in `model.py` but not yet produced by the
pipeline, so `_gmap` assembles one from `partition_text` + `build_glyph_lines`.
"""

import pygame
import pygame.freetype
import pytest

from videre.core.shaping.new_text_partition.model import RenderedTextGlyphMap
from videre.core.shaping.new_text_partition.partitioner import partition_text
from videre.core.shaping.new_text_partition.render import build_glyph_lines
from videre.core.shaping.shaper import Shaper
from videre.fonts.provider import get_font_provider
from videre.testing.utils import TEXT_SAMPLES

_SIZE = 20
# Three RTL Arabic letters (raw, like test_new_caret's ARAB sample).
ARB = "عرب"


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


def _gmap(
    text: str, shaper: Shaper, *, width: int | None = None, wrap_words: bool = True
) -> RenderedTextGlyphMap:
    """Assemble the (currently un-wired) `RenderedTextGlyphMap` for `text`."""
    lines = build_glyph_lines(text, shaper, _SIZE, width=width, wrap_words=wrap_words)
    return RenderedTextGlyphMap(partition_text(text), [gl for gl, _ in lines])


def _positions_per_line(gmap: RenderedTextGlyphMap) -> list[list[int]]:
    """Per display line, the glyphs' `logical_position`s in visual order."""
    return [[g.logical_position for g in gl.glyphs] for gl in gmap.wrapped_glyph_lines]


def _all_positions(gmap: RenderedTextGlyphMap) -> list[int]:
    """Every glyph's `logical_position`, lines concatenated in display order."""
    return [g.logical_position for gl in gmap.wrapped_glyph_lines for g in gl.glyphs]


def _glyphs_at(gmap: RenderedTextGlyphMap, pos: int) -> list:
    return [
        g
        for gl in gmap.wrapped_glyph_lines
        for g in gl.glyphs
        if g.logical_position == pos
    ]


def _ltr_glyph_id(shaper: Shaper, ch: str) -> int:
    _, font_path = get_font_provider().get_font_info(ch)
    glyphs = shaper.shape(
        text=ch, font_path=font_path, size_px=_SIZE, script="Latn", right_to_left=False
    )
    return glyphs[0].glyph_id


# -- wrapping: coverage / no loss / no duplication --------------------------


def test_single_line_covers_every_source_char(shaper) -> None:
    """No width -> one line, and (for plain ASCII) every source index is the
    logical_position of some glyph, gaps included."""
    text = "ab cd"
    gmap = _gmap(text, shaper)
    assert len(gmap.wrapped_glyph_lines) == 1
    assert set(_all_positions(gmap)) == set(range(len(text)))


def test_inter_word_space_is_a_gap_glyph(shaper) -> None:
    """A space kept mid-line (not at a break) is carried as an `is_gap` glyph,
    not dropped — so justify/selection can treat it specially."""
    gmap = _gmap("ab cd", shaper)
    space_glyphs = _glyphs_at(gmap, 2)  # the space in "ab cd"
    assert space_glyphs and all(g.is_gap for g in space_glyphs)


def test_wrap_keeps_every_visible_char_once(shaper) -> None:
    text = "alpha beta gamma"
    gmap = _gmap(text, shaper, width=100)
    assert len(gmap.wrapped_glyph_lines) > 1  # actually wrapped
    visible = {i for i, c in enumerate(text) if not c.isspace()}
    positions = _all_positions(gmap)
    # every visible char survives the wrap...
    assert visible <= set(positions)
    # ...exactly once (no char duplicated across the break)
    visible_hits = [p for p in positions if p in visible]
    assert len(visible_hits) == len(set(visible_hits))


def test_wrap_drops_only_whitespace_at_breaks(shaper) -> None:
    text = "alpha beta gamma"
    gmap = _gmap(text, shaper, width=100)
    dropped = set(range(len(text))) - set(_all_positions(gmap))
    assert dropped  # something was dropped (the break spaces)
    assert all(text[i].isspace() for i in dropped)


def test_ltr_visual_order_equals_logical_order(shaper) -> None:
    """LTR text: concatenating lines in display order yields strictly
    increasing source positions (visual order == logical order)."""
    gmap = _gmap("alpha beta gamma", shaper, width=100)
    flat = _all_positions(gmap)
    assert flat == sorted(flat)


# -- bidi: RTL visual reversal ----------------------------------------------


def test_rtl_pure_reverses_visual_order(shaper) -> None:
    """Pure Arabic (base RTL): on the line, the first (leftmost) glyph maps to
    a later source position than the last (rightmost) one, and every glyph —
    the inter-word gap included — is flagged RTL."""
    gmap = _gmap(f"{ARB} {ARB}", shaper)
    line = _positions_per_line(gmap)[0]
    assert line[0] > line[-1]
    assert all(g.is_rtl for gl in gmap.wrapped_glyph_lines for g in gl.glyphs)


# -- bidi: paired brackets in the real 'arabic' sample (UAX#9 N0) -----------


def test_arabic_sample_keeps_both_bracket_shapes(shaper) -> None:
    """The 'arabic' sample, rendered like `test_text_sample_renders_to_snapshot`
    (width=600, wrap), frames a latin IPA transcription in one '[' ... ']' pair.
    A correct render paints BOTH shapes — one opening, one closing — whether the
    brackets resolve straight to LTR or stay RTL and get mirrored AND
    repositioned (the reorder+mirror compensation). We assert on the painted
    shapes of the two source brackets as a SET, not on one glyph's direction, so
    the check survives that compensation. Before vibidi (rule N0) both collapsed
    onto ']'; N0 resolves the pair, so the two shapes are now distinct."""
    text = TEXT_SAMPLES["arabic"]
    bracket_positions = {i for i, c in enumerate(text) if c in "[]"}
    assert len(bracket_positions) == 2  # the sample has exactly one '[' and one ']'
    gmap = _gmap(text, shaper, width=600, wrap_words=True)
    shapes = {
        g.glyph_id
        for gl in gmap.wrapped_glyph_lines
        for g in gl.glyphs
        if g.logical_position in bracket_positions
    }
    assert shapes == {_ltr_glyph_id(shaper, "["), _ltr_glyph_id(shaper, "]")}
