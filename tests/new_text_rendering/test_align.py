"""Tests for the `align` parameter of `ShapedTextRendering.render_text`.

Pins horizontal placement contracts: LEFT (default), CENTER, RIGHT, and
JUSTIFY (with paragraph-end exemption). Uses pixel-column inspection
since alignment is not encoded in any returned metadata.
"""

import numpy as np
import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha
from videre.colors import Color
from videre.core.constants import TextAlign
from videre.core.rendering_result import Rendering
from videre.core.shaping import ShapedTextRendering


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


def _first_nonzero_col(rendering: Rendering) -> int:
    arr = pixels_alpha(rendering)
    cols = (arr > 0).any(axis=1)
    nz = np.flatnonzero(cols)
    return int(nz.min()) if nz.size else -1


def _line_right_edges(rendering: Rendering, line_block_height: int) -> list[int]:
    """Returns the rightmost non-zero pixel column for each line block.

    Splits the surface vertically into chunks of `line_block_height`
    pixels and scans each. Useful to verify that justified lines reach
    the target width while paragraph-end lines stay flush-left.
    """
    arr = pixels_alpha(rendering)
    h = rendering.get_height()
    out: list[int] = []
    y = 0
    while y < h:
        block = arr[:, y : y + line_block_height]
        cols = (block > 0).any(axis=1)
        nz = np.flatnonzero(cols)
        if nz.size:
            out.append(int(nz.max()) + 1)
        y += line_block_height
    return out


# -- LEFT (default) ----------------------------------------------------------


def test_default_align_is_left(fake_win) -> None:
    """`align=None` must behave like LEFT: content starts near column 0."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    s = r.render_text(
        "Hello", color=Color(0, 0, 0), width=200, wrap_words=True, align=None
    )[1]
    assert _first_nonzero_col(s) <= 2


def test_align_left_explicit(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    s = r.render_text(
        "Hello", color=Color(0, 0, 0), width=200, wrap_words=True, align=TextAlign.LEFT
    )[1]
    assert _first_nonzero_col(s) <= 2


# -- CENTER / RIGHT ----------------------------------------------------------


def test_align_center_pushes_content_to_middle(fake_win) -> None:
    """CENTER places the line such that the slack is split evenly."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    width = 200
    s_left = r.render_text(
        text, color=Color(0, 0, 0), width=width, wrap_words=True, align=TextAlign.LEFT
    )[1]
    s_center = r.render_text(
        text, color=Color(0, 0, 0), width=width, wrap_words=True, align=TextAlign.CENTER
    )[1]
    natural_width = r.render_text(text, color=Color(0, 0, 0))[1].get_width()
    expected_offset = (width - natural_width) // 2
    actual_offset = _first_nonzero_col(s_center) - _first_nonzero_col(s_left)
    # Allow ±2 px of slack for sub-pixel rounding.
    assert abs(actual_offset - expected_offset) <= 2


def test_align_right_pushes_content_to_right_edge(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    width = 200
    s_right = r.render_text(
        text, color=Color(0, 0, 0), width=width, wrap_words=True, align=TextAlign.RIGHT
    )[1]
    natural_width = r.render_text(text, color=Color(0, 0, 0))[1].get_width()
    arr = pixels_alpha(s_right)
    cols = (arr > 0).any(axis=1)
    last_col = int(np.flatnonzero(cols).max()) + 1
    # Last column should be near the right edge (within natural_width tolerance).
    assert last_col >= width - 4
    # And content should NOT start at column 0 (otherwise we'd be left-aligned).
    assert _first_nonzero_col(s_right) >= width - natural_width - 4


# -- JUSTIFY -----------------------------------------------------------------


def test_align_justify_stretches_non_final_lines(fake_win) -> None:
    """JUSTIFY widens inter-word gaps so non-final lines reach width.
    The last line of a paragraph stays at its natural width
    (left-aligned), matching CSS / browsers / Word."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "one two three four five six"
    width = 120
    s_left = r.render_text(
        text, color=Color(0, 0, 0), width=width, wrap_words=True, align=TextAlign.LEFT
    )[1]
    s_just = r.render_text(
        text,
        color=Color(0, 0, 0),
        width=width,
        wrap_words=True,
        align=TextAlign.JUSTIFY,
    )[1]
    edges_left = _line_right_edges(s_left, 24)
    edges_just = _line_right_edges(s_just, 24)
    assert len(edges_left) == len(edges_just) >= 2
    # Non-final line(s) reach (close to) width under JUSTIFY but not LEFT.
    for i in range(len(edges_just) - 1):
        assert edges_just[i] > edges_left[i], (
            f"line {i} not stretched: left={edges_left[i]} just={edges_just[i]}"
        )
        assert edges_just[i] >= width - 4
    # Last line is the paragraph end -> stays left (same as LEFT path).
    assert edges_just[-1] == edges_left[-1]


def test_align_justify_single_line_unchanged(fake_win) -> None:
    """A text that fits on one line is its own paragraph end; JUSTIFY
    must NOT stretch it (only multi-line paragraphs justify)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "one two"
    width = 200
    s_left = r.render_text(
        text, color=Color(0, 0, 0), width=width, wrap_words=True, align=TextAlign.LEFT
    )[1]
    s_just = r.render_text(
        text,
        color=Color(0, 0, 0),
        width=width,
        wrap_words=True,
        align=TextAlign.JUSTIFY,
    )[1]
    a = pixels_alpha(s_left)
    b = pixels_alpha(s_just)
    assert (a == b).all(), "JUSTIFY should not affect a single-line paragraph"


def test_align_justify_respects_paragraph_breaks(fake_win) -> None:
    """An explicit `\\n` resets the paragraph: each paragraph's last
    line must stay flush-left under JUSTIFY."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "one two three four\nshort"
    width = 120
    s = r.render_text(
        text,
        color=Color(0, 0, 0),
        width=width,
        wrap_words=True,
        align=TextAlign.JUSTIFY,
    )[1]
    edges = _line_right_edges(s, 24)
    # Last line of each paragraph stays at natural width; here paragraph
    # 1 has at least one wrap, then paragraph 2 is "short" alone.
    # We don't pin exact line counts, just that the very last line
    # ("short") is much shorter than width (no forced stretching).
    assert edges[-1] < width - 10


# -- Width=None: align is a no-op (no slack to play with) -------------------


def test_align_no_width_is_noop(fake_win) -> None:
    """Without `width`, the surface is sized to natural content; LEFT
    and CENTER produce the exact same pixels."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello world"
    s_left = r.render_text(text, color=Color(0, 0, 0), align=TextAlign.LEFT)[1]
    s_center = r.render_text(text, color=Color(0, 0, 0), align=TextAlign.CENTER)[1]
    assert (s_left.get_width(), s_left.get_height()) == (
        s_center.get_width(),
        s_center.get_height(),
    )
    a = pixels_alpha(s_left)
    b = pixels_alpha(s_center)
    assert (a == b).all()
