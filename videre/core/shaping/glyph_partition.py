from __future__ import annotations

from dataclasses import dataclass, field

from videre.core.shaping.text_partition.model import LineBidi, TextUnit
from videre.core.text_editing import EditUnit


@dataclass(slots=True, frozen=True)
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
class ShapedUnit:
    """A `TextUnit` after HarfBuzz shaping, kept in logical order on the line.

    The glyphs are in HarfBuzz output order: visual *within* the unit
    (left-to-right in pixels, hence reversed vs logical order for an RTL
    unit, with decreasing clusters), but the units themselves stay in
    logical order until the L2 reorder runs (after wrap). The source `unit`
    is kept so the wrap engine reads `is_gap` / `is_breakable` / `is_rtl`
    without re-deriving them.
    """

    unit: TextUnit
    glyphs: list[PositionedGlyph] = field(default_factory=list)


@dataclass(slots=True)
class ShapedTextLine:
    """One partition `Line` after shaping, BEFORE width-based wrapping.

    Units in logical order. `bidi` (the line's vibidi context) rides along for
    the downstream L2 reorder, which calls `bidi.vibidi_text.reorder(...)` to get
    the real UAX#9 visual order.
    """

    bidi: LineBidi
    units: list[ShapedUnit] = field(default_factory=list)
    edit_units: tuple[EditUnit, ...] = ()
    source_start: int = 0
    source_end: int = 0
    terminator: EditUnit | None = None

    @property
    def base_is_rtl(self) -> bool:
        return self.bidi.base_is_rtl


@dataclass(slots=True)
class GlyphLine:
    """One line of shaped glyphs in **visual** (paint) order.

    The only place in this module where data is stored visually (after the
    UAX#9 L2 reorder applied when building it from a logical `Line`). Flat by
    design — see `PositionedGlyph`.
    """

    glyphs: list[PositionedGlyph] = field(default_factory=list)
    edit_units: tuple[EditUnit, ...] = ()
    source_start: int = 0
    source_end: int = 0
    terminator: EditUnit | None = None
    base_is_rtl: bool = False


@dataclass(slots=True, frozen=True)
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
