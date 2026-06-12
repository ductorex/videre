"""Glyph rasterizer. Independent from surface rendering backend, only based on freetype."""

from dataclasses import dataclass
from functools import lru_cache

import freetype as ft
import numpy as np
from freetype.raw import FT_Outline_Embolden

from videre.colors import Color, Colors
from videre.core.shaping.utils import (
    SYNTHETIC_BOLD_STRENGTH,
    SYNTHETIC_SLANT_FACTOR,
    load_freetype_face,
)

_FT_FIXED_16_16 = 0x10000  # 1.0 in 16.16 fixed-point

# freetype-py exposes these constants only at runtime via dynamic re-exports
# from C bindings, so ty cannot resolve them as module attributes. The
# numeric values are stable across FreeType versions (see freetype/ftimage.h
# and freetype/freetype.h: FT_LOAD_DEFAULT == 0, FT_RENDER_MODE_NORMAL == 0,
# FT_LOAD_COLOR == 0x00100000). FT_PIXEL_MODE_GRAY == 2 is the standard
# 8-bit alpha mask; FT_PIXEL_MODE_BGRA == 7 is the premultiplied 32-bit
# format used by CBDT color emoji tables.
_FT_LOAD_DEFAULT = 0
_FT_LOAD_COLOR = 0x00100000
_FT_RENDER_MODE_NORMAL = 0
_FT_PIXEL_MODE_GRAY = 2
_FT_PIXEL_MODE_BGRA = 7
# FT_GLYPH_FORMAT_OUTLINE == FT_IMAGE_TAG('o','u','t','l'), 4-char tag.
_FT_GLYPH_FORMAT_OUTLINE = 0x6F75746C
# FT_LOAD_TARGET_LIGHT (1 << 16) selects the "light" auto-hinter target:
# full grayscale antialiasing with vertical hinting only, leaving the
# horizontal contour positions intact. We use it in sub-pixel mode so
# the `set_transform` sub-pixel delta we apply before rasterization
# isn't snapped back to the pixel grid by horizontal hinting.
_FT_LOAD_TARGET_LIGHT = 1 << 16

# Number of horizontal sub-pixel phases used when sub-pixel positioning
# is enabled. Each phase is `1 / _SUBPIXEL_PHASES` px wide, so the
# pre-rasterized bitmaps span offsets {0.00, 0.25, 0.50, 0.75} for the
# default value of 4. The cache grows by this factor when sub-pixel is
# on; a multiple of 4 keeps the bucket arithmetic exact in binary.
_SUBPIXEL_PHASES = 4


def subpixel_split(origin_x: float, subpixel: bool) -> tuple[int, int]:
    """Split a float pen origin into an integer pixel x and a phase index.

    Pixel mode: round to the nearest pixel, phase 0. Sub-pixel mode: quantize
    `origin_x * _SUBPIXEL_PHASES` to an int, then split into an integer pixel
    and a phase in `[0, _SUBPIXEL_PHASES)`; a fraction near 1.0 rolls over into
    the next pixel with phase 0, which is exactly the canonical pixel-aligned
    variant. Used by the flat pipeline's `_paint_line` to place each glyph.
    """
    if subpixel:
        q = int(round(origin_x * _SUBPIXEL_PHASES))
        return q // _SUBPIXEL_PHASES, q % _SUBPIXEL_PHASES
    return int(round(origin_x)), 0


def _italic_transform() -> tuple[ft.Matrix, ft.Vector]:
    matrix = ft.Matrix(
        _FT_FIXED_16_16,
        int(SYNTHETIC_SLANT_FACTOR * _FT_FIXED_16_16),
        0,
        _FT_FIXED_16_16,
    )
    return matrix, ft.Vector(0, 0)


def _identity_transform() -> tuple[ft.Matrix, ft.Vector]:
    return ft.Matrix(_FT_FIXED_16_16, 0, 0, _FT_FIXED_16_16), ft.Vector(0, 0)


@dataclass(slots=True, frozen=True)
class Glyph:
    image: np.ndarray | None
    width: int
    height: int
    bitmap_left: int
    bitmap_top: int

    def empty(self) -> bool:
        return self.image is None


_GLYPH_ZERO = Glyph(None, 0, 0, 0, 0)


