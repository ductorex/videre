"""Tests for the flat-model surface render (`new_text_partition.render`).

Sanity checks: a non-empty surface is painted, empty text still reserves one
line slot, an inter-word space widens the surface, wrap grows height and
respects width, and alignment shifts the content.
"""

import numpy as np
import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha
from videre.colors import Color
from videre.core.constants import TextAlign
from videre.core.shaping.new_text_partition.render import render_text
from videre.core.shaping.rasterizer import GlyphRasterizer
from videre.core.shaping.shaper import Shaper

BLACK = Color(0, 0, 0)


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


@pytest.fixture
def rasterizer() -> GlyphRasterizer:
    return GlyphRasterizer()


def _render(text, fake_win, shaper, rasterizer, **kw):
    return render_text(
        text,
        backend=fake_win.backend,
        rasterizer=rasterizer,
        shaper=shaper,
        size=16,
        color=BLACK,
        **kw,
    )[1]


def _content_columns(surface) -> np.ndarray:
    """Indices of surface columns that contain any painted pixel."""
    arr = pixels_alpha(surface)
    return np.flatnonzero((arr > 0).any(axis=1))


# -- Basic rendering ---------------------------------------------------------


def test_paints_a_nonempty_surface(fake_win, shaper, rasterizer) -> None:
    surf = _render("Hello world", fake_win, shaper, rasterizer)
    assert surf.get_width() > 0 and surf.get_height() > 0
    assert (pixels_alpha(surf) > 0).any(), "nothing was painted"


def test_empty_text_one_line_slot(fake_win, shaper, rasterizer) -> None:
    # Empty text still reserves one line slot: same height as a single glyph.
    empty = _render("", fake_win, shaper, rasterizer)
    one_line = _render("x", fake_win, shaper, rasterizer)
    assert empty.get_height() == one_line.get_height()


def test_inter_word_space_widens_surface(fake_win, shaper, rasterizer) -> None:
    with_space = _render("Hello world", fake_win, shaper, rasterizer)
    without = _render("Helloworld", fake_win, shaper, rasterizer)
    assert with_space.get_width() > without.get_width()


# -- Wrapping ----------------------------------------------------------------


def test_wrap_grows_height_and_respects_width(fake_win, shaper, rasterizer) -> None:
    text = "The quick brown fox jumps over the lazy dog"
    natural = _render(text, fake_win, shaper, rasterizer)
    wrapped = _render(text, fake_win, shaper, rasterizer, width=120, wrap_words=True)
    assert wrapped.get_height() > natural.get_height()
    assert wrapped.get_width() <= 120


# -- Alignment ---------------------------------------------------------------


def test_right_align_pushes_content_right(fake_win, shaper, rasterizer) -> None:
    text = "hi"
    left = _render(text, fake_win, shaper, rasterizer, width=200, align=TextAlign.LEFT)
    right = _render(
        text, fake_win, shaper, rasterizer, width=200, align=TextAlign.RIGHT
    )
    # Right-aligned content starts further right than left-aligned content.
    assert _content_columns(right).min() > _content_columns(left).min()


def test_center_align_between_left_and_right(fake_win, shaper, rasterizer) -> None:
    text = "hi"
    left = _render(text, fake_win, shaper, rasterizer, width=200, align=TextAlign.LEFT)
    center = _render(
        text, fake_win, shaper, rasterizer, width=200, align=TextAlign.CENTER
    )
    right = _render(
        text, fake_win, shaper, rasterizer, width=200, align=TextAlign.RIGHT
    )
    lc = _content_columns(left).min()
    cc = _content_columns(center).min()
    rc = _content_columns(right).min()
    assert lc < cc < rc


def test_underline_adds_pixels_below_baseline(fake_win, shaper, rasterizer) -> None:
    plain = _render("hello", fake_win, shaper, rasterizer)
    underlined = _render("hello", fake_win, shaper, rasterizer, underline=True)
    # The underline stroke adds painted pixels, so total ink area grows.
    assert int((pixels_alpha(underlined) > 0).sum()) > int(
        (pixels_alpha(plain) > 0).sum()
    )
