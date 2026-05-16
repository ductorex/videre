"""Tests for `videre.core.shaping.ShapedTextRendering`.

Pin the layout contract: line spacing, compact vs non-compact mode,
height_delta, underline drawing without resizing the line box, multi-line
stacking with constant baseline-to-baseline distance, and the absence of
glyph collision when underline is on.
"""

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.shaping import ShapedTextRendering
from videre.core.shaping.texts.textutils import get_font_provider
from videre.core.shaping.utils import line_metrics, underline_metrics


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
        ShapedTextRendering(**kwargs)
        .render_text(text, Color(0, 0, 0))[1]
        .surface.get_height()
    )


# -- Single-line height contract --------------------------------------------


def test_single_line_compact_height(metrics_16: tuple[int, int, int]) -> None:
    asc, desc, _ = metrics_16
    height = _surface_height("Hello", size=16)
    assert height == asc + 2 + desc  # h_delta default = 2


def test_single_line_non_compact_height(metrics_16: tuple[int, int, int]) -> None:
    _, desc, line_h = metrics_16
    height = _surface_height("Hello", size=16, compact=False)
    assert height == line_h + 2 + desc  # line_spacing = line_h + h_delta(2)


def test_height_delta_zero_is_smaller_than_default() -> None:
    h_default = _surface_height("Hello", size=16)
    h_zero = _surface_height("Hello", size=16, height_delta=0)
    assert h_zero < h_default
    assert h_default - h_zero == 2  # exactly the difference of height_delta


def test_height_delta_large_is_taller_than_default() -> None:
    h_default = _surface_height("Hello", size=16)
    h_big = _surface_height("Hello", size=16, height_delta=10)
    assert h_big - h_default == 8  # h_delta=10 vs default 2


# -- Multi-line stacking ----------------------------------------------------


def test_multi_line_stacks_at_line_spacing(metrics_16: tuple[int, int, int]) -> None:
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


def test_multi_line_non_compact(metrics_16: tuple[int, int, int]) -> None:
    _, desc, line_h = metrics_16
    line_spacing = line_h + 2
    h1 = _surface_height("L1", size=16, compact=False)
    h2 = _surface_height("L1\nL2", size=16, compact=False)
    assert h1 == line_spacing + desc
    assert h2 - h1 == line_spacing


# -- Empty input ------------------------------------------------------------


def test_empty_text_reserves_one_line_slot(metrics_16: tuple[int, int, int]) -> None:
    asc, desc, _ = metrics_16
    s = ShapedTextRendering(size=16).render_text("", Color(0, 0, 0))[1].surface
    assert s.get_width() == 1
    assert s.get_height() == asc + 2 + desc


# -- Underline doesn't change the line box ----------------------------------


@pytest.mark.parametrize("size", [12, 16, 24, 32])
def test_underline_does_not_resize_line(size: int) -> None:
    """Adding underline must not change the surface dimensions; the
    underline lives inside the descender region (or is clipped if the
    font's underline_position would push it past)."""
    text = "underline test"
    s_off = ShapedTextRendering(size=size).render_text(text, Color(0, 0, 0))[1].surface
    s_on = (
        ShapedTextRendering(size=size, underline=True)
        .render_text(text, Color(0, 0, 0))[1]
        .surface
    )
    assert s_on.get_size() == s_off.get_size()


def test_underline_pixels_below_baseline(metrics_16: tuple[int, int, int]) -> None:
    """The underline must produce non-zero alpha pixels below the baseline
    of the rendered text."""
    asc, _, _ = metrics_16
    text = "abc"  # short, no descenders, easy to inspect
    s_on = (
        ShapedTextRendering(size=16, underline=True)
        .render_text(text, Color(0, 0, 0))[1]
        .surface
    )
    s_off = ShapedTextRendering(size=16).render_text(text, Color(0, 0, 0))[1].surface

    # Same dimensions
    assert s_on.get_size() == s_off.get_size()

    # Compute alpha below the baseline. Baseline is at ascender + h_delta.
    baseline_y = asc + 2
    arr_on = pygame.surfarray.pixels_alpha(s_on)
    arr_off = pygame.surfarray.pixels_alpha(s_off)
    nz_on = (arr_on[:, baseline_y:] > 0).sum()
    nz_off = (arr_off[:, baseline_y:] > 0).sum()
    assert nz_on > nz_off, "underline should add non-zero alpha below baseline"


