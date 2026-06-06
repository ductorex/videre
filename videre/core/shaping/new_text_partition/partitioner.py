"""Implementation of `partition_text`: build a `TextPartition` from raw text.

Bidi direction comes from `videre.core.vibidi` (a full UAX#9 implementation,
including rule N0 for paired brackets). UAX#29 word segmentation, UAX#24 script
runs and per-character font routing reuse the helpers in `partition_utils`
(font lookup via `fonts.provider.get_font_provider`). The result is assembled
into the new
`new_text_partition.model` types, with three deliberate differences:

- **Explicit gaps.** Inter-word whitespace becomes a gap `TextUnit`
  (`is_gap=True`) carrying the real space characters, instead of the legacy
  `space_before` boolean. Leading / trailing whitespace is captured too. This
  gives `space_policy` (collapse / preserve) and justification real units to
  act on.
- **Original-text positions.** Every `LogicalCharacter` keeps its index in the
  ORIGINAL text, tracked across line-terminator normalization and the
  unprintable / bidi-control filtering, so caret / selection mapping stays
  exact.
- **Direction, not level.** vibidi resolves the full UAX#9 levels internally
  but exposes only each character's direction (`is_rtl`); units cut on that,
  and only the per-line `base_is_rtl` is kept. Any visual reorder is a separate
  downstream step that derives the pseudo-levels it needs from
  `(is_rtl, base_is_rtl)`.
"""

from __future__ import annotations

from typing import Iterator

from videre.core.shaping.new_text_partition.model import (
    Line,
    LineBidi,
    LogicalCharacter,
    TextPartition,
    TextUnit,
)
from videre.core.shaping.new_text_partition.partition_utils import (
    _BIDI_CONTROL_CHARS,
    _shaping_script,
    _split_by_font,
    _split_by_script,
    _split_by_word,
)
from videre.core.vibidi.vibidi import vibidi
from videre.fonts.provider import get_font_provider
from videre.fonts.unicode_utils import Unicode, get_character


def partition_text(text: str) -> TextPartition:
    """Segment `text` into a `TextPartition` ready for shaping / wrapping."""
    lines = tuple(_partition_line(raw, start) for raw, start in _iter_lines(text))
    return TextPartition(text=text, lines=lines)


def _iter_lines(text: str) -> Iterator[tuple[str, int]]:
    """Yield ``(raw_line_text, start_offset)`` for each logical line.

    Recognized terminators: ``\\r\\n``, ``\\r`` alone, ``\\n`` alone (each
    starts a new line; consecutive terminators yield empty lines).
    ``start_offset`` is the index of the line's first character in the
    ORIGINAL `text`, so every kept character maps back to its source position
    even though terminators occupy 1 (``\\n`` / ``\\r``) or 2 (``\\r\\n``) code
    points. Always yields at least one line (matches the legacy
    `_split_by_line`).
    """
    start = 0
    i = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\r":
            yield text[start:i], start
            # \r\n is a single terminator.
            i += 2 if i + 1 < n and text[i + 1] == "\n" else 1
            start = i
        elif c == "\n":
            yield text[start:i], start
            i += 1
            start = i
        else:
            i += 1
    # Trailing segment (also the whole string when there is no terminator, and
    # the empty-input case -> a single empty line).
    yield text[start:n], start


def _partition_line(raw: str, start: int) -> Line:
    """Build one `Line` from a raw line and its start offset in the original."""
    # Filter unprintable + bidi-control characters (UAX#9 X9), keeping each
    # surviving character's ORIGINAL position so `logical_position` indexes
    # `TextPartition.text`, not the filtered string. `positions` runs parallel
    # to `line_text`, exactly like the bidi `levels` below.
    kept = [
        (c, start + i)
        for i, c in enumerate(raw)
        if Unicode.printable(c) and c not in _BIDI_CONTROL_CHARS
    ]
    line_text = "".join(c for c, _ in kept)
    positions = [p for _, p in kept]

    vibidi_text = vibidi(line_text)
    bidi = LineBidi(vibidi_text, tuple(positions))
    base_is_rtl = vibidi_text.base_is_rtl
    if not line_text:
        return Line(components=(), bidi=bidi)
    is_rtls = [pos.is_rtl for pos in vibidi_text.logical_positions]

    components: list[TextUnit] = []
    cursor = 0
    # Words come out in source order and each `word.text` is a literal slice of
    # `line_text`, so a forward `str.find` locates them and the characters in
    # the hole `line_text[cursor:word_start]` are exactly the dropped
    # whitespace -> an explicit gap. This naturally captures leading,
    # inter-word and (after the loop) trailing whitespace.
    for word in _split_by_word(line_text):
        word_start = line_text.find(word.text, cursor)
        assert word_start != -1, (
            f"Cannot locate word {word.text!r} in {line_text!r} from {cursor}"
        )
        if word_start > cursor:
            components.append(
                _gap_unit(
                    line_text[cursor:word_start],
                    positions[cursor:word_start],
                    base_is_rtl,
                )
            )
        word_end = word_start + len(word.text)
        components.extend(
            _word_units(
                word.text,
                is_rtls[word_start:word_end],
                positions[word_start:word_end],
                is_breakable=not word.atomic,
            )
        )
        cursor = word_end
    if cursor < len(line_text):
        components.append(
            _gap_unit(line_text[cursor:], positions[cursor:], base_is_rtl)
        )
    return Line(components=tuple(components), bidi=bidi)


def _gap_unit(text: str, positions: list[int], base_is_rtl: bool) -> TextUnit:
    """An explicit whitespace gap. Inherits the line's base direction (UAX#9
    gives inter-word neutrals the paragraph direction), routes to the font the
    provider picks for its first character, and is never breakable. Keeps the
    real space characters + positions so `space_policy=PRESERVE` can render
    them and caret mapping stays exact."""
    name, path = get_font_provider().get_font_info(text[0])
    return TextUnit(
        characters=tuple(
            LogicalCharacter(get_character(c), p) for c, p in zip(text, positions)
        ),
        font_name=name,
        font_path=path,
        script="Zyyy",
        is_rtl=base_is_rtl,
        is_breakable=False,
        is_gap=True,
    )


def _word_units(
    text: str, is_rtls: list[bool], positions: list[int], *, is_breakable: bool
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
                            LogicalCharacter(get_character(c), p)
                            for c, p in zip(f_text, f_pos)
                        ),
                        font_name=per_font.font_name,
                        font_path=per_font.font_path,
                        script=_shaping_script(f_text),
                        is_rtl=is_rtl,
                        is_breakable=is_breakable,
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
