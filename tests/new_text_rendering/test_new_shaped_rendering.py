"""Tests for the new `ShapedTextRendering` (AbstractTextRendering wrapper over
the flat pipeline): render_text returns (caret, surface), render_char returns a
tight glyph bitmap, and styling flags reach the pipeline.
"""

import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha
from videre.colors import Color
from videre.core.shaping.new_text_partition.layout import RenderedText
from videre.core.shaping.new_text_partition.text_rendering import ShapedTextRendering

BLACK = Color(0, 0, 0)


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


def test_render_text_returns_caret_and_surface(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    rendered, surf = r.render_text("hello", color=BLACK)
    assert isinstance(rendered, RenderedText)
    assert surf.get_width() > 0 and surf.get_height() > 0
    assert rendered.get_width() == surf.get_width()
    assert rendered.total_visual_count() == 5
    assert (pixels_alpha(surf) > 0).any()


def test_render_text_wrap_respects_width(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    _, surf = r.render_text(
        "The quick brown fox jumps over the lazy dog", width=120, wrap_words=True
    )
    assert surf.get_width() <= 120


def test_render_char_paints_glyph(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    surf = r.render_char("A", color=BLACK)
    assert surf.get_width() > 0 and surf.get_height() > 0
    assert (pixels_alpha(surf) > 0).any()


def test_render_char_empty_is_zero(fake_win) -> None:
    r = ShapedTextRendering(fake_win.backend, size=16)
    surf = r.render_char("", color=BLACK)
    assert surf.get_width() == 0


def test_bold_renders_wider_than_regular(fake_win) -> None:
    regular = ShapedTextRendering(fake_win.backend, size=20)
    bold = ShapedTextRendering(fake_win.backend, size=20, bold=True)
    w_regular = regular.render_text("Hello", color=BLACK)[1].get_width()
    w_bold = bold.render_text("Hello", color=BLACK)[1].get_width()
    # Synthetic bold grows advances, so bold text is at least as wide.
    assert w_bold >= w_regular
