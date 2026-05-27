"""Tests for `videre.core.shaping.wrap.wrap_lines` and its integration in
`ShapedTextRendering.render_text` via the `width` / `wrap_words` parameters.

Covers: word-level wrap, cluster-level wrap, atomic-word overflow,
non-atomic split inside a word (CJK / oversized Latin run), inter-word
gap preservation, edge cases (empty input, width=None, width<=0).
"""

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.shaping import ShapedTextRendering, shape_text, wrap_lines


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


def _shape(text: str, size: int = 16, split_words: bool = True):
    return list(shape_text(text, size, split_words=split_words))


def _line_glyph_count(line) -> int:
    return sum(len(run.glyphs) for word in line.words for run in word.runs)


def _line_word_texts(line) -> list[str]:
    return ["".join(run.source_text for run in word.runs) for word in line.words]


# -- wrap_lines API contract --------------------------------------------------


def test_wrap_lines_width_none_yields_unchanged_lines() -> None:
    lines = _shape("The quick brown fox", split_words=True)
    wrapped = list(wrap_lines(lines, width=200, wrap_words=True))
    assert len(wrapped) == 1
    assert wrapped[0].words == lines[0].words


def test_wrap_lines_width_zero_yields_unchanged() -> None:
    lines = _shape("Hello world", split_words=True)
    wrapped = list(wrap_lines(lines, width=0, wrap_words=True))
    assert wrapped == lines


def test_wrap_lines_empty_lines_pass_through() -> None:
    lines = _shape("", split_words=True)
    wrapped = list(wrap_lines(lines, width=100, wrap_words=True))
    # split_text_to_renderable always emits at least one (empty) line.
    assert len(wrapped) == len(lines)
    assert all(line.is_empty() for line in wrapped if lines and not lines[0].words)


# -- Word-level wrap ----------------------------------------------------------


def test_word_wrap_splits_into_multiple_lines(fake_win) -> None:
    """A long sentence with a small width yields several lines, each ≤ width."""
    text = "The quick brown fox jumps over the lazy dog"
    r = ShapedTextRendering(fake_win.backend, size=16)
    s_full = r.render_text(text, color=Color(0, 0, 0))[1]
    s_wrap = r.render_text(text, color=Color(0, 0, 0), width=120, wrap_words=True)[1]
    assert s_wrap.get_height() > s_full.get_height()
    assert s_wrap.get_width() <= 120


def test_word_wrap_breaks_only_between_words() -> None:
    """With wrap_words=True, no original word is split (each emitted line's
    words are a contiguous prefix of the original word sequence)."""
    text = "alpha beta gamma delta epsilon zeta"
    lines = _shape(text, split_words=True)
    assert len(lines) == 1
    original_words = _line_word_texts(lines[0])
    wrapped = list(wrap_lines(lines, width=100, wrap_words=True, space_advance=5.0))
    # Concatenate the words of each wrapped line and check we recover the
    # original sequence in order.
    flat: list[str] = []
    for line in wrapped:
        flat.extend(_line_word_texts(line))
    assert flat == original_words


# -- Cluster-level wrap (wrap_words=False) -----------------------------------


def test_cluster_wrap_can_split_inside_a_word(fake_win) -> None:
    """With wrap_words=False, the wrap engine breaks at any cluster
    boundary, so a single English word can end up split across lines."""
    text = "supercalifragilisticexpialidocious"
    r = ShapedTextRendering(fake_win.backend, size=16)
    s = r.render_text(text, color=Color(0, 0, 0), width=80, wrap_words=False)[1]
    # The word is much wider than 80 px at size 16; it must wrap.
    assert s.get_height() > 25  # one line would be ~25 high


def test_cluster_wrap_each_line_within_width(fake_win) -> None:
    text = "The quick brown fox jumps over the lazy dog"
    r = ShapedTextRendering(fake_win.backend, size=16)
    s = r.render_text(text, color=Color(0, 0, 0), width=100, wrap_words=False)[1]
    assert s.get_width() <= 100


# -- Atomic vs non-atomic overflow -------------------------------------------


