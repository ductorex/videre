from enum import Enum, auto, unique


@unique
class TextWrap(Enum):
    CHAR = auto()
    WORD = auto()
    # WORD_THEN_CHAR = auto()  # todo


@unique
class TextSpacePolicy(Enum):
    """How runs of whitespace (gaps) are kept or collapsed when laying out text.

    Mirrors CSS `white-space-collapse` (combined with the wrap mode and
    `word-break`). videre always keeps newlines as hard breaks (logical lines
    are split upstream in the partitioner), so `COLLAPSE` matches CSS
    `pre-line` rather than `normal` / `nowrap` (which also collapse newlines).

      policy    wrap      ~ CSS
      --------  --------  --------------------------------
      COLLAPSE  no wrap   white-space: nowrap              (1)
      COLLAPSE  by word   white-space: normal             (1)
      COLLAPSE  by char   normal + word-break: break-all  (1)
      PRESERVE  no wrap   white-space: pre
      PRESERVE  by word   white-space: pre-wrap
      PRESERVE  by char   pre-wrap + word-break: break-all (2)

    (1) spaces only; newlines stay hard -> closer to pre-line.
    (2) terminal / <textarea>-like; no rigorous CSS equivalent.

    COLLAPSE shrinks every run of spaces to one; it drops gaps at line edges
    ONLY under word wrap (char wrap / no wrap keep an edge space, to disambiguate
    a word boundary from a mid-word break — a GUI choice, unlike CSS which trims
    every line edge). PRESERVE never drops a space, it only redistributes them
    across wrapped lines. See `text_partition.wrap` for the full
    start / inside / end table per (width x wrap_words x policy).
    """

    # AUTO (default): COLLAPSE when wrapping by word (TextWrap.WORD), PRESERVE
    # otherwise (wrap by char, or no wrap). The "natural" default: word-wrapped
    # text is tidied like a browser, char-wrapped / unwrapped text is faithful.
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
