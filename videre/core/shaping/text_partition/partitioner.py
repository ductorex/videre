"""Implementation of `partition_text`: build a `TextPartition` from raw text.

Bidi direction comes from `videre.core.vibidi` (a full UAX#9 implementation,
including rule N0 for paired brackets). UAX#29 word segmentation and Videre's
word profile live in `word_splitter`; UAX#24 script runs and per-character font
routing reuse the helpers in `partition_utils` (font lookup via
`fonts.provider.get_font_provider`). The result is assembled into the
`text_partition.model` types, with three deliberate differences:

- **Explicit gaps.** Inter-word whitespace becomes a gap `TextUnit`
  (`is_gap=True`) carrying the real space characters, instead of a per-word
  whitespace flag. Leading / trailing whitespace is captured too. This gives
  `space_policy` (collapse / preserve) and justification real units to act on.
- **Original-text positions.** Every `LogicalCharacter` keeps its index in the
  ORIGINAL text. Structural and invisible characters are classified as edit
  units rather than filtered, so caret / selection mapping stays exact.
- **Direction, not level.** vibidi resolves the full UAX#9 levels internally
  but exposes only each character's direction (`is_rtl`); units cut on that,
  and only the per-line `base_is_rtl` is kept. Visual reorder is a separate
  downstream step that asks vibidi for the line's resolved L2 order.
"""

from __future__ import annotations

from typing import Iterator

from videre.core.shaping.text_partition.model import (
    Line,
    LineBidi,
    LogicalCharacter,
    TextPartition,
    TextUnit,
)
from videre.core.shaping.text_partition.partition_utils import (
    _shaping_script,
    _split_by_font,
    _split_by_script,
)
from videre.core.shaping.text_partition.word_splitter import (
    GapSpan,
    WordSpan,
    split_word_spans,
)
from videre.core.text_editing import EditUnit, EditUnitKind, segment_edit_units
from videre.core.vibidi.vibidi import vibidi
from videre.fonts.provider import get_font_provider
from videre.fonts.unicode_utils import get_character


def partition_text(text: str) -> TextPartition:
    """Segment `text` into a `TextPartition` ready for shaping / wrapping."""
    edit_units = segment_edit_units(text)
    lines = tuple(
        _partition_line(text, start, end, units, terminator)
        for start, end, units, terminator in _iter_lines(text, edit_units)
    )
    return TextPartition(text=text, edit_units=edit_units, lines=lines)


def _iter_lines(
    text: str, edit_units: tuple[EditUnit, ...]
) -> Iterator[tuple[int, int, tuple[EditUnit, ...], EditUnit | None]]:
    """Yield source ranges + edit units for each author-authored line.

    UAX #29 makes ``\\r\\n`` one editing unit. All Unicode mandatory-break
    controls classified by `segment_edit_units` terminate a line while staying
    represented in the source model.
    """
    start = 0
    line_units: list[EditUnit] = []
    for unit in edit_units:
        if unit.kind is EditUnitKind.LINE_BREAK:
            yield start, unit.source_start, tuple(line_units), unit
            start = unit.source_end
            line_units = []
        else:
            line_units.append(unit)
    yield start, len(text), tuple(line_units), None


