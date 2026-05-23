from enum import Enum, unique


@unique
class TextWrap(Enum):
    CHAR = 1
    WORD = 2
    # WORD_THEN_CHAR = 3  # todo


@unique
class TextAlign(Enum):
    LEFT = 1
    CENTER = 2
    RIGHT = 3
    JUSTIFY = 4


@unique
class Alignment(Enum):
    START = 0
    CENTER = 1
    END = 2


@unique
class Side(Enum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"


WINDOW_FPS = 60
