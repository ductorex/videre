from __future__ import annotations

from dataclasses import dataclass, field

from videre.core.text_editing import EditUnit
from videre.core.text_rendering.text_partition.model import LineBidi, TextUnit


@dataclass(slots=True)
class PositionedGlyph:
    """One shaped, positioned glyph, ready to rasterize and blit.

    A `GlyphLine` holds these flat, in **visual** order, with no per-run
    grouping. A single line may mix fonts, scripts and directions, so each
    glyph self-describes: it carries what is needed to rasterize itself
    (`font_path`, `bold`, `italic`) and to map back to the source
    (`is_rtl`, `logical_position`). This is the deliberate inverse of the
    legacy `ShapedRun`/`ShapedGlyph` split — the grouping lives upstream on
    `TextUnit` (the HarfBuzz shaping unit); downstream the glyphs are flat.
    """

    # --- HarfBuzz shaping output: drives layout and width-based wrap ---
    glyph_id: int
    x_advance: float
    x_offset: float
    y_offset: float
    # Ink bounding box on x, relative to the glyph origin: lets the wrap
    # engine reserve room for bitmaps that overhang their advance (italics,
    # swashes, `f` / `T`). Mirrors `ShapedGlyph.ink_left` / `ink_right`.
    ink_left: float
    ink_right: float

    # --- rasterization context (flat list => each glyph self-describes) ---
    # No bitmap stored here: pixels are produced on demand and cached by
    # `GlyphRasterizer.render_single_glyph(font_path, size, bold, italic,
    # glyph_id, color)`, keeping shaping and rasterization decoupled.
    font_path: str
    bold: bool
    italic: bool

    # --- source mapping for caret / selection ---
    # Internal glyph direction (odd bidi level). With a flat list there is no
    # run to carry it, so it sits per glyph: caret helpers use it to know
    # which visual edge (left / right) maps to the glyph's logical start vs end.
    is_rtl: bool
    # True when this glyph belongs to a gap (whitespace) unit. Keeps the flat
    # line self-describing: JUSTIFY widens inter-word gaps and selection can
    # treat them specially without a parallel structure. Gap glyphs stay
    # contiguous after the reorder (it permutes whole units).
    is_gap: bool
    # Logical position of this glyph's source character in `TextPartition.text`.
    # Several glyphs may share one position (one character decomposed into many
    # glyphs); one glyph may span several positions (a ligature, or a collapsed
    # space run), its logical span ending at the next glyph's `logical_position`
    # in logical order. Replaces the old parallel `codepoints` list (no more
    # length coupling).
    logical_position: int
    # Explicit half-open source range of the HarfBuzz cluster. This is not
    # inferred from the next visible glyph: controls may have no ink, and one
    # ligature cluster may span several editing units.
    source_end: int
    # False for source controls that HarfBuzz represents with an invisible
    # placeholder glyph. They still contribute a zero-width layout item.
    paint: bool


@dataclass(slots=True)
class ShapedCluster:
    """One HarfBuzz cluster (a base plus its marks, or a ligature), pre-measured.

    The intended atom of wrap / reorder / caret in the cluster-first model
    (docs/shaping-cluster-model.md): glyphs stay in HarfBuzz output order within
    it. `advance` / `ink_left` / `ink_right` equal `measure_glyphs(glyphs)`,
    computed once here instead of re-derived per wrap. The break block is
    intrinsic (text-only); the wrap combines it with `wrap_words`.
    """

    glyphs: tuple[PositionedGlyph, ...]
    advance: float
    ink_left: float
    ink_right: float
    logical_position: int
    source_end: int
    is_rtl: bool
    is_gap: bool
    paint: bool
    starts_unit: bool
    unit_breakable: bool
    unit_can_break_before: bool
    no_break_before: bool


