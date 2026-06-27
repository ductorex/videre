"""Shape a partition `Line` into glyphs via HarfBuzz, as a flat cluster list.

Produces a `ShapedTextLine`: the line's `ShapedCluster`s in logical order, each
pre-measured and carrying its `PositionedGlyph`s. Within a cluster the glyphs
are in HarfBuzz output order (visual left-to-right, so reversed vs logical for
an RTL cluster); the clusters themselves stay in logical order until the L2
reorder (after wrap).

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
from typing import Iterator

from uharfbuzz import Buffer, Face, Font, FontFuncs, ot_font_set_funcs, shape

from videre.core.text_editing import EditUnitKind
from videre.core.text_rendering.glyph_partition import (
    PositionedGlyph,
    ShapedCluster,
    ShapedTextLine,
    build_clusters,
)
from videre.core.text_rendering.rasterizer import glyph_bitmap_bounds
from videre.core.text_rendering.text_partition.model import (
    Line,
    LogicalCharacter,
    TextUnit,
)
from videre.core.text_rendering.utils import (
    SYNTHETIC_BOLD_STRENGTH,
    SYNTHETIC_SLANT_FACTOR,
    glyph_advance,
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
        return glyph_advance(self._font_path, self._size_px, glyph_id)

    def _nominal_glyph(self, _font: Font, unicode: int, _user_data: object) -> int:
        return self._hb_default_font.get_nominal_glyph(unicode) or 0

    def _variation_glyph(
        self, _font: Font, unicode: int, variation_selector: int, _user_data: object
    ) -> int:
        return (
            self._hb_default_font.get_variation_glyph(unicode, variation_selector) or 0
        )


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

    `ink_left` / `ink_right` describe the glyph's pixel bitmap envelope
    along the x-axis, relative to its origin (`pen_x + x_offset` at draw
    time). They are derived from FreeType's hinted metrics and the same
    synthetic bold/slant transformations as the rasterizer. Most glyphs have
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


@dataclass(slots=True, frozen=True)
class _ShapeRun:
    units: tuple[TextUnit, ...]
    script: str


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
        # The wrap engine needs the exact painted bitmap edges, not HarfBuzz's
        # unhinted outline bbox. `glyph_bitmap_bounds` uses the rasterizer's
        # shared FreeType preparation, including synthetic bold and slant.
        out: list[ShapedGlyph] = []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            ink_left, ink_right = glyph_bitmap_bounds(
                font_path, size_px, bold, italic, info.codepoint
            )
            out.append(
                ShapedGlyph(
                    glyph_id=info.codepoint,
                    cluster=info.cluster,
                    x_advance=pos.x_advance / 64,
                    y_advance=pos.y_advance / 64,
                    x_offset=pos.x_offset / 64,
                    y_offset=pos.y_offset / 64,
                    ink_left=float(ink_left),
                    ink_right=float(ink_right),
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
    """Shape a line into clusters, batching compatible units into HB runs."""
    clusters = [
        cluster
        for run in _shape_runs(line.components)
        for cluster in _shape_run(
            run.units, run.script, shaper, size_px, bold=bold, italic=italic
        )
    ]
    return ShapedTextLine(
        clusters=clusters,
        bidi=line.bidi,
        source_start=line.source_start,
        source_end=line.source_end,
        terminator=line.terminator,
    )


def _shape_runs(units: tuple[TextUnit, ...]) -> Iterator[_ShapeRun]:
    """Yield maximal HarfBuzz-compatible runs.

    `TextUnit` boundaries carry wrap metadata, so they must survive. They do
    not all need their own HB buffer, though: adjacent units with the same font
    and direction can share one buffer when their real text uses the same script.
    Gap units are script-neutral and adopt the surrounding run's script.
    """
    run: list[TextUnit] = []
    run_script: str | None = None
    for unit in units:
        if not run:
            run = [unit]
            run_script = None if unit.is_gap else unit.script
            continue
        joined_script = _joined_run_script(run[0], run_script, unit)
        if joined_script is None:
            yield _ShapeRun(tuple(run), run_script or "Zyyy")
            run = [unit]
            run_script = None if unit.is_gap else unit.script
        else:
            run.append(unit)
            run_script = joined_script
    if run:
        yield _ShapeRun(tuple(run), run_script or "Zyyy")


def _joined_run_script(
    first: TextUnit, current_script: str | None, unit: TextUnit
) -> str | None:
    if first.font_path != unit.font_path or first.is_rtl != unit.is_rtl:
        return None
    if unit.is_gap:
        return current_script
    if current_script is None:
        return unit.script
    return current_script if unit.script == current_script else None


def _shape_run(
    units: tuple[TextUnit, ...],
    script: str,
    shaper: Shaper,
    size_px: int,
    *,
    bold: bool,
    italic: bool,
) -> list[ShapedCluster]:
    if len(units) == 1 and units[0].script == script:
        return _shape_unit(units[0], shaper, size_px, bold=bold, italic=italic)

    characters = [character for unit in units for character in unit.characters]
    text = _shape_text(characters)
    shaped = shaper.shape(
        text=text,
        font_path=units[0].font_path,
        size_px=size_px,
        script=script,
        right_to_left=units[0].is_rtl,
        bold=bold,
        italic=italic,
    )
    if not shaped:
        return []

    unit_by_offset: list[int] = []
    unit_ends: list[int] = []
    offset = 0
    for index, unit in enumerate(units):
        offset += len(unit.characters)
        unit_ends.append(offset)
        unit_by_offset.extend([index] * len(unit.characters))

    cluster_starts = sorted({glyph.cluster for glyph in shaped})
    cluster_ends = {
        cluster: (
            cluster_starts[i + 1] if i + 1 < len(cluster_starts) else len(characters)
        )
        for i, cluster in enumerate(cluster_starts)
    }
    if _has_cross_unit_cluster(cluster_ends, unit_by_offset, unit_ends):
        return [
            cluster
            for unit in units
            for cluster in _shape_unit(unit, shaper, size_px, bold=bold, italic=italic)
        ]

    glyphs_by_unit: list[list[PositionedGlyph]] = [[] for _unit in units]
    for glyph in shaped:
        unit_index = unit_by_offset[glyph.cluster]
        unit = units[unit_index]
        start = glyph.cluster
        end = cluster_ends[start]
        glyphs_by_unit[unit_index].append(
            _positioned_glyph(
                glyph,
                characters[start:end],
                unit,
                bold=bold,
                italic=italic,
                size_px=size_px,
            )
        )

    return [
        cluster
        for unit, glyphs in zip(units, glyphs_by_unit)
        for cluster in build_clusters(glyphs, unit)
    ]


def _shape_text(characters: list[LogicalCharacter]) -> str:
    return "".join(
        "\ufffd"
        if character.edit_unit.kind is EditUnitKind.INVALID
        else character.character.c
        for character in characters
    )


def _has_cross_unit_cluster(
    cluster_ends: dict[int, int], unit_by_offset: list[int], unit_ends: list[int]
) -> bool:
    for start, end in cluster_ends.items():
        unit_index = unit_by_offset[start]
        if end > unit_ends[unit_index]:
            return True
    return False


def _shape_unit(
    unit: TextUnit, shaper: Shaper, size_px: int, *, bold: bool, italic: bool
) -> list[ShapedCluster]:
    text = _shape_text(list(unit.characters))
    shaped = shaper.shape(
        text=text,
        font_path=unit.font_path,
        size_px=size_px,
        script=unit.script,
        right_to_left=unit.is_rtl,
        bold=bold,
        italic=italic,
    )
    cluster_starts = sorted({glyph.cluster for glyph in shaped})
    cluster_ends = {
        cluster: (
            cluster_starts[i + 1]
            if i + 1 < len(cluster_starts)
            else len(unit.characters)
        )
        for i, cluster in enumerate(cluster_starts)
    }
    glyphs: list[PositionedGlyph] = []
    for glyph in shaped:
        characters = unit.characters[glyph.cluster : cluster_ends[glyph.cluster]]
        glyphs.append(
            _positioned_glyph(
                glyph, characters, unit, bold=bold, italic=italic, size_px=size_px
            )
        )
    return build_clusters(glyphs, unit)


def _positioned_glyph(
    glyph: ShapedGlyph,
    characters: tuple[LogicalCharacter, ...] | list[LogicalCharacter],
    unit: TextUnit,
    *,
    bold: bool,
    italic: bool,
    size_px: int,
) -> PositionedGlyph:
    kinds = {character.edit_unit.kind for character in characters}
    paint = bool(kinds & {EditUnitKind.TEXT, EditUnitKind.INVALID})
    is_tab = EditUnitKind.TAB in kinds
    return PositionedGlyph(
        glyph_id=glyph.glyph_id,
        x_advance=(glyph.x_advance if paint else float(size_px) if is_tab else 0.0),
        x_offset=glyph.x_offset if paint else 0.0,
        y_offset=glyph.y_offset if paint else 0.0,
        ink_left=glyph.ink_left if paint else 0.0,
        ink_right=glyph.ink_right if paint else 0.0,
        font_path=unit.font_path,
        bold=bold,
        italic=italic,
        is_rtl=unit.is_rtl,
        is_gap=unit.is_gap,
        logical_position=characters[0].logical_position,
        source_end=max(character.edit_unit.source_end for character in characters),
        paint=paint,
    )
