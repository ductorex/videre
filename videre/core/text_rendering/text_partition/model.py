"""
New model for text segmentation.

Should also to produce a partition of logical text containing enough info for next rendering steps:
- harfbuzz algorithm: can run on each text unit
- glyph conversion: can be done for each character in each text unit
- text wrapping: can be done by combining glyph info (from glyph conversion) and gap/text unit info (from partition).
"""

from __future__ import annotations

from dataclasses import dataclass

from videre.core.text_editing import EditUnit
from videre.core.textual.unicode_char import Character
from videre.core.vibidi.vibidi import VibidiText


@dataclass(slots=True)
class TextPartition:
    # Python str, containing text to be rendered.
    text: str
    # Immutable edit view over the complete source. The ranges tile `text`.
    edit_units: tuple[EditUnit, ...]
    lines: tuple[Line, ...]


@dataclass(slots=True)
class LineBidi:
    """Per-line bidi context, carried from segmentation down to the L2 reorder.

    `vibidi_text` is the resolved bidi of the WHOLE logical line (levels computed
    with full line context; they stay internal to vibidi). `positions[i]` is the
    original-text index of the i-th character of the filtered line text vibidi
    saw, so a glyph's `logical_position` maps to a vibidi index via the inverse —
    letting the reorder translate between the two coordinate spaces.
    `orig_to_index` is the inverse of `positions`, built with the `LineBidi`
    value instead of derived later by the reorder step.
    """

    vibidi_text: VibidiText
    positions: tuple[int, ...]
    orig_to_index: dict[int, int]

    @property
    def base_is_rtl(self) -> bool:
        return self.vibidi_text.base_is_rtl


@dataclass(slots=True)
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
    # Edit units belonging to the line content, excluding its terminator.
    edit_units: tuple[EditUnit, ...]
    # Source range occupied by the content (the terminator starts at
    # `source_end`, when present).
    source_start: int
    source_end: int
    # Author-authored line break following this line. It has no glyph but is
    # an editable source unit and later becomes a zero-width layout item.
    terminator: EditUnit | None
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


@dataclass(slots=True)
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
    # Explicit word-wrap opportunity before this unit. This covers boundaries
    # such as the position after a hyphen, even when both neighbouring units
    # are otherwise atomic.
    can_break_before: bool
    # Source positions whose cluster must stay attached to the preceding one.
    # Used for punctuation attached to a breakable run, e.g. `(中文)`.
    no_break_before: frozenset[int]
    # True if all characters in this unit are spaces
    # NB: A gap unit may have a specific rendering. Example: if split by word, a gap with n>1 spaces may be rendered
    # as just 1 space. Or, if text is justified, gap rendered width may be independent of gap space count.
    # Gap rendering could also be optimized, since we just need to render space.
    is_gap: bool


@dataclass(slots=True)
class LogicalCharacter:
    character: Character
    # Logical position of this character in the ORIGINAL, unfiltered text
    # (`TextPartition.text`): `partition.text[logical_position] == character.c`.
    # Tracked across line-terminator normalization (\r\n -> one break) and the
    # unprintable / bidi-control filtering, so positions may be non-contiguous
    # but always point at the real source character (caret / selection slice
    # the source text with these).
    logical_position: int
    # Editing unit containing this code point. Several consecutive logical
    # characters may reference the same unit (combining sequence, emoji ZWJ,
    # ideographic variation sequence, ...).
    edit_unit: EditUnit
