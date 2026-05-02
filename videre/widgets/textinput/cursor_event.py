import bisect
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from videre.core.fontfactory.pygame_text_rendering import RenderedText

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CursorDefinition:
    x: int | float
    y: int
    pos: int


class _CursorEvent(ABC):
    __slots__ = ()

    @abstractmethod
    def handle(self, rendered: RenderedText) -> CursorDefinition:
        raise NotImplementedError()

    @classmethod
    def null(cls, rendered: RenderedText) -> CursorDefinition:
        return CursorDefinition(x=0, y=rendered.font_sizes.height_delta, pos=0)


class CursorMouseEvent:
    __slots__ = ("x", "y")

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"{type(self).__name__}({self.x}, {self.y})"

    def _handle(self, rendered: RenderedText) -> Any:
        x = self.x
        y = self.y

        lines = rendered.lines
        if not lines:
            return None

        ys = [line.y for line in lines]
        line_pos = max(0, bisect.bisect_right(ys, y) - 1)
        line = lines[line_pos]
        if not line.elements:
            return None

        xs = [el.x for el in line.elements]
        word_pos = max(0, bisect.bisect_right(xs, x) - 1)
        word = line.elements[word_pos]
        char_xs = [word.x + ch.x for ch in word.tasks]
        char_pos = max(0, bisect.bisect_right(char_xs, x) - 1)
        char = word.tasks[char_pos]
        left = char.x
        right = char.x + char.advance

        # NB: x may be outside the line, e.g. before line start or after line end.
        # So, it is not guaranteed that left <= x <= right.
        dist_x_left = abs(x - left)
        dist_x_right = abs(x - right)

        if dist_x_left <= dist_x_right:
            to_right = False
            chosen_charpos = char.pos
        else:
            to_right = True
            chosen_charpos = char.pos + 1

        return line, chosen_charpos, left, right, to_right

    def to_pos(self, rendered: RenderedText) -> int:
        output = self._handle(rendered)
        if output is None:
            return 0
        _, chosen_charpos, _, _, _ = output
        return chosen_charpos


class CursorCharPosEvent(_CursorEvent):
    __slots__ = ("pos",)

    def __init__(self, pos: int):
        self.pos = pos

    def __repr__(self):
        return f"{type(self).__name__}({self.pos})"

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.pos == other.pos

    def handle(self, rendered: RenderedText) -> CursorDefinition:
        pos = self.pos

        lines = rendered.lines
        if not lines:
            return self.null(rendered)

        line_pos = max(
            0,
            bisect.bisect_right(
                lines, pos, key=lambda line: line.elements[0].tasks[0].pos
            )
            - 1,
        )
        line = lines[line_pos]
        if not line.elements:
            return self.null(rendered)

        word_pos = max(
            0, bisect.bisect_right(line.elements, pos, key=lambda w: w.tasks[0].pos) - 1
        )
        word = line.elements[word_pos]
        char_pos = max(
            0, bisect.bisect_right(word.tasks, pos, key=lambda chr: chr.pos) - 1
        )
        char = word.tasks[char_pos]
        if pos not in (char.pos, char.pos + 1):
            logger.error(
                f"Unexpected char pos {char.pos} for cursor pos {pos}; char: {char}"
            )

        left = char.x
        right = char.x + char.advance

        cursor_y = line.y - rendered.font_sizes.ascender
        if pos > char.pos:
            cursor_x = right
        else:
            cursor_x = left
        return CursorDefinition(x=cursor_x, y=cursor_y, pos=pos)
