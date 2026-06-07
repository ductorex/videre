"""
New model for text segmentation.

Should also to produce a partition of logical text containing enough info for next rendering steps:
- harfbuzz algorithm: can run on each text unit
- glyph conversion: can be done for each character in each text unit
- text wrapping: can be done by combining glyph info (from glyph conversion) and gap/text unit info (from partition).
"""

from __future__ import annotations

from dataclasses import dataclass

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
