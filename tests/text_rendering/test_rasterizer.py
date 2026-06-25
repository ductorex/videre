"""Tests for `videre.core.text_rendering.rasterizer.GlyphRasterizer`.

Pins the corner branches of glyph rasterization that the high-level
text tests don't naturally exercise: missing glyphs (id=0), whitespace
glyphs that produce no bitmap, color emoji bitmaps (BGRA pixel mode,
exercised via the `_bgra_to_numpy_array` helper directly since the bundled
fonts are all monochrome), and alpha-modulated text colors.
"""

import numpy as np
import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha, rasterize
from videre.colors import Color
from videre.core.text_rendering import GlyphRasterizer, Shaper, TextRendering
from videre.core.text_rendering.rasterizer import _bgra_to_numpy_array
from videre.fonts.provider import get_font_provider


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


# -- render_single_glyph: missing glyph + whitespace bitmap -----------------


def test_render_single_glyph_id_zero_returns_empty() -> None:
    """`glyph_id=0` is the FreeType convention for "no glyph for this
    codepoint"; rasterizer must short-circuit to an empty `Glyph`
    instead of asking the cache for a nonsense entry."""
    r = GlyphRasterizer()
    _, font_path = get_font_provider().get_font_info(" ")
    s = r.render_single_glyph(font_path, 16, False, False, 0)
    assert s.empty()
    assert s.width == 0 and s.height == 0


def test_render_single_glyph_whitespace_yields_empty() -> None:
    """A whitespace glyph (eg. U+0020 SPACE) has a valid glyph_id but
    no bitmap (width=0). The rasterizer must detect that and return an
    empty `Glyph`, not a 1-pixel garbage one."""
    shaper = Shaper()
    _, path = get_font_provider().get_font_info(" ")
    glyphs = shaper.shape(
        text=" ", font_path=path, size_px=16, script="Latn", right_to_left=False
    )
    assert glyphs and glyphs[0].glyph_id != 0
    r = GlyphRasterizer()
    s = r.render_single_glyph(path, 16, False, False, glyphs[0].glyph_id)
    assert s.empty()
    assert s.width == 0 and s.height == 0


# -- Sub-pixel phase --------------------------------------------------------


def test_render_single_glyph_phase_shifts_bitmap() -> None:
    """Two distinct sub-pixel phases of the same glyph must rasterize to
    different coverage: the outline is shifted by `phase / _SUBPIXEL_PHASES`
    px before rendering, so this proves the `phase` argument reaches
    `_rasterize_glyph` (not just the LIGHT-hint flag that `subpixel` sets)."""
    shaper = Shaper()
    _, path = get_font_provider().get_font_info("A")
    glyphs = shaper.shape(
        text="A", font_path=path, size_px=32, script="Latn", right_to_left=False
    )
    gid = glyphs[0].glyph_id
    r = GlyphRasterizer()
    g0 = r.render_single_glyph(path, 32, False, False, gid, subpixel=True, phase=0)
    g2 = r.render_single_glyph(path, 32, False, False, gid, subpixel=True, phase=2)
    assert not g0.empty() and not g2.empty()
    assert g0.image is not None and g2.image is not None
    differ = g0.image.shape != g2.image.shape or not np.array_equal(g0.image, g2.image)
    assert differ


def test_render_single_glyph_phase_cached_per_phase() -> None:
    """Same `(glyph, phase)` returns the cached instance; different phases are
    distinct cache entries (so a sub-pixel run never reuses a wrong bitmap)."""
    shaper = Shaper()
    _, path = get_font_provider().get_font_info("A")
    gid = shaper.shape(
        text="A", font_path=path, size_px=24, script="Latn", right_to_left=False
    )[0].glyph_id
    r = GlyphRasterizer()
    a = r.render_single_glyph(path, 24, False, False, gid, subpixel=True, phase=1)
    b = r.render_single_glyph(path, 24, False, False, gid, subpixel=True, phase=1)
    assert a is b  # cache hit on identical key
    c = r.render_single_glyph(path, 24, False, False, gid, subpixel=True, phase=3)
    assert c is not a  # different phase -> different entry


# -- Color with explicit alpha ----------------------------------------------


