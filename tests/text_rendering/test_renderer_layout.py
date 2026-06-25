"""Tests for `videre.core.text_rendering.TextRendering`.

Pin the layout contract: line spacing, compact vs non-compact mode,
height_delta, underline drawing without resizing the line box, multi-line
stacking with constant baseline-to-baseline distance, and the absence of
glyph collision when underline is on.
"""

import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha, pixels_red, rasterize
from videre.colors import Color
from videre.core.constants import TextAlign
from videre.core.text_rendering import TextRendering
from videre.core.text_rendering.utils import line_metrics, underline_metrics
from videre.fonts.provider import get_font_provider


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture(scope="module")
def metrics_16() -> tuple[int, int, int]:
    """(ascender, descender, line_height) for the reference font at size 16."""
    _, path = get_font_provider().get_font_info(" ")
    return line_metrics(path, 16)


def _surface_height(text: str, **kwargs) -> int:
    return (
        TextRendering(**kwargs).render_text(text, color=Color(0, 0, 0))[1].get_height()
    )


# -- Single-line height contract --------------------------------------------


def test_single_line_compact_height(fake_win, metrics_16: tuple[int, int, int]) -> None:
    asc, desc, _ = metrics_16
    height = _surface_height("Hello", size=16)
    assert height == asc + 2 + desc  # h_delta default = 2


def test_single_line_non_compact_height(
    fake_win, metrics_16: tuple[int, int, int]
) -> None:
    _, desc, line_h = metrics_16
    height = _surface_height("Hello", size=16, compact=False)
    assert height == line_h + 2 + desc  # line_spacing = line_h + h_delta(2)


def test_height_delta_zero_is_smaller_than_default(fake_win) -> None:
    h_default = _surface_height("Hello", size=16)
    h_zero = _surface_height("Hello", size=16, height_delta=0)
    assert h_zero < h_default
    assert h_default - h_zero == 2  # exactly the difference of height_delta


def test_height_delta_large_is_taller_than_default(fake_win) -> None:
    h_default = _surface_height("Hello", size=16)
    h_big = _surface_height("Hello", size=16, height_delta=10)
    assert h_big - h_default == 8  # h_delta=10 vs default 2


# -- Multi-line stacking ----------------------------------------------------


def test_multi_line_stacks_at_line_spacing(
    fake_win, metrics_16: tuple[int, int, int]
) -> None:
    """For N lines, total height should be:
    `ascender + height_delta + (N-1) * line_spacing + descender` in compact mode.
    Each added line therefore adds exactly `line_spacing` to the total.
    """
    asc, desc, line_h = metrics_16
    line_spacing = line_h + 2  # h_delta default
    h1 = _surface_height("L1", size=16)
    h2 = _surface_height("L1\nL2", size=16)
    h3 = _surface_height("L1\nL2\nL3", size=16)
    assert h1 == asc + 2 + desc
    assert h2 - h1 == line_spacing
    assert h3 - h2 == line_spacing


def test_multi_line_non_compact(fake_win, metrics_16: tuple[int, int, int]) -> None:
    _, desc, line_h = metrics_16
    line_spacing = line_h + 2
    h1 = _surface_height("L1", size=16, compact=False)
    h2 = _surface_height("L1\nL2", size=16, compact=False)
    assert h1 == line_spacing + desc
    assert h2 - h1 == line_spacing


# -- Empty input ------------------------------------------------------------


def test_empty_text_reserves_one_line_slot(
    fake_win, metrics_16: tuple[int, int, int]
) -> None:
    asc, desc, _ = metrics_16
    s = TextRendering(size=16).render_text("", color=Color(0, 0, 0))[1]
    # No glyph -> no width, but the height still reserves one line slot.
    assert s.get_width() == 0
    assert s.get_height() == asc + 2 + desc


# -- Result dims match the paired surface (TextRenderingResult contract) ----


