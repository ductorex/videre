from abc import ABC, abstractmethod
from typing import Self

import pygame

from videre import TextAlign
from videre.fonts.unicode_utils import Unicode


class AbstractTextElement(ABC):
    __slots__ = ("x",)

    def __init__(self, x=0):
        self.x = x

    @abstractmethod
    def is_newline(self) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_printable(self) -> bool:
        raise NotImplementedError()

    def at(self, x: int) -> Self:
        self.x = x
        return self


class CharTask(AbstractTextElement):
    __slots__ = ("el", "font", "width", "horizontal_shift", "bounds", "pos")

    def __init__(
        self,
        c: str,
        font,
        width: int,
        horizontal_shift: int,
        bounds: pygame.Rect,
        pos: int,
    ):
        super().__init__(0)
        self.el = c
        self.font = font
        self.width = width
        self.horizontal_shift = horizontal_shift
        self.bounds = bounds
        self.pos = pos

    def __repr__(self):
        return f"{repr(self.el)}:pos={self.pos}@{self.x},print={self.is_printable()}"

    def is_newline(self) -> bool:
        return self.el == "\n"

    def is_printable(self) -> bool:
        return Unicode.printable(self.el)


class WordTask(AbstractTextElement):
    __slots__ = ("width", "tasks", "height", "horizontal_shift")

    def __init__(
        self, width: int, x: int, tasks: list[CharTask], height=0, horizontal_shift=0
    ):
        super().__init__(x)
        self.width = width
        self.tasks = tasks
        self.height = height
        self.horizontal_shift = horizontal_shift

    def __repr__(self):
        return f"{self.x}:" + repr("".join(t.el for t in self.tasks))

    def is_newline(self) -> bool:
        return self.height and not self.width

    def is_printable(self) -> bool:
        return bool(self.width)


class Line[T: AbstractTextElement]:
    __slots__ = ("x", "y", "newline", "elements")

    def __init__(self, y=0, newline=False):
        self.x = 0
        self.y = y
        self.newline = newline
        self.elements: list[T] = []

    def __repr__(self):
        return f"({self.y}, {self.elements})"

    def __bool__(self):
        return bool(self.elements or self.newline)

    def add(self, element: T):
        self.elements.append(element)

    def limit(self) -> int:
        info = self.elements[-1]
        return info.x + info.width


class CharsLine(Line[CharTask]):
    __slots__ = ()


class WordsLine(Line[WordTask]):
    __slots__ = ()

    @classmethod
    def from_chars(cls, lines: list[Line[CharTask]], keep_spaces=False):
        if keep_spaces:
            word_lines = [WordsLine._chars_to_word(line) for line in lines]
        else:
            word_lines = [WordsLine._split_words(line) for line in lines]
        return word_lines

    @classmethod
    def _chars_to_word(cls, ch_line: Line[CharTask]) -> Self:
        tasks = ch_line.elements
        words_line = cls(ch_line.y)
        words_line.add(WordTask(ch_line.limit() if tasks else 0, 0, tasks))
        return words_line

    @classmethod
    def _split_words(cls, chars_line: Line[CharTask]) -> Self:
        words: list[list[CharTask]] = []
        word: list[CharTask] = []
        for task in chars_line.elements:
            if task.el == " ":
                if word:
                    words.append(word)
                    word = []
            else:
                word.append(task)
        if word:
            words.append(word)
        words_line = cls(chars_line.y)
        if words:
            x0 = words[0][0].x
            for word in words:
                w_x = word[0].x
                x = w_x - x0
                tasks = [ch.at(ch.x - w_x) for ch in word]
                last_ch = tasks[-1]
                w = last_ch.x + last_ch.width
                words_line.add(WordTask(w, x, tasks))
        return words_line


def align_words(lines: list[Line[WordTask]], width: int, align=TextAlign.LEFT) -> None:
    if align == TextAlign.NONE or align == TextAlign.LEFT:
        return
    if align == TextAlign.JUSTIFY:
        justify_words(lines, width)
        return
    for line in lines:
        if line.elements:
            assert line.elements[0].x == 0, line
            remaining = width - line.limit()
            if remaining:
                if align == TextAlign.CENTER:
                    remaining /= 2
                line.x = remaining


def justify_words(lines: list[Line[WordTask]], width: int) -> None:
    paragraphs = []
    p = []
    for line in lines:
        if line.elements:
            p.append(line)
        elif p:
            paragraphs.append(p)
            p = []
    if p:
        paragraphs.append(p)

    for paragraph in paragraphs:
        for i in range(len(paragraph) - 1):
            line = paragraph[i]
            if len(line.elements) > 1:
                assert line.elements[0].x == 0
                remaining = width - sum(wt.width for wt in line.elements)
                if remaining:
                    interval = remaining / (len(line.elements) - 1)
                    x = line.elements[0].width + interval
                    for j in range(1, len(line.elements)):
                        wt = line.elements[j]
                        wt.x = x
                        x += wt.width + interval
