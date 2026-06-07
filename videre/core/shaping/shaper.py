"""Shape a partition `Line` into glyphs via HarfBuzz, keeping the unit link.

Produces a `ShapedTextLine`: the line's `TextUnit`s in logical order, each
carrying its `PositionedGlyph`s. Within a unit the glyphs are in HarfBuzz
output order (visual left-to-right, so reversed vs logical for an RTL unit);
the units themselves stay in logical order until the L2 reorder (after wrap).

`logical_position` is read straight off the unit's `LogicalCharacter`s via the
HarfBuzz cluster index, so it is correct in both reading directions: for an
RTL unit the clusters decrease but each one still points at the right source
character. Several glyphs sharing a cluster (decomposition) get the same
position; a ligature glyph takes its cluster's first character's position.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from uharfbuzz import Buffer, Face, Font, FontFuncs, ot_font_set_funcs, shape

from videre.core.shaping.glyph_partition import (
    PositionedGlyph,
    ShapedTextLine,
    ShapedUnit,
)
from videre.core.shaping.text_partition.model import Line, TextUnit
from videre.core.shaping.utils import (
    SYNTHETIC_BOLD_STRENGTH,
    SYNTHETIC_SLANT_FACTOR,
    glyph_metrics,
)

# Third element of the `synthetic_bold` tuple. False means HarfBuzz grows
# the glyph advances to absorb the embolden; True would keep the original
# advances and let the thicker strokes overlap their neighbors. We pick
# False so bold text is genuinely wider than regular, like CSS/browsers/Word.
_SYNTHETIC_BOLD_IN_PLACE = False


@lru_cache(maxsize=64)
def _load_face(font_path: str) -> Face:
    # Bounded like `load_freetype_face`: a HarfBuzz `Face` holds the font file
    # bytes and there are ~174 fonts, so cap the resident set (not `@cache`).
    return Face(Path(font_path).read_bytes())


class _FreetypeFontFuncsForHb:
    """Python equivalent of HarfBuzz's `hb_ft_font_set_funcs` (which
    `uharfbuzz` doesn't expose). Plugged into a HB Font, it makes
    HarfBuzz query FreeType for hinted per-glyph advances; an
    OT-funcs sibling Font is reused for cmap-only lookups
    (unicode -> glyph id) so we don't reimplement them.
    """

    __slots__ = ("_hb_default_font", "_font_path", "_size_px")

    def __init__(self, font_path: str, size_px: int) -> None:
        face = _load_face(font_path)
        scale = size_px * 64

        # OT-funcs Font used only for unicode -> glyph_id mapping. We
        # don't query advances on it; this saves us from reimplementing
        # cmap parsing.
        default_font = Font(face)
        default_font.scale = (scale, scale)
        ot_font_set_funcs(default_font)

        self._hb_default_font = default_font
        self._font_path = font_path
        self._size_px = size_px

    def to_font_funcs(self) -> FontFuncs:
        # Bound methods passed below transitively keep `self` alive for
        # as long as the returned FontFuncs is held: uharfbuzz stores
        # them as Python callables. Don't convert them to staticmethods
        # or free functions — that would break the implicit keepalive
        # and crash at shape time on a collected helper.
        funcs = FontFuncs.create()
        funcs.set_glyph_h_advance_func(self._get_h_advance, None)
        funcs.set_nominal_glyph_func(self._nominal_glyph, None)
        funcs.set_variation_glyph_func(self._variation_glyph, None)
        return funcs

    def _get_h_advance(self, _font: Font, glyph_id: int, _user_data: object) -> int:
        # Hinted advance in 26.6 fixed-point, exactly as HarfBuzz expects.
        # Cached per (font, size, glyph): a hit touches no FreeType face, so it
        # also sidesteps the shared-face pixel-size contention this used to
        # guard against.
        return glyph_metrics(self._font_path, self._size_px, glyph_id)[0]

    def _nominal_glyph(self, _font: Font, unicode: int, _user_data: object) -> int:
        return self._hb_default_font.get_nominal_glyph(unicode)

    def _variation_glyph(
        self, _font: Font, unicode: int, variation_selector: int, _user_data: object
    ) -> int:
        return self._hb_default_font.get_variation_glyph(unicode, variation_selector)


@dataclass(slots=True, frozen=True)
class ShapedGlyph:
    """A single glyph as produced by HarfBuzz, with positions in pixels.

    `cluster` is the Python index of the source character in the run's
    source-text string, such that `source_text[g.cluster]`
    yields the source character (or the first one when several codepoints
    collapsed into a single cluster via a ligature or Indic reordering).
    It is NOT a UTF-8 byte index nor a UTF-16 code-unit index; we feed
    HarfBuzz with `Buffer.add_str` which works on Python codepoints.
    When one codepoint produces several glyphs (decomposition), they all
    carry that codepoint's cluster. Clusters are monotonic for LTR runs
    and reversed for RTL runs (HarfBuzz returns glyphs in visual order).
    Use it to find legal break positions: two consecutive glyphs with
    different clusters delimit a cluster boundary safe to wrap on.

    `ink_left` / `ink_right` describe the glyph's bitmap bounding box
    along the x-axis, **in pixels and relative to the glyph's origin**
    (= `pen_x + x_offset` at draw time). They come straight from
    HarfBuzz `font.get_glyph_extents` (`x_bearing` and
    `x_bearing + width` respectively). Most glyphs have
    `ink_right <= x_advance`, but italic letters and a few sidebearing-
    light glyphs (e.g. `f`, `T`, certain punctuation, RTL letters with
    swashes) overhang past the advance — which means the wrap engine
    must compare the cluster's effective right edge to the available
    width, not just the cumulative advance.
    """

    glyph_id: int
    cluster: int
    x_advance: float
    y_advance: float
    x_offset: float
    y_offset: float
    ink_left: float = 0.0
    ink_right: float = 0.0


class Shaper:
    """Thin wrapper over uharfbuzz with a per-(font_path, size_px, bold, italic) Font cache.

    Sizes are in pixels. HarfBuzz needs a scale to map font design units to
    output units; by FreeType convention it expects scale and returns
    positions in 26.6 fixed-point (an integer of 64 = 1 pixel, giving 6 bits
    of sub-pixel precision). So we set `font.scale = (size_px * 64, size_px
    * 64)` and divide each returned advance/offset by 64 to recover float
    pixels.

    Each HarfBuzz Font has custom `FontFuncs` installed: the
    `glyph_h_advance` callback queries FreeType for the *hinted* per-glyph
    advance, while `nominal_glyph` and `variation_glyph` delegate to a
    sibling Font with the standard OpenType funcs (so unicode-to-glyph
    mapping still works). The net effect is the same as HarfBuzz's
    `hb_ft_font_set_funcs` (which isn't exposed by uharfbuzz): HarfBuzz
    returns advances that are pixel-aligned for glyphs in isolation, and
    applies GPOS deltas (kerning, mark positioning) on top — so we keep
    the kerning while having the base advance grid-fit.

    See `_SYNTHETIC_BOLD_IN_PLACE` for the rationale on how synthetic bold
    interacts with advances; we choose to let advances grow with the
    embolden, matching modern toolkits rather than legacy in-place
    behavior.
    """

    __slots__ = ("_fonts", "_funcs_cache")

    def __init__(self) -> None:
        self._fonts: dict[tuple[str, int, bool, bool], Font] = {}
        # Memoized FontFuncs per (font_path, size_px). Each FontFuncs
        # holds bound methods of a `_FreetypeFontFuncsForHb` instance,
        # which transitively keeps that instance and its FreeType face
        # / OT-funcs default Font alive — so caching the FontFuncs
        # alone is enough.
        self._funcs_cache: dict[tuple[str, int], FontFuncs] = {}

    def _get_funcs(self, font_path: str, size_px: int) -> FontFuncs:
        key = (font_path, size_px)
        cached = self._funcs_cache.get(key)
        if cached is not None:
            return cached

        funcs = _FreetypeFontFuncsForHb(font_path, size_px).to_font_funcs()
        self._funcs_cache[key] = funcs
        return funcs

    def _get_font(self, font_path: str, size_px: int, bold: bool, italic: bool) -> Font:
        key = (font_path, size_px, bold, italic)
        font = self._fonts.get(key)
        if font is None:
            face = _load_face(font_path)
            font = Font(face)
            scale = size_px * 64
            font.scale = (scale, scale)
            font.funcs = self._get_funcs(font_path, size_px)
            if bold:
                font.synthetic_bold = (
                    SYNTHETIC_BOLD_STRENGTH,
                    SYNTHETIC_BOLD_STRENGTH,
                    _SYNTHETIC_BOLD_IN_PLACE,
                )
            if italic:
                font.synthetic_slant = SYNTHETIC_SLANT_FACTOR
            self._fonts[key] = font
        return font

    def shape(
        self,
        text: str,
        font_path: str,
        size_px: int,
        script: str,
        right_to_left: bool,
        *,
        bold: bool = False,
        italic: bool = False,
    ) -> tuple[ShapedGlyph, ...]:
        if not text:
            return ()
        font = self._get_font(font_path, size_px, bold, italic)
        buf = Buffer()
        buf.add_str(text)
        buf.script = script
        buf.direction = "rtl" if right_to_left else "ltr"
        shape(font, buf)
        # `pos.x_advance` carries the FreeType-hinted base advance
        # (because our custom `glyph_h_advance_func` calls FT_Load_Glyph)
        # plus the GPOS contextual deltas HarfBuzz layers on top — so
        # kerning is preserved while the base lands on the pixel grid
        # for non-kerned glyphs. Synthetic bold is also already baked in:
        # HarfBuzz applies the embolden growth on top of what our
        # callback returns, via `font.synthetic_bold`.
        #
        # We still query FreeType separately for the bitmap extent
        # (`metr.width`, `metr.horiBearingX`) because the wrap engine
        # needs the actual hinted bitmap edges to detect overflow, and
        # HarfBuzz's `get_glyph_extents` reads the unhinted glyf bbox.
        # The bitmap-side bold compensation mirrors the rasterizer's
        # `FT_Outline_Embolden`, which grows the outline by `strength`
        # on every side (so `+2*strength` total to bitmap width).
        # Italic shear doesn't change the advance — only the bitmap leans
        # — so no compensation needed there.
        bold_bitmap_extra = 2 * SYNTHETIC_BOLD_STRENGTH * size_px if bold else 0.0
        out: list[ShapedGlyph] = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            _, ft_bearing, ft_w = glyph_metrics(font_path, size_px, info.codepoint)
            ft_x_bearing = ft_bearing / 64
            ft_width = ft_w / 64 + bold_bitmap_extra
            out.append(
                ShapedGlyph(
                    glyph_id=info.codepoint,
                    cluster=info.cluster,
                    x_advance=pos.x_advance / 64,
                    y_advance=pos.y_advance / 64,
                    x_offset=pos.x_offset / 64,
                    y_offset=pos.y_offset / 64,
                    ink_left=ft_x_bearing,
                    ink_right=ft_x_bearing + ft_width,
                )
            )
        return tuple(out)


def shape_line(
    line: Line,
    shaper: Shaper,
    size_px: int,
    *,
    bold: bool = False,
    italic: bool = False,
) -> ShapedTextLine:
    """Shape every component of `line` (gaps included) into a `ShapedTextLine`."""
    units = [
        _shape_unit(unit, shaper, size_px, bold=bold, italic=italic)
        for unit in line.components
    ]
    return ShapedTextLine(units=units, bidi=line.bidi)


def _shape_unit(
    unit: TextUnit, shaper: Shaper, size_px: int, *, bold: bool, italic: bool
) -> ShapedUnit:
    text = "".join(lc.character.c for lc in unit.characters)
    shaped = shaper.shape(
        text=text,
        font_path=unit.font_path,
        size_px=size_px,
        script=unit.script,
        right_to_left=unit.is_rtl,
        bold=bold,
        italic=italic,
    )
    glyphs = [
        PositionedGlyph(
            glyph_id=g.glyph_id,
            x_advance=g.x_advance,
            x_offset=g.x_offset,
            y_offset=g.y_offset,
            ink_left=g.ink_left,
            ink_right=g.ink_right,
            font_path=unit.font_path,
            bold=bold,
            italic=italic,
            is_rtl=unit.is_rtl,
            is_gap=unit.is_gap,
            logical_position=unit.characters[g.cluster].logical_position,
        )
        for g in shaped
    ]
    return ShapedUnit(unit=unit, glyphs=glyphs)