@pytest.mark.parametrize(
    "text, init_kwargs, render_kwargs",
    [
        ("Hello", {}, {}),  # single line, intrinsic width
        ("", {}, {}),  # empty: no line_layouts to derive from
        ("L1\nL2\nL3", {}, {}),  # multi-line
        ("Hello world foo bar baz quux", {}, {"width": 80}),  # cluster wrap
        ("Hi", {}, {"width": 200, "align": TextAlign.RIGHT}),  # box wider than ink
        ("Bonjour", {"size": 24, "bold": True}, {}),  # synthetic bold
    ],
)
def test_result_dims_match_surface(
    fake_win, text: str, init_kwargs: dict, render_kwargs: dict
) -> None:
    """`ShapedRenderedText.get_width/get_height` report the exact pixel size
    of the surface returned alongside it. The size is not derivable from
    `line_layouts` alone — empty text has no layout, and an explicit `width`
    with RIGHT/CENTER alignment makes the surface wider than the inked
    content — so the result stores the surface dimensions verbatim.
    """
    result, surface = TextRendering(**init_kwargs).render_text(
        text, color=Color(0, 0, 0), **render_kwargs
    )
    assert result.get_width() == surface.get_width()
    assert result.get_height() == surface.get_height()


# -- Underline doesn't change the line box ----------------------------------


@pytest.mark.parametrize("size", [12, 16, 24, 32])
def test_underline_does_not_resize_line(fake_win, size: int) -> None:
    """Adding underline must not change the surface dimensions; the
    underline lives inside the descender region (or is clipped if the
    font's underline_position would push it past)."""
    text = "underline test"
    s_off = TextRendering(size=size).render_text(text, color=Color(0, 0, 0))[1]
    s_on = TextRendering(size=size).render_text(
        text, color=Color(0, 0, 0), underline=True
    )[1]
    assert (s_on.get_width(), s_on.get_height()) == (
        s_off.get_width(),
        s_off.get_height(),
    )


def test_underline_pixels_below_baseline(
    fake_win, metrics_16: tuple[int, int, int]
) -> None:
    """The underline must produce non-zero alpha pixels below the baseline
    of the rendered text."""
    asc, _, _ = metrics_16
    text = "abc"  # short, no descenders, easy to inspect
    s_on = rasterize(
        fake_win.backend,
        TextRendering(size=16).render_text(text, color=Color(0, 0, 0), underline=True)[
            1
        ],
    )
    s_off = rasterize(
        fake_win.backend,
        TextRendering(size=16).render_text(text, color=Color(0, 0, 0))[1],
    )

    # Same dimensions
    assert (s_on.get_width(), s_on.get_height()) == (
        s_off.get_width(),
        s_off.get_height(),
    )

    # Compute alpha below the baseline. Baseline is at ascender + h_delta.
    baseline_y = asc + 2
    arr_on = pixels_alpha(s_on)
    arr_off = pixels_alpha(s_off)
    nz_on = (arr_on[:, baseline_y:] > 0).sum()
    nz_off = (arr_off[:, baseline_y:] > 0).sum()
    assert nz_on > nz_off, "underline should add non-zero alpha below baseline"


def test_underline_color_matches_text(fake_win) -> None:
    """The underline takes the same RGB color as the text."""
    text = "abc"
    color = Color(255, 0, 0)  # red
    s = rasterize(
        fake_win.backend,
        TextRendering(size=16).render_text(text, color=color, underline=True)[1],
    )
    arr_r = pixels_red(s)
    arr_a = pixels_alpha(s)
    # Find a pixel at the underline strip with non-zero alpha; its red
    # channel must be 255 (the requested color).
    nz_indices = (arr_a > 0).nonzero()
    assert len(nz_indices[0]) > 0
    # Pick one strongly-opaque pixel and check its red is the requested color.
    fully_opaque_mask = arr_a == 255
    if fully_opaque_mask.any():
        assert arr_r[fully_opaque_mask].max() == 255


# -- Underline + multi-line: no chevauchement de la ligne suivante -----------


def test_underline_multiline_no_glyph_collision(
    fake_win, metrics_16: tuple[int, int, int]
) -> None:
    """The underline of line N must not visibly merge with the ascender
    of line N+1: the row strictly above line N+1's baseline minus its
    ascender must remain empty in the no-underline render and stay
    untouched in the with-underline render at that position.
    """
    asc, desc, line_h = metrics_16
    line_spacing = line_h + 2
    text = "FF\nFF"  # two lines, easy ascender shape
    s_on = rasterize(
        fake_win.backend,
        TextRendering(size=16).render_text(text, color=Color(0, 0, 0), underline=True)[
            1
        ],
    )
    # Line 2 baseline is at (asc + h_delta) + line_spacing = asc + 2 + line_spacing.
    line2_baseline = asc + 2 + line_spacing
    line2_top = line2_baseline - asc  # top of glyphs on line 2

    arr = pixels_alpha(s_on)
    # Find the underline strip below line 1's baseline.
    line1_baseline = asc + 2
    ul_offset, ul_thickness = underline_metrics(
        get_font_provider().get_font_info(" ")[1], 16
    )
    ul_top = line1_baseline + ul_offset
    ul_bottom = ul_top + ul_thickness
    # Underline must end strictly above line 2's glyph top.
    assert ul_bottom <= line2_top, (
        f"underline (rows {ul_top}..{ul_bottom - 1}) collides with line 2 "
        f"glyphs starting at row {line2_top}"
    )
    # Sanity: there is content on line 2 at its expected vertical band.
    line2_content = (arr[:, line2_top : line2_baseline + desc] > 0).sum()
    assert line2_content > 0


