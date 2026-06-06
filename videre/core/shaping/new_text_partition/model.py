"""
New model for text segmentation.

Should also to produce a partition of logical text containing enough info for next rendering steps:
- harfbuzz algorithm: can run on each text unit
- glyph conversion: can be done for each character in each text unit
- text wrapping: can be done by combining glyph info (from glyph conversion) and gap/text unit info (from partition).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from videre.core.vibidi.vibidi import VibidiText
from videre.fonts.unicode_utils import Character


@dataclass(slots=True, frozen=True)
class TextPartition:
    # Python str, containing text to be rendered.
    text: str
    lines: tuple[Line, ...]


@dataclass(slots=True, frozen=True)
class LineBidi:
    """Per-line bidi context, carried from segmentation down to the L2 reorder.

    `vibidi_text` is the resolved bidi of the WHOLE logical line (levels computed
    with full line context; they stay internal to vibidi). `positions[i]` is the
    original-text index of the i-th character of the filtered line text vibidi
    saw, so a glyph's `logical_position` maps to a vibidi index via the inverse —
    letting the reorder translate between the two coordinate spaces.
    """

    vibidi_text: VibidiText
    positions: tuple[int, ...]

    @property
    def base_is_rtl(self) -> bool:
        return self.vibidi_text.base_is_rtl


@dataclass(slots=True, frozen=True)
class Line:
    """
    Unwrapped line of logical text, with components ordered in logical order (same as in TextPartition.text).
    Empty line is represented with empty component tuple.
    """

    # Line components, in logical order.
    # No sequence of gaps allowed. Only 1 gap between words.
    # We can have gap at start or end of line.
    # We can have sequence of words, e.g. in scripts/languages
    # where "words" are not necessarly separated by spaces.
    components: tuple[TextUnit, ...]
    # Per-line bidi context: vibidi result for the whole line + the
    # original-position mapping. The reorder calls `bidi.vibidi_text.reorder(...)`
    # for real UAX#9 visual order; `base_is_rtl` stays exposed for gap units and
    # callers.
    bidi: LineBidi

    @property
    def base_is_rtl(self) -> bool:
        return self.bidi.base_is_rtl

    def __post_init__(self):
        for i, component in enumerate(self.components):
            if component.is_gap:
                before: TextUnit | None = self.components[i - 1] if i > 0 else None
                after: TextUnit | None = (
                    self.components[i + 1] if i < len(self.components) - 1 else None
                )
                assert before is None or not before.is_gap
                assert after is None or not after.is_gap


@dataclass(slots=True, frozen=True)
class TextUnit:
    """
    Sequence of consecutive characters renderable with 1 single font,
    and not separated by neither spaces nor script/language-speficic word-break rules.
    """

    characters: tuple[LogicalCharacter, ...]
    font_name: str
    font_path: str
    script: str
    # Internal text direction: True if RTL. NB: characters are still in logical order.
    is_rtl: bool
    # True if this unit can be break by character.
    # Used when text is wrapped by words and there's not enough space left on a line to display this unit.
    is_breakable: bool
    # True if all characters in this unit are spaces
    # NB: A gap unit may have a specific rendering. Example: if split by word, a gap with n>1 spaces may be rendered
    # as just 1 space. Or, if text is justified, gap rendered width may be independent of gap space count.
    # Gap rendering could also be optimized, since we just need to render space.
    is_gap: bool


@dataclass(slots=True, frozen=True)
class LogicalCharacter:
    character: Character
    # Logical position of this character in the ORIGINAL, unfiltered text
    # (`TextPartition.text`): `partition.text[logical_position] == character.c`.
    # Tracked across line-terminator normalization (\r\n -> one break) and the
    # unprintable / bidi-control filtering, so positions may be non-contiguous
    # but always point at the real source character (caret / selection slice
    # the source text with these).
    logical_position: int


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


@dataclass(slots=True)
class RenderedTextGlyphMap:
    partition: TextPartition
    # Glyph lines, after text wrap is applied. So, does not necessarily match partition.lines."""
    wrapped_glyph_lines: list[GlyphLine] = field(default_factory=list)
