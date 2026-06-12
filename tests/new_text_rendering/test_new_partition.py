"""Tests for `partition_text` — the new segmentation entry point.

New-model invariants: explicit gaps, original-text logical positions (across
``\\r\\n`` and the unprintable / bidi-control filtering), per-line base
direction, and the no-adjacent-gaps rule.
"""

import pytest

from videre.core.shaping.text_partition.partitioner import partition_text
from videre.core.text_editing import EditUnitKind

ARAB = "أبج"  # 3-codepoint Arabic chunk
HEB = "אבג"  # 3-codepoint Hebrew chunk

_SAMPLES = [
    "",
    "hello world",
    "   ",
    "  hi  ",
    "hello\nworld",
    "a\r\nb\rc\nd",
    "Hello世界",  # Hello世界 (UAX#29 break, no whitespace)
    "中 文",  # 中 文 (CJK with a space)
    f"hi {ARAB} bye",
    f"{ARAB} Paris {ARAB}",  # 3 bidi levels
    f"fr : {ARAB} / en",  # neutrals keep paragraph direction
    "ab\U0001f600cd",  # ab😀cd (emoji font routing)
    f"{ARAB}{HEB}",  # two adjacent RTL scripts
]


# -- Explicit gaps -----------------------------------------------------------


def test_inter_word_gap_is_explicit() -> None:
    (line,) = partition_text("hello world").lines
    assert [u.is_gap for u in line.components] == [False, True, False]
    gap = line.components[1]
    assert "".join(lc.character.c for lc in gap.characters) == " "
    assert [lc.logical_position for lc in gap.characters] == [5]
    # A gap inherits the line base direction and is never breakable.
    assert gap.is_rtl is False
    assert gap.is_breakable is False


def test_leading_and_trailing_gaps_are_captured() -> None:
    # The legacy path drops these (only `space_before` survived); the new
    # model keeps them as real gap units so PRESERVE can render them.
    (line,) = partition_text("  hi  ").lines
    assert [u.is_gap for u in line.components] == [True, False, True]
    lead, _word, trail = line.components
    assert [lc.logical_position for lc in lead.characters] == [0, 1]
    assert [lc.logical_position for lc in trail.characters] == [4, 5]


def test_all_whitespace_line_is_one_gap() -> None:
    (line,) = partition_text("   ").lines
    assert len(line.components) == 1
    assert line.components[0].is_gap is True
    assert [lc.logical_position for lc in line.components[0].characters] == [0, 1, 2]


def test_no_adjacent_gaps_invariant() -> None:
    for text in _SAMPLES:
        for line in partition_text(text).lines:
            gaps = [u.is_gap for u in line.components]
            assert not any(a and b for a, b in zip(gaps, gaps[1:])), text


def test_cjk_break_has_no_gap() -> None:
    # "Hello世界": UAX#29 splits between Hello and 世界 with no source
    # whitespace, so there must be NO gap between the two units.
    (line,) = partition_text("Hello世界").lines
    assert all(not u.is_gap for u in line.components)


def test_cjk_variation_selector_stays_in_breakable_run() -> None:
    # U+3402 U+E0100 is a registered Adobe-Japan1 ideographic variation
    # sequence. The selector must stay attached to its base without splitting
    # the surrounding CJK run into separate shaping units.
    text = "\u3402\U000e0100\u6587"
    (line,) = partition_text(text).lines

    assert len(line.components) == 1
    (unit,) = line.components
    assert "".join(lc.character.c for lc in unit.characters) == text
    assert unit.is_breakable is True


# -- Logical positions index the original text ------------------------------


@pytest.mark.parametrize("text", _SAMPLES)
def test_logical_positions_index_original_text(text: str) -> None:
    part = partition_text(text)
    for line in part.lines:
        for unit in line.components:
            for lc in unit.characters:
                assert part.text[lc.logical_position] == lc.character.c


@pytest.mark.parametrize("text", _SAMPLES)
def test_logical_positions_strictly_increase_per_line(text: str) -> None:
    for line in partition_text(text).lines:
        positions = [
            lc.logical_position for u in line.components for lc in u.characters
        ]
        assert positions == sorted(positions)
        assert len(positions) == len(set(positions))


def test_position_tracking_across_crlf() -> None:
    # The second line "b" sits at original index 3 despite the \r\n before it.
    lines = partition_text("a\r\nb").lines
    assert len(lines) == 2
    (b_unit,) = lines[1].components
    assert [lc.logical_position for lc in b_unit.characters] == [3]


def test_lines_keep_explicit_source_ranges_and_terminators() -> None:
    part = partition_text("a\r\nb\vc")
    first, second, last = part.lines
    assert first.terminator is not None
    assert second.terminator is not None

    assert (first.source_start, first.source_end, first.terminator.kind) == (
        0,
        1,
        EditUnitKind.LINE_BREAK,
    )
    assert (second.source_start, second.source_end, second.terminator.kind) == (
        3,
        4,
        EditUnitKind.LINE_BREAK,
    )
    assert (first.terminator.source_start, first.terminator.source_end) == (1, 3)
    assert (last.source_start, last.source_end) == (5, 6)
    assert last.terminator is None


def test_hidden_controls_are_preserved_in_partition_source_order() -> None:
    text = "a\x01\u200eb"
    part = partition_text(text)
    characters = [
        character
        for line in part.lines
        for unit in line.components
        for character in unit.characters
    ]

    assert "".join(character.character.c for character in characters) == text
    assert [character.logical_position for character in characters] == list(
        range(len(text))
    )
    assert [unit.kind for unit in part.edit_units] == [
        EditUnitKind.TEXT,
        EditUnitKind.HIDDEN_CONTROL,
        EditUnitKind.BIDI_CONTROL,
        EditUnitKind.TEXT,
    ]


# -- Base direction ----------------------------------------------------------


def test_base_is_rtl_follows_paragraph() -> None:
    assert partition_text("hello").lines[0].base_is_rtl is False
    assert partition_text(ARAB).lines[0].base_is_rtl is True
