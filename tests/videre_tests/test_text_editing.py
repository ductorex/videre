import pytest

from videre.core.text_editing import (
    EditUnitKind,
    grapheme_boundaries,
    next_edit_unit,
    previous_edit_unit,
    segment_edit_units,
)


@pytest.mark.parametrize(
    ("text", "boundaries"),
    [
        ("", (0,)),
        ("abc", (0, 1, 2, 3)),
        ("e\u0301x", (0, 2, 3)),
        ("\r\nx", (0, 2, 3)),
        ("\u1100\u1161\u11a8", (0, 3)),
        ("\u0915\u094d\u0937", (0, 3)),
        ("\U0001f1e8\U0001f1e6\U0001f1fa", (0, 2, 3)),
        ("\U0001f468\u200d\U0001f469\u200d\U0001f467\u200d\U0001f466", (0, 7)),
        ("\u3402\U000e0100", (0, 2)),
    ],
)
def test_grapheme_boundaries_cover_extended_clusters(
    text: str, boundaries: tuple[int, ...]
) -> None:
    assert grapheme_boundaries(text) == boundaries


def test_edit_units_classify_structural_and_hidden_characters() -> None:
    text = "\t\r\n\v\u200e\u00ad\u200b\u2060\x01\ud800"
    assert [unit.kind for unit in segment_edit_units(text)] == [
        EditUnitKind.TAB,
        EditUnitKind.LINE_BREAK,
        EditUnitKind.LINE_BREAK,
        EditUnitKind.BIDI_CONTROL,
        EditUnitKind.SOFT_HYPHEN,
        EditUnitKind.BREAK_OPPORTUNITY,
        EditUnitKind.NO_BREAK,
        EditUnitKind.HIDDEN_CONTROL,
        EditUnitKind.INVALID,
    ]


def test_join_control_and_variation_selector_stay_with_their_base() -> None:
    text = "\u0646\u200c\u0645\u3402\U000e0100"
    units = segment_edit_units(text)

    assert [(unit.source_start, unit.source_end) for unit in units] == [
        (0, 2),
        (2, 3),
        (3, 5),
    ]
    assert all(unit.kind is EditUnitKind.TEXT for unit in units)


def test_previous_and_next_use_whole_edit_units() -> None:
    units = segment_edit_units("e\u0301x")

    assert previous_edit_unit(units, 2) == units[0]
    assert previous_edit_unit(units, 1) == units[0]
    assert next_edit_unit(units, 0) == units[0]
    assert next_edit_unit(units, 1) == units[0]
    assert next_edit_unit(units, 2) == units[1]