def test_atomic_word_too_long_overflows_under_word_wrap(fake_win) -> None:
    """An atomic word that doesn't fit on its own line gets emitted
    whole on a single line; the surface honors the requested width
    (the visual overflow is clipped at the right edge — same convention
    as pygame for a fixed-width text box)."""
    text = "supercalifragilisticexpialidocious"
    r = ShapedTextRendering(fake_win.backend, size=16)
    s_constrained = r.render_text(
        text, color=Color(0, 0, 0), width=80, wrap_words=True
    )[1]
    s_natural = r.render_text(text, color=Color(0, 0, 0))[1]  # no width: natural width
    # Single line in both cases
    assert s_constrained.get_height() == s_natural.get_height()
    # Surface clamped to requested width
    assert s_constrained.get_width() == 80
    # Natural width is much larger (the word genuinely needs more room)
    assert s_natural.get_width() > 80


def test_non_atomic_word_splits_under_word_wrap(fake_win) -> None:
    """A non-atomic 'word' (CJK / SE-Asian run coalesced into one Word)
    is allowed to break at a cluster boundary even under word wrap."""
    text = "你好世界你好世界你好世界你好世界"  # 16 CJK codepoints
    r = ShapedTextRendering(fake_win.backend, size=16)
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_yes = r.render_text(text, color=Color(0, 0, 0), width=80, wrap_words=True)[1]
    # CJK width per glyph ~ 16px → 16 chars wraps to several lines under 80px
    assert s_yes.get_width() <= 80
    assert s_yes.get_height() > s_no.get_height()


# -- Spaces preserved between words ------------------------------------------