class GlyphRasterizer:
    """Rasterize HarfBuzz glyph IDs to Glyph objects via freetype-py.

    Each colored bitmap is rendered once and cached by
    `(font_path, size_px, bold, italic, glyph_id, color)`. Bold is applied
    by emboldening the glyph outline before rasterization (so the bitmap
    grows in both directions); italic is applied by setting an affine
    transform on the face before loading the glyph. Both effects mirror
    the synthetic bold/slant configured on the HarfBuzz `Shaper`, so the
    advances computed during shaping align with the bitmap dimensions
    produced here. Canonical bitmap bounds are cached separately without
    retaining their temporary pixel buffer.
    """

    __slots__ = ("_glyph_cache",)

    def __init__(self) -> None:
        self._glyph_cache: dict[tuple, Glyph] = {}

    def render_single_glyph(
        self,
        font_path: str,
        size_px: int,
        bold: bool,
        italic: bool,
        glyph_id: int,
        color: Color = Colors.black,
        *,
        subpixel: bool = False,
        phase: int = 0,
    ) -> Glyph:
        """Rasterize a single glyph to a `Glyph`.

        Produces only the glyph bitmap, no advance padding, no
        baseline-relative offset. Empty inputs (id 0, whitespace,
        missing glyph, unsupported pixel format) yield a `Glyph` for
        which `empty()` is True. The returned `Glyph` is the cached
        instance; it is frozen and its underlying numpy buffer must be
        treated as read-only.

        `subpixel` / `phase` select a horizontally shifted bitmap for
        sub-pixel positioning: the caller computes them with
        `subpixel_split(origin_x, subpixel)` and blits at the returned
        integer pixel. With the defaults (`subpixel=False, phase=0`) the
        bitmap is the canonical pixel-aligned, full-hinted one.
        """
        if glyph_id == 0:
            return _GLYPH_ZERO
        return self._get_glyph(
            font_path, size_px, bold, italic, glyph_id, color, subpixel, phase
        )

    def _get_glyph(
        self,
        font_path: str,
        size_px: int,
        bold: bool,
        italic: bool,
        glyph_id: int,
        rgba: Color,
        subpixel: bool = False,
        phase: int = 0,
    ) -> "Glyph":
        # `subpixel` belongs in the cache key because LIGHT vs full
        # hinting produce visibly different bitmaps even at phase 0,
        # so a sub-pixel run and a pixel-aligned run sharing the same
        # glyph id must not reuse each other's bitmap.
        key = (font_path, size_px, bold, italic, glyph_id, rgba, subpixel, phase)
        sprite = self._glyph_cache.get(key)
        if sprite is None:
            sprite = _rasterize_glyph(
                font_path, size_px, bold, italic, glyph_id, rgba, subpixel, phase
            )
            self._glyph_cache[key] = sprite
        return sprite


def _rasterize_glyph(
    font_path: str,
    size_px: int,
    bold: bool,
    italic: bool,
    glyph_id: int,
    rgba: Color,
    subpixel: bool,
    phase: int,
) -> Glyph:
    slot = _render_glyph_slot(
        font_path, size_px, bold, italic, glyph_id, subpixel, phase
    )
    bitmap = slot.bitmap
    bitmap_left = slot.bitmap_left
    bitmap_top = slot.bitmap_top
    width, rows, pitch = bitmap.width, bitmap.rows, bitmap.pitch
    pixel_mode = bitmap.pixel_mode

    if width == 0 or rows == 0:
        image = None
    elif pixel_mode == _FT_PIXEL_MODE_BGRA:
        image = _bgra_to_numpy_array(bytes(bitmap.buffer), width, rows, pitch)
    elif pixel_mode == _FT_PIXEL_MODE_GRAY:
        image = _gray_to_numpy_array(bytes(bitmap.buffer), width, rows, pitch, rgba)
    else:
        # Other formats (FT_PIXEL_MODE_MONO, _LCD, etc.) are rare for our
        # use case; skip them rather than risk a wrong conversion.
        image = None

    if image is None:
        return Glyph(None, 0, 0, bitmap_left, bitmap_top)
    return Glyph(image, width, rows, bitmap_left, bitmap_top)


@lru_cache(maxsize=16384)
def glyph_bitmap_bounds(
    font_path: str, size_px: int, bold: bool, italic: bool, glyph_id: int
) -> tuple[int, int]:
    """Exact canonical bitmap bounds `(left, right)` used by the rasterizer."""
    if glyph_id == 0:
        return (0, 0)
    slot = _render_glyph_slot(
        font_path, size_px, bold, italic, glyph_id, subpixel=False, phase=0
    )
    return (slot.bitmap_left, slot.bitmap_left + slot.bitmap.width)


