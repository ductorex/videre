from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TextLine:
    text: str


@dataclass(slots=True, frozen=True)
class TextScript:
    text: str
    script: str  # ISO 15924 code, available from fontTools.unicodedata
    # NB: direction is no longer carried at the script level. UAX#9
    # resolves direction at the codepoint level (the `bidi_level` on
    # `RenderablePiece`), which accounts for context — a Latin digit
    # inside an Arabic run is direction-LTR even though its script is
    # Common, and a neutral like ' / ' between Latin and Arabic gets
    # its direction from the surrounding paragraph context, not its
    # script. Keeping direction on TextScript would conflict with the
    # bidi-driven value upstream.


@dataclass(slots=True, frozen=True)
class BidiRun:
    """A maximal run of consecutive codepoints sharing the same bidi
    embedding level. Produced by `_split_by_level` from a (text,
    per-codepoint levels) pair. Used to slice a Word into segments of
    uniform direction before further per-script / per-font splitting.
    """

    text: str
    level: int


@dataclass(slots=True, frozen=True)
class Word:
    text: str
    atomic: bool
    """
    True when the consumer should keep the whole text on a single line if
    possible: scripts with explicit word separators (Latin, Cyrillic, Arabic,
    Hebrew, etc.) where the segmentation already isolated linguistic words.
    False when the consumer may break between two grapheme clusters within
    the text: runs of CJK ideographs, Hangul syllables, and SE-Asian
    scripts (Thai, Khmer, Lao, Myanmar). The whole run is coalesced into a
    single Word so HarfBuzz receives the full context for shaping (vowel
    positioning, contextual forms, ligatures) and font lookup runs once per
    run; the consumer must call grapheme-cluster segmentation to find legal
    break positions.
    """
    space_before: bool = False
    """
    True when the source had at least one whitespace token immediately
    before this word. Drives the inter-word `space_advance` insertion in
    rendering and wrapping: two adjacent words with no source whitespace
    between them (e.g. `Hello` and `世界` in `"Hello世界"` — UAX#29 word
    boundaries do not require a separator) must render flush. Always False
    on the first Word of a line.
    """


@dataclass(slots=True, frozen=True)
class PerFont:
    text: str
    font_name: str
    font_path: str


@dataclass(slots=True, frozen=True)
class RenderablePiece:
    text: str
    font_name: str
    font_path: str
    script: str
    bidi_level: int = 0
    """UAX#9 resolved embedding level for every codepoint of `text`.
    Even = LTR, odd = RTL. All codepoints of a single piece share the
    same level by construction (the segmentation cuts on level changes
    before script and font)."""

    @property
    def right_to_left(self) -> bool:
        """Derived from the bidi level. Kept as a property so consumers
        (HarfBuzz shaper, glyph layout) can read direction without
        knowing UAX#9 conventions."""
        return self.bidi_level % 2 == 1


@dataclass(slots=True, frozen=True)
class RenderableText:
    atomic: bool
    """
    If False, characters can be dispatched to multiple lines if first line is not wide enough.
    If True and text is split by words, then characters must be rendered in same line if possible.
    If not possible, go to next line. If next whole line is still not enough, word is rendered
    as-is in whole line, and visually truncated by available width.
    """
    pieces: tuple[RenderablePiece, ...]
    space_before: bool = False
    """
    True when the source had whitespace immediately before this element.
    Mirrors `Word.space_before`; the rendering / wrap layers use it to
    insert an inter-word advance only when a real whitespace existed in the
    source. Always False on the first element of a line and always False
    when `split_words=False` (in that mode each line is a single Word and
    whitespace is preserved inside the piece text).
    """


@dataclass(slots=True, frozen=True)
class RenderableLine:
    elements: tuple[RenderableText, ...]
    bidi_base_level: int = 0
    """UAX#9 paragraph base level for the line (0 = LTR, 1 = RTL),
    derived from `_split_by_bidi`. Used by the rendering pipeline to
    apply the L2 visual-reorder rule and to assign a direction to
    inter-word gaps that have no glyph of their own."""

    def is_empty(self) -> bool:
        return not self.elements
