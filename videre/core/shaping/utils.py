from functools import lru_cache

import freetype as ft

# Em fraction added per side to each glyph stroke for synthetic bold.
# Shared between HarfBuzz (`font.synthetic_bold`) and FreeType
# (`FT_Outline_Embolden`) so advances and bitmaps stay aligned. 1/24 em
# is FreeType's default and the de-facto value across Cairo/Pango/Skia.
SYNTHETIC_BOLD_STRENGTH = 1 / 24

# Synthetic italic slant factor: shear applied via HarfBuzz
# (`font.synthetic_slant`) during shaping and via a FreeType 16.16 affine
# transform during rasterization. 0.2 is ~11.3 degrees, the classic
# synthetic italic angle.
SYNTHETIC_SLANT_FACTOR = 0.2

# Extra row reserved above the typographic ascender, applied by both
# `line_metrics` (for layout-time baseline placement) and the rasterizer
# (for line-surface allocation). Some glyphs produce bitmaps whose top
# extends 1 px above the typographic ascender — empirically observed at
# common UI sizes (8, 10, 12, 14) on stacked-diacritic glyphs such as
# U+01D7 (Ǘ): a U with both háček and acute accent stacked above. Without
# this margin the rasterizer's blit lands at y=-1 and the topmost AA row
# of the glyph is silently clipped against the surface boundary, producing
# a slightly harder-edged accent. The legacy `PygameTextRendering` carries
# the same `+ 1` (see `FontSizes.ascender`); keeping them in sync avoids
# drift between the two pipelines on baseline placement.
TOP_GLYPH_MARGIN_PX = 1


@lru_cache(maxsize=64)
def load_freetype_face(font_path: str) -> ft.Face:
    """Cached `freetype.Face` factory shared across the shaping package.

    The rasterizer mutates per-call state (set_pixel_sizes / set_transform /
    load_glyph) while partition_utils only reads the cmap (get_char_index). The
    cmap is immutable once the face is loaded, so the read-only consumer is
    unaffected by mutations made by the rasterizer between two calls.
    """
    return ft.Face(font_path)


@lru_cache(maxsize=128)
def space_advance(font_path: str, size_px: int) -> float:
    """Pixels-space horizontal advance of the U+0020 SPACE glyph.

    Used between consecutive `ShapedWord`s during layout: the shaped
    pipeline (like `pygame_text_rendering`) does not store or render the
    inter-word space as a glyph; instead each word boundary contributes
    a virtual advance equal to this value, computed once on the
    reference font. Falls back to 0.0 if the font has no space glyph.
    """
    face = load_freetype_face(font_path)
    face.set_pixel_sizes(0, size_px)
    glyph_idx = face.get_char_index(0x20)
    if glyph_idx == 0:
        return 0.0
    face.load_glyph(glyph_idx)
    return face.glyph.advance.x / 64.0


@lru_cache(maxsize=128)
def line_metrics(font_path: str, size_px: int) -> tuple[int, int, int]:
    """Pixels-space line metrics: ``(ascender_px, descender_px, line_height_px)``.

    `ascender_px` is the typographic distance above the baseline (positive).
    `descender_px` is the typographic distance below the baseline (positive,
    abs of FreeType's signed value).
    `line_height_px` is the recommended distance between two consecutive
    baselines (typically a bit more than ascender + descender, the surplus
    being the font's internal leading / line gap).

    Mutates the freetype.Face state via `set_pixel_sizes`. Safe to share
    the face with the rasterizer because the result is cached and we
    only read from the size table after setting it.
    """
    face = load_freetype_face(font_path)
    face.set_pixel_sizes(0, size_px)
    ascender = abs(face.size.ascender / 64) + TOP_GLYPH_MARGIN_PX
    descender = abs(face.size.descender / 64)
    height = face.size.height / 64
    return (int(round(ascender)), int(round(descender)), int(round(height)))


@lru_cache(maxsize=128)
def underline_metrics(font_path: str, size_px: int) -> tuple[int, int]:
    """Pixels-space underline metrics: ``(offset_px, thickness_px)``.

    `offset_px` is the distance from the baseline to the **top** of the
    underline stroke, positive = below baseline. `thickness_px` is the
    stroke height, clamped to >= 1.

    `face.underline_thickness` and `face.underline_position` come from the
    TTF `post` table in font units. Per FreeType convention,
    `underline_position` is signed (negative = below baseline) and
    represents the *center* of the stroke; we shift by half the thickness
    to get the top offset that drawing code wants. Falls back to (1, 1)
    when units_per_EM is missing — better than crashing on a malformed
    font.
    """
    face = load_freetype_face(font_path)
    em = face.units_per_EM
    if em <= 0:
        return (1, 1)
    thickness = max(1, int(round(face.underline_thickness * size_px / em)))
    center_below_baseline = -face.underline_position * size_px / em
    top_below_baseline = center_below_baseline - thickness / 2
    return (int(round(top_below_baseline)), thickness)
