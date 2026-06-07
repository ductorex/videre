"""Tests for `partition_text` — the new segmentation entry point.

New-model invariants: explicit gaps, original-text logical positions (across
``\\r\\n`` and the unprintable / bidi-control filtering), per-line base
direction, and the no-adjacent-gaps rule.
"""

import pytest

from videre.core.shaping.text_partition.partitioner import partition_text

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


# -- Base direction ----------------------------------------------------------


def test_base_is_rtl_follows_paragraph() -> None:
    assert partition_text("hello").lines[0].base_is_rtl is False
    assert partition_text(ARAB).lines[0].base_is_rtl is True
