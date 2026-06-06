from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class TextScript:
    text: str
    script: str  # ISO 15924 code, available from fontTools.unicodedata
    # NB: direction is no longer carried at the script level. UAX#9
    # resolves direction at the codepoint level (the `bidi_level`
    # resolved per piece), which accounts for context — a Latin digit
    # inside an Arabic run is direction-LTR even though its script is
    # Common, and a neutral like ' / ' between Latin and Arabic gets
    # its direction from the surrounding paragraph context, not its
    # script. Keeping direction on TextScript would conflict with the
    # bidi-driven value upstream.


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