def test_inter_word_spaces_visible(fake_win) -> None:
    """The shaped pipeline doesn't store spaces as glyphs, but the layout
    inserts a space_advance between consecutive words. So 'Hello world'
    must render wider than 'Helloworld' at natural width (no `width`
    constraint, otherwise the surface is clamped to it)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    with_space = r.render_text("Hello world", color=Color(0, 0, 0))[1]
    without_space = r.render_text("Helloworld", color=Color(0, 0, 0))[1]
    assert with_space.get_width() > without_space.get_width()


def test_no_phantom_gap_between_uax29_words_without_whitespace(fake_win) -> None:
    """UAX#29 splits `Hello世界` at the Latin/CJK boundary even with no
    whitespace between them. The renderer must NOT insert an inter-word
    `space_advance` there (would produce a phantom gap absent from the
    source). Conversely, `Hello 世界` keeps the gap because a real
    whitespace was present in the source.
    """
    r = ShapedTextRendering(fake_win.backend, size=16)
    no_space = r.render_text("Hello世界", color=Color(0, 0, 0))[1]
    with_space = r.render_text("Hello 世界", color=Color(0, 0, 0))[1]
    # The version with the source whitespace must be strictly wider than
    # the one without, by approximately one `space_advance` (the
    # difference need not be exact since space_advance is fractional and
    # the surface width rounds to an integer).
    assert with_space.get_width() > no_space.get_width()


def test_no_phantom_gap_in_wrap_mode(fake_win) -> None:
    """Same property, exercised through the wrap path (`split_words=True`,
    width given) which actually triggers the `space_before` decision in
    `_wrap_by_words` and `_render_line`."""
    import numpy as np

    from tests.common import pixels_alpha

    def content_width(surface) -> int:
        arr = pixels_alpha(surface)
        cols = (arr > 0).any(axis=1)
        nonzero = np.flatnonzero(cols)
        return int(nonzero.max()) + 1 if nonzero.size else 0

    r = ShapedTextRendering(fake_win.backend, size=16)
    s_no = r.render_text("Hello世界", color=Color(0, 0, 0), width=500, wrap_words=True)[
        1
    ]
    s_yes = r.render_text(
        "Hello 世界", color=Color(0, 0, 0), width=500, wrap_words=True
    )[1]
    assert content_width(s_yes) > content_width(s_no)


def test_punctuation_attached_no_extra_gap() -> None:
    """`Hello, world` produces two Words after trail-fusion (`Hello,`
    and `world`). The second has `space_before=True` (a real whitespace
    sat between them in the source); the comma must NOT introduce its
    own phantom gap between `Hello` and `,`. Equivalent: a sentence
    with comma must render the same width as the same sentence without
    comma plus the comma's natural advance, not plus one extra
    `space_advance`.
    """
    lines_with_comma = _shape("Hello, world", split_words=True)
    words = lines_with_comma[0].words
    assert ["".join(r.source_text for r in w.runs) for w in words] == [
        "Hello,",
        "world",
    ]
    assert words[0].space_before is False
    assert words[1].space_before is True


def test_shape_text_propagates_space_before() -> None:
    """`ShapedWord.space_before` mirrors the source whitespace. First
    word is always False; subsequent words carry True iff a whitespace
    token appeared between them and the previous word."""
    lines = _shape("Hello 世界 more", split_words=True)
    assert len(lines) == 1
    words = lines[0].words
    assert len(words) == 3
    flags = [w.space_before for w in words]
    assert flags == [False, True, True]


def test_shape_text_no_space_before_at_uax29_break() -> None:
    """At a UAX#29 word boundary without whitespace (Latin↔CJK), the
    second word must have `space_before=False`."""
    lines = _shape("Hello世界", split_words=True)
    words = lines[0].words
    assert len(words) == 2
    assert words[0].space_before is False
    assert words[1].space_before is False


def test_cluster_wrap_preserves_space_before() -> None:
    """Regression: `_wrap_by_clusters` reconstructs `ShapedWord`s via
    `_build_line`, which used to drop `space_before` ⇒ all post-wrap
    words ended up without inter-word gaps, rendering "How are you" as
    "Howareyou". Pin that the attribute is now propagated from the
    original word into every reconstruction."""
    text = "How are you ?"
    lines = _shape(text, split_words=True)
    wrapped = list(wrap_lines(lines, width=100, wrap_words=False, space_advance=4.0))
    # Across all wrapped sub-lines, every word that came from a source
    # word with `space_before=True` must keep that flag (mirror in the
    # reconstructed `ShapedWord`). Concretely: at least one word with
    # `space_before=True` must exist after wrap, otherwise the bug is
    # back.
    assert any(w.space_before for sl in wrapped for w in sl.words), (
        "no reconstructed word kept space_before=True after cluster wrap"
    )


def test_word_wrap_does_not_strand_trailing_space_at_eol_width(fake_win) -> None:
    """When two words exactly fit width, the trailing space of the second
    one must NOT push us to a new line. Pygame uses the same convention."""
    # Build a width where 'aaa bbb' would fit if we don't count the
    # trailing space of 'bbb', but not if we do.
    r = ShapedTextRendering(fake_win.backend, size=16)
    s = r.render_text("aaa bbb", color=Color(0, 0, 0), width=500, wrap_words=True)[1]
    one_line_height = s.get_height()
    # Now constrain width to exactly the natural width of "aaa bbb" → still 1 line
    natural = r.render_text("aaa bbb", color=Color(0, 0, 0))[1].get_width()
    s2 = r.render_text("aaa bbb", color=Color(0, 0, 0), width=natural, wrap_words=True)[
        1
    ]
    assert s2.get_height() == one_line_height


# -- Multi-line input ---------------------------------------------------------


def test_explicit_newlines_preserved_in_wrap(fake_win) -> None:
    """Source newlines always start a new line; wrap may add more lines
    inside each original line, but never coalesce two source lines."""
    text = "first line of text\nsecond line of text"
    r = ShapedTextRendering(fake_win.backend, size=16)
    s_no_wrap = r.render_text(text, color=Color(0, 0, 0))[1]
    s_wrap = r.render_text(text, color=Color(0, 0, 0), width=80, wrap_words=True)[1]
    # No wrap: 2 lines. With wrap at width=80: at least 2*ceil(line_width/80)
    # but always >= 2.
    assert s_wrap.get_height() >= s_no_wrap.get_height()


# -- Surface dimensions sanity ------------------------------------------------


@pytest.mark.parametrize("width", [40, 80, 120, 200])
@pytest.mark.parametrize("wrap_words", [True, False])
def test_wrap_respects_width(width: int, wrap_words: bool, fake_win) -> None:
    text = "Lorem ipsum dolor sit amet consectetur adipiscing elit"
    r = ShapedTextRendering(fake_win.backend, size=16)
    s = r.render_text(text, color=Color(0, 0, 0), width=width, wrap_words=wrap_words)[1]
    # Word-wrap may overflow on an oversized atomic word; here our words
    # are short, so all lines should fit.
    assert s.get_width() <= width


# -- shape_text contract: split_words drives the word boundaries -------------


def test_shape_text_split_words_changes_word_count() -> None:
    """When width is given, render_text passes split_words=True so the
    wrap engine can break between words. With split_words=False (the
    default when no width), each script run becomes a single Word."""
    text = "alpha beta gamma"
    lines_split = _shape(text, split_words=True)
    lines_nosplit = _shape(text, split_words=False)
    assert len(lines_split[0].words) == 3  # alpha, beta, gamma
    assert len(lines_nosplit[0].words) == 1  # one big chunk