@dataclass(slots=True)
class ShapedTextLine:
    """One partition `Line` after shaping, BEFORE width-based wrapping.

    Clusters in logical order. `bidi` (the line's vibidi context) rides along
    for the downstream L2 reorder, which calls `bidi.vibidi_text.reorder(...)`
    to get the real UAX#9 visual order.
    """

    bidi: LineBidi
    clusters: list[ShapedCluster] = field(default_factory=list)
    source_start: int = 0
    source_end: int = 0
    terminator: EditUnit | None = None

    @property
    def base_is_rtl(self) -> bool:
        return self.bidi.base_is_rtl


@dataclass(slots=True)
class GlyphLine:
    """One line in **visual** (paint) order, holding its `ShapedCluster`s after
    the UAX#9 L2 reorder. `glyphs` flattens them on demand for the paint / pen
    path; the caret reads the clusters directly (no regrouping).
    """

    clusters: list[ShapedCluster] = field(default_factory=list)
    source_start: int = 0
    source_end: int = 0
    terminator: EditUnit | None = None
    base_is_rtl: bool = False
    _glyphs: list[PositionedGlyph] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def glyphs(self) -> list[PositionedGlyph]:
        """Flat visual-order glyphs, flattened from the clusters once and cached
        (render_text reads this several times per line)."""
        if self._glyphs is None:
            self._glyphs = [g for cluster in self.clusters for g in cluster.glyphs]
        return self._glyphs


@dataclass(slots=True)
class GlyphMeasure:
    """Horizontal geometry of a glyph sequence relative to its pen origin."""

    advance: float
    left: float
    right: float

    @property
    def width(self) -> float:
        return self.right - self.left


def measure_glyphs(glyphs: list[PositionedGlyph]) -> GlyphMeasure:
    """Measure advance and the complete horizontal ink envelope.

    Negative left bearings and terminal overhangs are retained. The logical
    advance interval is included as well, so whitespace and invisible controls
    keep their layout width. Glyph origins use the paint path's rounding.
    """
    pen = 0.0
    real_left = 0.0
    real_right = 0.0
    for g in glyphs:
        origin = int(round(pen + g.x_offset))
        real_left = min(real_left, origin + g.ink_left)
        real_right = max(real_right, origin + g.ink_right)
        pen += g.x_advance
    return GlyphMeasure(pen, min(real_left, 0.0), max(real_right, pen))


def group_clusters(glyphs: list[PositionedGlyph]) -> list[list[PositionedGlyph]]:
    """Group consecutive glyphs sharing one HarfBuzz cluster (same
    `(logical_position, source_end)`): a base plus its marks, or a ligature.
    The smallest chunk safe to wrap on, and the unit the caret measures. Works
    for RTL too (positions decrease, but equal ones stay adjacent)."""
    out: list[list[PositionedGlyph]] = []
    i = 0
    n = len(glyphs)
    while i < n:
        j = i + 1
        lp = glyphs[i].logical_position
        source_end = glyphs[i].source_end
        while (
            j < n
            and glyphs[j].logical_position == lp
            and glyphs[j].source_end == source_end
        ):
            j += 1
        out.append(glyphs[i:j])
        i = j
    return out


def build_clusters(
    glyphs: list[PositionedGlyph], unit: TextUnit
) -> list[ShapedCluster]:
    """Group a shaped unit's glyphs into pre-measured `ShapedCluster`s carrying
    the unit's intrinsic break flags. `starts_unit` marks the first cluster (the
    word-boundary anchor); `no_break_before` is resolved per cluster."""
    clusters: list[ShapedCluster] = []
    for index, group in enumerate(group_clusters(glyphs)):
        measure = measure_glyphs(group)
        first = group[0]
        clusters.append(
            ShapedCluster(
                glyphs=tuple(group),
                advance=measure.advance,
                ink_left=measure.left,
                ink_right=measure.right,
                logical_position=first.logical_position,
                source_end=first.source_end,
                is_rtl=unit.is_rtl,
                is_gap=unit.is_gap,
                paint=any(g.paint for g in group),
                starts_unit=index == 0,
                unit_breakable=unit.is_breakable,
                unit_can_break_before=unit.can_break_before,
                no_break_before=first.logical_position in unit.no_break_before,
            )
        )
    return clusters