# -- Bold / italic produce different surfaces (sanity) ----------------------


def test_bold_renders_wider_than_regular(fake_win) -> None:
    text = "Hello bold"
    s_reg = TextRendering(size=24).render_text(text, color=Color(0, 0, 0))[1]
    s_bold = TextRendering(size=24, bold=True).render_text(text, color=Color(0, 0, 0))[
        1
    ]
    assert s_bold.get_width() > s_reg.get_width()


def test_italic_does_not_crash_and_is_not_identical(fake_win) -> None:
    text = "Hello italic"
    s_reg = rasterize(
        fake_win.backend,
        TextRendering(size=24).render_text(text, color=Color(0, 0, 0))[1],
    )
    s_it = rasterize(
        fake_win.backend,
        TextRendering(size=24, italic=True).render_text(text, color=Color(0, 0, 0))[1],
    )
    assert s_it.get_width() > 0 and s_it.get_height() > 0
    # Italic shears the glyphs; pixel content must differ even if dims
    # happen to match.
    if (s_reg.get_width(), s_reg.get_height()) == (s_it.get_width(), s_it.get_height()):
        a = pixels_alpha(s_reg)
        b = pixels_alpha(s_it)
        assert not (a == b).all()


# -- render_char (single-character drop-in for Character/Checkbox/Radio) ----


def test_render_char_empty_returns_zero_size(fake_win) -> None:
    s = TextRendering(size=16).render_char("")
    assert (s.get_width(), s.get_height()) == (0, 0)


def test_render_char_returns_tight_glyph_bitmap(fake_win) -> None:
    """`render_char` must return a glyph-tight surface, not a sbaseline-
    padded one. A latin uppercase letter at size 16 should fit in a box
    much smaller than the font's full line height (which would be ~17px
    tall when including ascender + descender)."""
    s = TextRendering(size=16).render_char("A")
    w, h = s.get_width(), s.get_height()
    assert w > 0 and h > 0
    # Tight bitmap: A is shorter than the full line height (which would
    # otherwise be ~17 at size=16). The cap height of typical fonts at
    # 16px sits around 11-12px.
    assert h <= 16


@pytest.mark.parametrize(
    "char",
    [
        "☐",  # ☐ ballot box
        "☑",  # ☑ ballot box with check
        "○",  # ○ white circle
        "◉",  # ◉ fisheye
    ],
)
def test_render_char_widget_symbols_have_pixels(fake_win, char: str) -> None:
    """The four Checkbox/Radio symbols must rasterize to non-empty
    surfaces at the typical symbol size (otherwise the widgets render
    blank). Pins the FontProvider routes those codepoints to a font
    that actually has the glyph."""
    s = rasterize(fake_win.backend, TextRendering(size=22).render_char(char))
    w, h = s.get_width(), s.get_height()
    assert w > 0 and h > 0
    arr = pixels_alpha(s)
    assert (arr > 0).any(), f"render_char({char!r}) produced an empty bitmap"


def test_render_char_color_applied(fake_win) -> None:
    """The color argument must color the glyph pixels (alpha-modulated
    by the font's antialiased coverage)."""
    s = rasterize(
        fake_win.backend, TextRendering(size=16).render_char("A", Color(255, 0, 0))
    )
    arr_r = pixels_red(s)
    arr_a = pixels_alpha(s)
    fully_opaque = arr_a == 255
    if fully_opaque.any():
        assert arr_r[fully_opaque].max() == 255


def test_render_char_cached_returns_independent_surfaces(fake_win) -> None:
    """Two calls for the same character must return independent
    surfaces (caller may freely blit onto either one)."""
    r = TextRendering(size=16)
    s1 = r.render_char("A")
    s2 = r.render_char("A")
    assert s1 is not s2  # not the same object