def _render_glyph_slot(
    font_path: str,
    size_px: int,
    bold: bool,
    italic: bool,
    glyph_id: int,
    subpixel: bool,
    phase: int,
):
    """Load, transform, embolden and rasterize one FreeType glyph slot."""
    face = load_freetype_face(font_path)
    face.set_pixel_sizes(0, size_px)
    matrix, delta = _italic_transform() if italic else _identity_transform()
    if subpixel:
        # Shift the outline by `phase / _SUBPIXEL_PHASES` px before
        # rasterization. The delta is in 26.6 fixed-point (64 = 1 px),
        # so a phase of 1 = 0.25 px = 16 fixed-point units. With
        # `_FT_LOAD_TARGET_LIGHT` below, horizontal hinting is disabled
        # so the contour keeps its sub-pixel x-position; otherwise the
        # full hinter would snap it back to the integer pixel grid and
        # the four cached variants would all look identical.
        delta = ft.Vector(phase * (64 // _SUBPIXEL_PHASES), delta.y)
    face.set_transform(matrix, delta)
    # FT_LOAD_COLOR makes FreeType return color bitmaps (CBDT/sbix) when the
    # face has them, so emoji glyphs are rasterized in their native colors
    # instead of yielding an empty alpha-only mask.
    load_flags = _FT_LOAD_DEFAULT | _FT_LOAD_COLOR
    if subpixel:
        load_flags |= _FT_LOAD_TARGET_LIGHT
    face.load_glyph(glyph_id, load_flags)

    if bold:
        # freetype-py has no Python wrapper for embolden: like most mutator
        # ops, it lives in `freetype.raw` as a raw ctypes binding and
        # expects the underlying C struct pointer, exposed on each wrapper
        # via the conventional `_FT_<Name>` attribute (see e.g.
        # `Outline.__init__`, which stores its argument as `self._FT_Outline`).
        # We use FT_Outline_Embolden rather than the convenience
        # FT_GlyphSlot_Embolden because the latter applies a fixed ~1/24 em
        # strength, which would desynchronize advances (set by HarfBuzz to
        # SYNTHETIC_BOLD_STRENGTH) from bitmaps (set here). The strength
        # argument is in 26.6 fixed-point at the current pixel size.
        # Color bitmap glyphs reach the rasterizer pre-rendered, so we skip
        # embolden on them.
        if face.glyph.format == _FT_GLYPH_FORMAT_OUTLINE:
            strength = int(size_px * 64 * SYNTHETIC_BOLD_STRENGTH)
            FT_Outline_Embolden(face.glyph.outline._FT_Outline, strength)

    face.glyph.render(_FT_RENDER_MODE_NORMAL)
    return face.glyph


def _gray_to_numpy_array(
    buffer: bytes, width: int, rows: int, pitch: int, rgba: Color
) -> np.ndarray:
    raw = np.frombuffer(buffer, dtype=np.uint8)
    alpha = raw.reshape((rows, pitch))[:, :width]
    rgba_arr = np.empty((rows, width, 4), dtype=np.uint8)
    rgba_arr[..., 0] = rgba.r
    rgba_arr[..., 1] = rgba.g
    rgba_arr[..., 2] = rgba.b
    if rgba.a == 255:
        rgba_arr[..., 3] = alpha
    else:
        rgba_arr[..., 3] = (alpha.astype(np.uint16) * rgba.a // 255).astype(np.uint8)
    return rgba_arr


def _bgra_to_numpy_array(
    buffer: bytes, width: int, rows: int, pitch: int
) -> np.ndarray:
    """Convert a FreeType BGRA bitmap (premultiplied alpha) to a numpy
    RGBA image with non-premultiplied alpha. The user-supplied color is
    ignored for color glyphs - the bitmap carries its own colors.
    """
    raw = np.frombuffer(buffer, dtype=np.uint8)
    bgra = raw.reshape((rows, pitch))[:, : width * 4].reshape((rows, width, 4))
    alpha = bgra[..., 3]
    safe_alpha = np.maximum(alpha, 1).astype(np.uint16)
    rgba_arr = np.empty((rows, width, 4), dtype=np.uint8)
    # Un-premultiply RGB and reorder BGRA -> RGBA. Where alpha is 0, force
    # RGB to 0 so the pixel is fully transparent without color leakage.
    rgba_arr[..., 0] = np.minimum(
        bgra[..., 2].astype(np.uint16) * 255 // safe_alpha, 255
    ).astype(np.uint8)
    rgba_arr[..., 1] = np.minimum(
        bgra[..., 1].astype(np.uint16) * 255 // safe_alpha, 255
    ).astype(np.uint8)
    rgba_arr[..., 2] = np.minimum(
        bgra[..., 0].astype(np.uint16) * 255 // safe_alpha, 255
    ).astype(np.uint8)
    rgba_arr[..., 3] = alpha
    rgba_arr[alpha == 0] = 0
    return rgba_arr