def test_render_text_with_translucent_color(fake_win) -> None:
    """Color = (R, G, B, alpha<255) routes through the alpha-mod
    branch in `_gray_to_numpy_array`. The opaque path multiplies the
    glyph coverage by the requested alpha; output alpha must be
    bounded by the requested alpha."""
    text = "abc"
    _, rendered = TextRendering(size=24).render_text(text, color=Color(255, 0, 0, 128))
    arr_a = pixels_alpha(rasterize(fake_win.backend, rendered))
    # Glyph pixels should never reach full opacity since input alpha
    # was capped at 128.
    assert int(arr_a.max()) <= 128
    # And there must be some opaque-ish ink: alpha non-zero pixels
    # exist.
    assert int(arr_a.max()) > 0


# -- Color emoji (BGRA pixel mode) ------------------------------------------


# -- _bgra_to_numpy_array (color emoji path) ------------------------------------
#
# The bundled FontProvider routes 😀 to `Noto Emoji Regular`, which is
# outline-based (monochrome), so the BGRA branch is not reachable from
# `render_text` with the current font config. We test the helper
# directly with a hand-built premultiplied-BGRA buffer.


def _make_premultiplied_bgra(
    rgba_per_pixel: list[tuple[int, int, int, int]], width: int, rows: int
) -> bytes:
    """Build a tightly-packed (no padding) BGRA buffer with each
    pixel's RGB already premultiplied by alpha — the format
    FreeType emits for color glyphs."""
    out = bytearray(width * rows * 4)
    for i, (r, g, b, a) in enumerate(rgba_per_pixel):
        # Premultiply
        pr = r * a // 255
        pg = g * a // 255
        pb = b * a // 255
        out[i * 4 + 0] = pb  # B
        out[i * 4 + 1] = pg  # G
        out[i * 4 + 2] = pr  # R
        out[i * 4 + 3] = a  # A
    return bytes(out)


def test_bgra_to_numpy_array_unpremultiplies_correctly() -> None:
    """A 2×1 buffer with one fully-opaque red pixel and one
    half-translucent green pixel must un-premultiply back to
    (255, 0, 0, 255) and (0, 255, 0, 128) in the resulting RGBA array."""
    pixels = [(255, 0, 0, 255), (0, 255, 0, 128)]
    width, rows = 2, 1
    pitch = width * 4
    buf = _make_premultiplied_bgra(pixels, width, rows)
    arr = _bgra_to_numpy_array(buf, width, rows, pitch)
    assert arr.shape == (rows, width, 4)
    # Pixel (y=0, x=0): pure red, fully opaque.
    assert int(arr[0, 0, 0]) == 255  # R
    assert int(arr[0, 0, 1]) == 0  # G
    assert int(arr[0, 0, 3]) == 255  # A
    # Pixel (y=0, x=1): pure green at half alpha. Un-premultiplication
    # divides green = 128 by alpha = 128 then multiplies by 255 → 255.
    assert int(arr[0, 1, 1]) == 255  # G
    assert int(arr[0, 1, 3]) == 128  # A


def test_bgra_to_numpy_array_zero_alpha_clears_rgb() -> None:
    """Where alpha is 0 the un-premultiplication divides by max(alpha,
    1) but the helper post-zeros those pixels so transparent regions
    don't leak any color."""
    width, rows = 1, 1
    buf = bytes([200, 100, 50, 0])  # B G R A — alpha=0
    arr = _bgra_to_numpy_array(buf, width, rows, width * 4)
    # RGBA all four channels must be zero.
    assert int(arr[0, 0, 0]) == 0  # R
    assert int(arr[0, 0, 1]) == 0  # G
    assert int(arr[0, 0, 2]) == 0  # B
    assert int(arr[0, 0, 3]) == 0  # A


def test_bgra_to_numpy_array_handles_pitch_padding() -> None:
    """FreeType bitmaps may have `pitch > width * 4` (row padding).
    The helper must slice each row to `width * 4` bytes, ignoring the
    trailing padding."""
    width, rows = 1, 2
    pitch = width * 4 + 8  # 8 bytes of padding per row
    pixels_one_row = bytes([0, 0, 255, 255])  # B G R A — pure red opaque
    padding = bytes([0xFF] * 8)
    buf = pixels_one_row + padding + pixels_one_row + padding
    arr = _bgra_to_numpy_array(buf, width, rows, pitch)
    # Both rows must be pure red (the padding bytes mustn't bleed in).
    assert int(arr[0, 0, 0]) == 255  # y=0, x=0, R
    assert int(arr[1, 0, 0]) == 255  # y=1, x=0, R
    assert int(arr[0, 0, 3]) == 255  # alpha
