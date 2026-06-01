from enum import Enum, auto, unique


@unique
class TextWrap(Enum):
    CHAR = auto()
    WORD = auto()
    # WORD_THEN_CHAR = auto()  # todo


@unique
class TextSpacePolicy(Enum):
    # AUTO (default) policy: **collapse** only if TextWrap.WORD, preserve otherwise.
    AUTO = auto()
    COLLAPSE = auto()
    PRESERVE = auto()


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
