from dataclasses import dataclass
from enum import StrEnum, auto, unique

from videre.fonts.unicode_utils import Character, get_character


@dataclass(slots=True, frozen=True)
class DirectedCharacter:
    character: Character
    logical_position: int
    level: int


@dataclass(slots=True, frozen=True)
class DirectedSegment:
    directed_characters: tuple[DirectedCharacter, ...]
    segment_level: int

    @property
    def is_reversed(self) -> bool:
        return self.directed_characters[0].level < 0


@unique
class CharClass(StrEnum):
    LEFT_TO_RIGHT = auto()
    RIGHT_TO_LEFT = auto()
    NUMBER = auto()
    NEUTRAL = auto()


def _char_type_to_level(ct: CharClass) -> int:
    assert ct not in (CharClass.NEUTRAL, CharClass.NUMBER)
    return -1 if ct == CharClass.RIGHT_TO_LEFT else 1


def compute_directed_segments(
    text: str, base_is_rtl: bool = False
) -> list[DirectedSegment]:
    base_type = CharClass.RIGHT_TO_LEFT if base_is_rtl else CharClass.LEFT_TO_RIGHT

    characters: list[Character] = []
    char_types: list[CharClass] = []
    for c in text:
        ch = get_character(c)
        if ch.is_european_number or ch.is_arabic_number:
            cls = CharClass.NUMBER
        elif ch.script_is_neutral:
            cls = CharClass.NEUTRAL
        else:
            cls = (
                CharClass.RIGHT_TO_LEFT if ch.script_is_rtl else CharClass.LEFT_TO_RIGHT
            )
        characters.append(ch)
        char_types.append(cls)

    cls_runs: list[list[tuple[int, CharClass]]] = []
    cls_run: list[tuple[int, CharClass]] = []
    for i, cls in enumerate(char_types):
        if cls_run and cls_run[-1][1] != cls:
            cls_runs.append(cls_run)
            cls_run = []
        cls_run.append((i, cls))
    if cls_run:
        cls_runs.append(cls_run)

    # Get previous directions (ignoring neutral runs) for number runs.
    prev_solved_ones: list[CharClass | None] = []
    curr_prev_cls = None
    for run in cls_runs:
        run_type = run[0][1]
        if run_type == CharClass.LEFT_TO_RIGHT or run_type == CharClass.RIGHT_TO_LEFT:
            curr_prev_cls = run_type
            prev_solved_ones.append(None)
        elif run_type == CharClass.NEUTRAL:
            prev_solved_ones.append(None)
        else:
            prev_solved_ones.append(curr_prev_cls)

    # Get next directions (ignoring neutral runs) for number runs.
    next_solved_ones: list[CharClass | None] = []
    curr_next_cls = None
    for run in reversed(cls_runs):
        run_type = run[0][1]
        if run_type == CharClass.LEFT_TO_RIGHT or run_type == CharClass.RIGHT_TO_LEFT:
            curr_next_cls = run_type
            next_solved_ones.append(None)
        elif run_type == CharClass.NEUTRAL:
            next_solved_ones.append(None)
        else:
            next_solved_ones.append(curr_next_cls)
    next_solved_ones.reverse()

    run_seg_levels: list[CharClass | None] = []
    run_char_levels: list[CharClass | None] = []

    # Infer segment and character levels for solved and number runs.
    for index_run, run in enumerate(cls_runs):
        run_type = run[0][1]
        if run_type == CharClass.LEFT_TO_RIGHT or run_type == CharClass.RIGHT_TO_LEFT:
            run_seg_levels.append(run_type)
            run_char_levels.append(run_type)
        elif run_type == CharClass.NUMBER:
            is_full_arabic_number = all(
                characters[logical_pos].is_arabic_number for logical_pos, _ in run
            )

            prev_type = prev_solved_ones[index_run] or base_type
            next_type = next_solved_ones[index_run] or base_type

            if base_type == CharClass.LEFT_TO_RIGHT:
                if is_full_arabic_number:
                    number_level = CharClass.RIGHT_TO_LEFT
                else:
                    if prev_type == next_type:
                        number_level = prev_type
                    elif prev_type == CharClass.LEFT_TO_RIGHT:
                        # next_type should be RTL (LTR -> number -> RTL).
                        # Solve as previous type (LTR).
                        number_level = prev_type
                    else:
                        # next_type should be LTR (RTL -> number -> LTR).
                        # Solve as previous type (RTL).
                        number_level = prev_type
                    # NB: Seems number_level is always prev_type when base_type is LTR.
            else:
                # base_type is RTL
                if prev_type == next_type:
                    number_level = prev_type
                elif prev_type == CharClass.RIGHT_TO_LEFT:
                    # next_type should be LTR (RTL -> number -> LTR)
                    # Seems we must attach number to next type (LTR) only if next run is not space (or neutral?)
                    next_run_is_neutral = False
                    if index_run < len(cls_runs) - 1:
                        next_run = cls_runs[index_run + 1]
                        next_run_type = next_run[0][1]
                        assert next_run_type in (
                            CharClass.LEFT_TO_RIGHT,
                            CharClass.NEUTRAL,
                        )
                        next_run_is_neutral = next_run_type == CharClass.NEUTRAL

                    number_level = prev_type if next_run_is_neutral else next_type
                else:
                    # next_type should be RTL (LTR -> number -> RTL)
                    # Logical order with segment direction: <<(next)<< NN(number)NN >>(prev)>> <<(base)<<
                    # Expected visual order:
                    # either: <<(next)<< >>(prev)>> NN(number)NN <<(base)<< (number attached to prev)
                    # or:     <<(next)<< NN(number)NN >>(prev)>> <<(base)<< (number as RTL head of next?)
                    # Hypothesis: first (attached to prev) for EN numbers, and AN numbers not following spaces.
                    if is_full_arabic_number:
                        prev_run_is_neutral = False
                        if index_run > 0:
                            prev_run = cls_runs[index_run - 1]
                            prev_run_type = prev_run[0][1]
                            assert prev_run_type in (
                                CharClass.LEFT_TO_RIGHT,
                                CharClass.NEUTRAL,
                            )
                            prev_run_is_neutral = prev_run_type == CharClass.NEUTRAL
                        number_level = next_type if prev_run_is_neutral else prev_type
                    else:
                        number_level = prev_type

            run_seg_levels.append(number_level)
            run_char_levels.append(CharClass.LEFT_TO_RIGHT)
        else:
            run_seg_levels.append(None)
            run_char_levels.append(None)

    # Infer segment and character levels for neutral runs.
    for index_run, run in enumerate(cls_runs):
        if run_seg_levels[index_run] is None:
            assert run[0][1] == CharClass.NEUTRAL
            prev_level = run_seg_levels[index_run - 1] if index_run > 0 else base_type
            next_level = (
                run_seg_levels[index_run + 1]
                if index_run < len(run_seg_levels) - 1
                else base_type
            )
            neutral_level = prev_level if prev_level == next_level else base_type
            run_seg_levels[index_run] = neutral_level
            run_char_levels[index_run] = neutral_level

    segments = []
    for index_run, run in enumerate(cls_runs):
        run_seg_level = run_seg_levels[index_run]
        run_char_level = run_char_levels[index_run]
        assert run_seg_level is not None
        assert run_char_level is not None
        directed_segment = DirectedSegment(
            directed_characters=tuple(
                DirectedCharacter(
                    character=characters[logical_pos],
                    logical_position=logical_pos,
                    level=_char_type_to_level(run_char_level),
                )
                for logical_pos, _ in run
            ),
            segment_level=_char_type_to_level(run_seg_level),
        )
        segments.append(directed_segment)

    return segments


def compute_segments_visual_order(
    segments: list[DirectedSegment], base_is_rtl: bool = False
) -> list[DirectedSegment]:
    run_sequences = []
    run_levels = []
    seg_run = []
    for i, segment in enumerate(segments):
        if seg_run and segments[i - 1].segment_level != segment.segment_level:
            run_sequences.append(seg_run)
            run_levels.append(segments[i - 1].segment_level)
            seg_run = []
        seg_run.append(segment)
    if seg_run:
        run_sequences.append(seg_run)
        run_levels.append(segments[-1].segment_level)

    for run_level, run in zip(run_levels, run_sequences):
        if run_level < 0:
            run.reverse()

    if base_is_rtl:
        run_sequences.reverse()

    return [seg for run in run_sequences for seg in run]


# todo test "en turc ottoman : دولت 3000 عليه 2000 عثمانیه / devlet-i ʿaliyye-i"
