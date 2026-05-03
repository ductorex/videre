import pytest

from videre.core.fontfactory.pygame_font_factory import PygameFontFactory
from videre.core.fontfactory.pygame_text_rendering import PygameTextRendering


@pytest.mark.parametrize("wrap_words", (False, True))
def test_render_text(wrap_words):
    height_delta = 2
    ff = PygameFontFactory(size=24)
    font = ff.base_font
    line_height = ff.font_height + height_delta
    ascender = abs(font.get_sized_ascender(ff.size)) + 1
    descender = abs(font.get_sized_descender(ff.size))
    compact_y = ascender + height_delta
    assert line_height == 35
    assert ascender == 27
    assert descender == 8

    tr_compact = PygameTextRendering(ff, height_delta=height_delta, compact=True)
    tr_full = PygameTextRendering(ff, height_delta=height_delta, compact=False)

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