def _partition_line(
    source: str,
    start: int,
    end: int,
    edit_units: tuple[EditUnit, ...],
    terminator: EditUnit | None,
) -> Line:
    """Build one `Line` without destructively filtering its source."""
    line_text = source[start:end]
    positions = list(range(start, end))
    unit_by_position = {
        position: unit
        for unit in edit_units
        for position in range(unit.source_start, unit.source_end)
    }

    vibidi_text = vibidi(line_text)
    bidi = LineBidi(vibidi_text, tuple(positions))
    base_is_rtl = vibidi_text.base_is_rtl
    if not line_text:
        return Line(
            components=(),
            edit_units=edit_units,
            source_start=start,
            source_end=end,
            terminator=terminator,
            bidi=bidi,
        )
    is_rtls = [pos.is_rtl for pos in vibidi_text.logical_positions]

    components: list[TextUnit] = []
    for span in split_word_spans(line_text):
        if isinstance(span, GapSpan):
            components.append(
                _gap_unit(
                    line_text[span.start : span.end],
                    positions[span.start : span.end],
                    unit_by_position,
                    base_is_rtl,
                )
            )
            continue
        assert isinstance(span, WordSpan)
        no_break_before = frozenset(
            positions[offset] for offset in span.no_break_before
        )
        components.extend(
            _word_units(
                line_text[span.start : span.end],
                is_rtls[span.start : span.end],
                positions[span.start : span.end],
                unit_by_position,
                is_breakable=not span.atomic,
                break_before=positions[span.start] if span.break_before else None,
                no_break_before=no_break_before,
            )
        )
    return Line(
        components=tuple(components),
        edit_units=edit_units,
        source_start=start,
        source_end=end,
        terminator=terminator,
        bidi=bidi,
    )


def _gap_unit(
    text: str,
    positions: list[int],
    unit_by_position: dict[int, EditUnit],
    base_is_rtl: bool,
) -> TextUnit:
    """An explicit whitespace gap. Inherits the line's base direction (UAX#9
    gives inter-word neutrals the paragraph direction), routes to the font the
    provider picks for its first character, and is never breakable. Keeps the
    real space characters + positions so `space_policy=PRESERVE` can render
    them and caret mapping stays exact."""
    name, path = get_font_provider().get_font_info(text[0])
    return TextUnit(
        characters=tuple(
            LogicalCharacter(get_character(c), p, unit_by_position[p])
            for c, p in zip(text, positions)
        ),
        font_name=name,
        font_path=path,
        script="Zyyy",
        is_rtl=base_is_rtl,
        is_breakable=False,
        can_break_before=False,
        no_break_before=frozenset(),
        is_gap=True,
    )


def _word_units(
    text: str,
    is_rtls: list[bool],
    positions: list[int],
    unit_by_position: dict[int, EditUnit],
    *,
    is_breakable: bool,
    break_before: int | None,
    no_break_before: frozenset[int],
) -> list[TextUnit]:
    """Split one word into TextUnits by (direction, script, font).

    Cuts on direction (each character's `is_rtl`, from vibidi) then script then
    font: HarfBuzz only needs a direction per run, and consecutive code points
    are grouped while they share it. `is_breakable` is the word's `not atomic`,
    propagated to each of its units.
    """
    units: list[TextUnit] = []
    for d_lo, d_hi in _runs(is_rtls):
        is_rtl = is_rtls[d_lo]
        d_text = text[d_lo:d_hi]
        d_pos = positions[d_lo:d_hi]
        s_off = 0
        for script_seg in _split_by_script(d_text):
            s_text = script_seg.text
            s_pos = d_pos[s_off : s_off + len(s_text)]
            f_off = 0
            for per_font in _split_by_font(s_text, script_seg.script):
                f_text = per_font.text
                f_pos = s_pos[f_off : f_off + len(f_text)]
                units.append(
                    TextUnit(
                        characters=tuple(
                            LogicalCharacter(get_character(c), p, unit_by_position[p])
                            for c, p in zip(f_text, f_pos)
                        ),
                        font_name=per_font.font_name,
                        font_path=per_font.font_path,
                        script=_shaping_script(f_text),
                        is_rtl=is_rtl,
                        is_breakable=is_breakable,
                        can_break_before=(
                            break_before is not None and f_pos[0] == break_before
                        ),
                        no_break_before=no_break_before.intersection(f_pos),
                        is_gap=False,
                    )
                )
                f_off += len(f_text)
            s_off += len(s_text)
    return units


def _runs(seq: list) -> Iterator[tuple[int, int]]:
    """Yield ``(lo, hi)`` half-open ranges of maximal runs of equal values."""
    n = len(seq)
    i = 0
    while i < n:
        j = i + 1
        while j < n and seq[j] == seq[i]:
            j += 1
        yield i, j
        i = j
