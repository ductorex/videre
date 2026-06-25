"""Tests for the new `TextRendering` (AbstractTextRendering wrapper over
the flat pipeline): render_text returns (caret, surface), render_char returns a
tight glyph bitmap, and styling flags reach the pipeline.
"""

import numpy as np
import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha, rasterize
from videre.colors import Color
from videre.core.text_rendering.renderer import TextRendering
from videre.core.text_rendering.rendering.layout import RenderedText

BLACK = Color(0, 0, 0)


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


def test_render_text_returns_caret_and_surface(fake_win) -> None:
    r = TextRendering(size=16)
    rendered, surf = r.render_text("hello", color=BLACK)
    surf = rasterize(fake_win.backend, surf)
    assert isinstance(rendered, RenderedText)
    assert surf.get_width() > 0 and surf.get_height() > 0
    assert rendered.get_width() == surf.get_width()
    assert rendered.total_visual_count() == 5
    assert (pixels_alpha(surf) > 0).any()


def test_render_text_wrap_respects_width(fake_win) -> None:
    r = TextRendering(size=16)
    _, surf = r.render_text(
        "The quick brown fox jumps over the lazy dog", width=120, wrap_words=True
    )
    assert surf.get_width() <= 120


def test_render_char_paints_glyph(fake_win) -> None:
    r = TextRendering(size=16)
    surf = rasterize(fake_win.backend, r.render_char("A", color=BLACK))
    assert surf.get_width() > 0 and surf.get_height() > 0
    assert (pixels_alpha(surf) > 0).any()


def test_render_char_empty_is_zero(fake_win) -> None:
    r = TextRendering(size=16)
    surf = r.render_char("", color=BLACK)
    assert surf.get_width() == 0


def test_bold_renders_wider_than_regular(fake_win) -> None:
    regular = TextRendering(size=20)
    bold = TextRendering(size=20, bold=True)
    w_regular = regular.render_text("Hello", color=BLACK)[1].get_width()
    w_bold = bold.render_text("Hello", color=BLACK)[1].get_width()
    # Synthetic bold grows advances, so bold text is at least as wide.
    assert w_bold >= w_regular


# -- Sub-pixel positioning --------------------------------------------------


def test_subpixel_changes_pixels_not_size(fake_win) -> None:
    """Sub-pixel positioning shifts glyph bitmaps within the line but doesn't
    touch advances, so the surface keeps the same size while the painted
    coverage differs from the pixel-aligned render."""
    pixel = TextRendering(size=16, subpixel=False)
    sub = TextRendering(size=16, subpixel=True)
    _, surf_pixel = pixel.render_text("Hello world", color=BLACK)
    _, surf_sub = sub.render_text("Hello world", color=BLACK)
    surf_pixel = rasterize(fake_win.backend, surf_pixel)
    surf_sub = rasterize(fake_win.backend, surf_sub)
    assert surf_sub.get_width() == surf_pixel.get_width()
    assert surf_sub.get_height() == surf_pixel.get_height()
    assert not np.array_equal(pixels_alpha(surf_pixel), pixels_alpha(surf_sub))


def test_subpixel_defaults_off_and_explicit_wins(fake_win) -> None:
    """No `subpixel` argument -> off; an explicit bool is honored. (The old
    VIDERE_USE_SHAPED_SUBPIXEL env flag was removed along with env.py.)"""
    assert TextRendering(size=16)._subpixel is False
    on = TextRendering(size=16, subpixel=True)
    assert on._subpixel is True
    off = TextRendering(size=16, subpixel=False)
    assert off._subpixel is False
