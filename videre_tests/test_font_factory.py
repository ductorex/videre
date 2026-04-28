import functools

import pygame
import pygame.image
import pytest

from videre.core.constants import TextAlign
from videre.core.fontfactory.pygame_font_factory import PygameFontFactory
from videre.core.fontfactory.pygame_text_rendering import PygameTextRendering
from videre.core.pygame_drawer_executor import PygameDrawerExecutor


@pytest.mark.parametrize("wrap_words", (False, True))
def test_render_text(wrap_words):
    height_delta = 2
    ff = PygameFontFactory(size=24)
    font = ff.base_font
    line_height = ff.font_height + height_delta
    ascender = abs(font.get_sized_ascender(ff.default_size)) + 1
    descender = abs(font.get_sized_descender(ff.default_size))
    compact_y = ascender + height_delta
    assert line_height == 35
    assert ascender == 27
    assert descender == 8

    tr = PygameTextRendering(ff, height_delta=height_delta)

    _function = functools.partial(tr.render_text, wrap_words=wrap_words)

    def function(*a, **k):
        return _function(*a, **k).drawer

    ff_render_text = functools.partial(function, compact=True)

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

    s = function("a", compact=False)
    assert s.get_width() == 12
    assert s.get_height() == line_height + descender

    s = function("a\na", compact=False)
    assert s.get_width() == 12
    assert s.get_height() == 2 * line_height + descender

    s = function("a\na\na", compact=False)
    assert s.get_width() == 12
    assert s.get_height() == 3 * line_height + descender

    s = function("a\n\na", compact=False)
    assert s.get_width() == 12
    assert s.get_height() == 3 * line_height + descender

    s = function("a\n\na\n\n", compact=False)
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


def _surface_bytes(surface):
    return pygame.image.tobytes(surface, "RGBA")


_PARITY_FACTORY = PygameFontFactory(size=24)
_PARITY_EXECUTOR = PygameDrawerExecutor(_PARITY_FACTORY)

_PARITY_CASES: list[tuple[str, dict, str, dict]] = [
    ("plain_latin", {}, "Hello, world!", {}),
    ("underline_latin", {"underline": True}, "Hello, world!", {}),
    ("underline_strong", {"underline": True, "strong": True}, "Bold underlined.", {}),
    ("underline_italic", {"underline": True, "italic": True}, "Italic underlined.", {}),
    (
        "underline_strong_italic",
        {"underline": True, "strong": True, "italic": True},
        "Bold italic underlined.",
        {},
    ),
    ("multiline", {}, "first line\nsecond line\nthird", {}),
    ("multiline_underline", {"underline": True}, "first\nsecond\nthird", {}),
    ("cjk", {}, "炎炎ノ消防隊", {}),
    ("cjk_underline", {"underline": True}, "炎炎ノ消防隊", {}),
    ("mixed_latin_cjk", {"underline": True}, "Hello 炎炎", {}),
    ("colored", {}, "Colored text", {"color": pygame.Color(255, 0, 0, 255)}),
    (
        "colored_underline",
        {"underline": True},
        "Colored underlined",
        {"color": pygame.Color(0, 128, 0, 255)},
    ),
    ("selection", {}, "Hello, world!", {"selection": (2, 7)}),
    (
        "selection_underline",
        {"underline": True},
        "Hello, world!",
        {"selection": (2, 7)},
    ),
    (
        "wrap_word",
        {},
        "the quick brown fox jumps over the lazy dog",
        {"width": 100, "wrap_words": True},
    ),
    (
        "wrap_word_underline",
        {"underline": True},
        "the quick brown fox jumps over the lazy dog",
        {"width": 100, "wrap_words": True},
    ),
    (
        "wrap_char_underline",
        {"underline": True},
        "the quick brown fox jumps over the lazy dog",
        {"width": 100},
    ),
    (
        "align_center",
        {"underline": True},
        "centered\nlines",
        {"width": 200, "wrap_words": True, "align": TextAlign.CENTER},
    ),
    (
        "align_right",
        {"underline": True},
        "right-aligned\nunderlined",
        {"width": 200, "wrap_words": True, "align": TextAlign.RIGHT},
    ),
    (
        "align_justify",
        {"underline": True},
        "justified text rendering with several words to spread",
        {"width": 200, "wrap_words": True, "align": TextAlign.JUSTIFY},
    ),
    ("empty", {}, "", {}),
    ("empty_underline", {"underline": True}, "", {}),
    ("only_newlines", {}, "\n\n", {}),
    ("only_spaces", {}, "   ", {}),
    ("non_printable", {}, "\v\b\t\r\0", {}),
]


# TODO Each case should instead be checked at the level of pixel.
#      Either by comparing to expected surface saved in image (file regression),
#      or by checking drawer object precisely.
