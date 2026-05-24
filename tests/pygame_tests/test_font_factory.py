import pygame
import pygame.freetype
import pytest

from videre.core.pygame_backend.font_factory import PygameFontFactory
from videre.core.pygame_backend.text_rendering import PygameTextRendering
from videre.fonts.font_utils import FontUtils
from videre.fonts.provider import FONT_NOTO_REGULAR, FontProvider

_BASE_FONT_PATH = FontProvider().get_font_info(" ")[1]


@pytest.fixture
def using_pygame_freetype():
    try:
        pygame.freetype.init()
        yield
    finally:
        pygame.freetype.quit()


def test_pygame_font_cache(using_pygame_freetype):
    path = FONT_NOTO_REGULAR.path

    font_s15 = pygame.freetype.Font(path, size=15)

    font_s20 = pygame.freetype.Font(path, size=20)

    font_s15_i = pygame.freetype.Font(path, size=15)
    font_s15_i.oblique = True

    font_s15_b = pygame.freetype.Font(path, size=15)
    font_s15_b.strong = True

    assert font_s15.size == 15
    assert not font_s15.strong
    assert not font_s15.oblique

    assert font_s20.size == 20
    assert not font_s20.strong
    assert not font_s20.oblique

    assert font_s15_i.size == 15
    assert not font_s15_i.strong
    assert font_s15_i.oblique

    assert font_s15_b.size == 15
    assert font_s15_b.strong
    assert not font_s15_b.oblique


@pytest.mark.parametrize("wrap_words", (False, True))
def test_render_text(wrap_words, using_pygame_freetype):
    size = 24
    height_delta = 2
    ff = PygameFontFactory()
    font = ff.get_font(" ")
    line_height = font.get_sized_height(size) + height_delta
    ascender = abs(font.get_sized_ascender(size)) + 1
    descender = abs(font.get_sized_descender(size))
    compact_y = ascender + height_delta
    assert line_height == 35
    assert ascender == 27
    assert descender == 8

    tr_compact = PygameTextRendering(
        ff, size=size, height_delta=height_delta, compact=True
    )
    tr_full = PygameTextRendering(
        ff, size=size, height_delta=height_delta, compact=False
    )

    def ff_render_text(text):
        return tr_compact.render_text(text, wrap_words=wrap_words)[1].surface

    def ff_render_text_full(text):
        return tr_full.render_text(text, wrap_words=wrap_words)[1].surface

    s = ff_render_text("")
    assert s.get_width() == 0
    assert s.get_height() == ascender + height_delta + descender

    s = ff_render_text("\v\b\t\r\0")
    assert s.get_width() == 0
    assert s.get_height() == ascender + height_delta + descender

    s = ff_render_text("\n")
    assert s.get_width() == 0
    assert s.get_height() == 2 * line_height + descender

    s = ff_render_text("\n\n\n")
    assert s.get_width() == 0
    assert s.get_height() == 4 * line_height + descender

    s = ff_render_text_full("a")
    assert s.get_width() == 12
    assert s.get_height() == line_height + descender

    s = ff_render_text_full("a\na")
    assert s.get_width() == 12
    assert s.get_height() == 2 * line_height + descender

    s = ff_render_text_full("a\na\na")
    assert s.get_width() == 12
    assert s.get_height() == 3 * line_height + descender

    s = ff_render_text_full("a\n\na")
    assert s.get_width() == 12
    assert s.get_height() == 3 * line_height + descender

    s = ff_render_text_full("a\n\na\n\n")
    assert s.get_width() == 12
    assert s.get_height() == 5 * line_height + descender

    s = ff_render_text("a")
    assert s.get_width() == 12
    assert s.get_height() == compact_y + descender

    s = ff_render_text("a\na")
    assert s.get_width() == 12
    assert s.get_height() == compact_y + line_height + descender

    s = ff_render_text("a\na\na")
    assert s.get_width() == 12
    assert s.get_height() == compact_y + 2 * line_height + descender

    s = ff_render_text("a\n\na")
    assert s.get_width() == 12
    assert s.get_height() == compact_y + 2 * line_height + descender

    s = ff_render_text("a\na\na\n\n")
    assert s.get_width() == 12
    assert s.get_height() == compact_y + 4 * line_height + descender


def test_font_resolution(using_pygame_freetype):
    font = pygame.freetype.Font(_BASE_FONT_PATH)
    assert font.resolution == 72


@pytest.mark.parametrize("size", [8, 12, 24, 30, 100, 799, 1000])
def test_font_sized_height(size: int, using_pygame_freetype):
    path = _BASE_FONT_PATH
    pygame_size = pygame.freetype.Font(path).get_sized_height(size)
    fonttools_size = FontUtils(path, size).sized_height
    assert fonttools_size is not None
    assert fonttools_size > 0, fonttools_size
    assert pygame_size == fonttools_size, (pygame_size, fonttools_size)