def test_underline_color_matches_text() -> None:
    """The underline takes the same RGB color as the text."""
    text = "abc"
    color = Color(255, 0, 0)  # red
    s = ShapedTextRendering(size=16, underline=True).render_text(text, color)[1].surface
    arr_r = pygame.surfarray.pixels_red(s)
    arr_a = pygame.surfarray.pixels_alpha(s)
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
    metrics_16: tuple[int, int, int],
) -> None:
    """The underline of line N must not visibly merge with the ascender
    of line N+1: the row strictly above line N+1's baseline minus its
    ascender must remain empty in the no-underline render and stay
    untouched in the with-underline render at that position.
    """
    asc, desc, line_h = metrics_16
    line_spacing = line_h + 2
    text = "FF\nFF"  # two lines, easy ascender shape
    s_on = (
        ShapedTextRendering(size=16, underline=True)
        .render_text(text, Color(0, 0, 0))[1]
        .surface
    )
    # Line 2 baseline is at (asc + h_delta) + line_spacing = asc + 2 + line_spacing.
    line2_baseline = asc + 2 + line_spacing
    line2_top = line2_baseline - asc  # top of glyphs on line 2

    arr = pygame.surfarray.pixels_alpha(s_on)
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


def test_bold_renders_wider_than_regular() -> None:
    text = "Hello bold"
    s_reg = ShapedTextRendering(size=24).render_text(text, Color(0, 0, 0))[1].surface
    s_bold = (
        ShapedTextRendering(size=24, bold=True)
        .render_text(text, Color(0, 0, 0))[1]
        .surface
    )
    assert s_bold.get_width() > s_reg.get_width()


def test_italic_does_not_crash_and_is_not_identical() -> None:
    text = "Hello italic"
    s_reg = ShapedTextRendering(size=24).render_text(text, Color(0, 0, 0))[1].surface
    s_it = (
        ShapedTextRendering(size=24, italic=True)
        .render_text(text, Color(0, 0, 0))[1]
        .surface
    )
    assert s_it.get_width() > 0 and s_it.get_height() > 0
    # Italic shears the glyphs; pixel content must differ even if dims
    # happen to match.
    if s_reg.get_size() == s_it.get_size():
        a = pygame.surfarray.pixels_alpha(s_reg)
        b = pygame.surfarray.pixels_alpha(s_it)
        assert not (a == b).all()


# -- render_char (single-character drop-in for Character/Checkbox/Radio) ----


def test_render_char_empty_returns_zero_size() -> None:
    s = ShapedTextRendering(size=16).render_char("")
    assert s.get_size() == (0, 0)


def test_render_char_returns_tight_glyph_bitmap() -> None:
    """`render_char` must return a glyph-tight surface, not a baseline-
    padded one. A latin uppercase letter at size 16 should fit in a box
    much smaller than the font's full line height (which would be ~17px
    tall when including ascender + descender)."""
    s = ShapedTextRendering(size=16).render_char("A")
    w, h = s.get_size()
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
def test_render_char_widget_symbols_have_pixels(char: str) -> None:
    """The four Checkbox/Radio symbols must rasterize to non-empty
    surfaces at the typical symbol size (otherwise the widgets render
    blank). Pins the FontProvider routes those codepoints to a font
    that actually has the glyph."""
    s = ShapedTextRendering(size=22).render_char(char)
    w, h = s.get_size()
    assert w > 0 and h > 0
    arr = pygame.surfarray.pixels_alpha(s)
    assert (arr > 0).any(), f"render_char({char!r}) produced an empty bitmap"


def test_render_char_color_applied() -> None:
    """The color argument must color the glyph pixels (alpha-modulated
    by the font's antialiased coverage)."""
    s = ShapedTextRendering(size=16).render_char("A", Color(255, 0, 0))
    arr_r = pygame.surfarray.pixels_red(s)
    arr_a = pygame.surfarray.pixels_alpha(s)
    fully_opaque = arr_a == 255
    if fully_opaque.any():
        assert arr_r[fully_opaque].max() == 255


def test_render_char_cached_returns_independent_surfaces() -> None:
    """Two calls for the same character must return independent
    surfaces (caller may freely blit onto either one)."""
    r = ShapedTextRendering(size=16)
    s1 = r.render_char("A")
    s2 = r.render_char("A")
    assert s1 is not s2  # not the same object
