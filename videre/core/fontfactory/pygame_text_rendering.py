import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import pygame
import pygame.freetype
import pygame.gfxdraw
import pygame.transform

from videre.colors import Colors
from videre.core.constants import TextAlign
from videre.core.fontfactory.font_factory_utils import (
    CharTask,
    Line,
    WordTask,
    WordsLine,
    align_words,
)
from videre.core.fontfactory.pygame_font_factory import PygameFontFactory
from videre.core.pygame_utils import Color, PygameUtils, Surface


class FontSizes:
    __slots__ = (
        "height_delta",
        "line_spacing",
        "ascender",
        "descender",
        "space_width",
        "space_shift",
    )

    def __init__(self, base_font: pygame.freetype.Font, size: int, height_delta=2):
        self.height_delta = height_delta
        self.line_spacing = base_font.get_sized_height(size) + height_delta
        self.ascender = abs(base_font.get_sized_ascender(size)) + 1
        self.descender = abs(base_font.get_sized_descender(size))
        self.space_width = base_font.get_rect(" ", size=size).width

        (metric,) = base_font.get_metrics(" ", size=size)
        self.space_shift = metric[4] if metric else self.space_width


@dataclass(slots=True)
class RenderedText:
    lines: list[Line[WordTask]]
    surface: Surface
    font_sizes: FontSizes

    def first_x(self) -> int:
        if self.lines:
            line = self.lines[0]
            if line.elements:
                return line.elements[0].x
        return 0


class PygameTextRendering(PygameUtils):
    def __init__(
        self,
        fonts: PygameFontFactory,
        size=0,
        strong=False,
        italic=False,
        underline=False,
        height_delta=2,
    ):
        super().__init__()

        size = size or fonts.size
        height_delta = 2 if height_delta is None else height_delta

        self._fonts = fonts
        self._size = size
        self._strong = bool(strong)
        self._italic = bool(italic)
        self._underline = bool(underline)

        self._height_delta = height_delta
        self._font_sizes = FontSizes(fonts.base_font, size, height_delta)
        self._render_word_lines = self._render_word_lines_old

    def _get_font(self, text: str):
        font = self._fonts.get_font(text)
        try:
            font.strong = self._strong
            font.oblique = self._italic
        except Exception as exc:
            logging.warning(
                f'Unable to set strong or italic for font "{font.name}": '
                f"{type(exc).__name__}: {exc}"
            )
        return font

    def render_char(self, c: str, color: Color = None) -> Surface:
        surface, box = self._get_font(c).render(c, size=self._size, fgcolor=color)
        return surface

    def render_text(
        self,
        text: str,
        width: int = None,
        *,
        compact=True,
        color: Color = None,
        align=TextAlign.LEFT,
        wrap_words=False,
        selection: tuple[int, int] | None = None,
    ) -> RenderedText:
        if width is None or not wrap_words:
            new_width, height, char_lines = self._get_char_tasks(text, width, compact)
            lines = WordsLine.from_chars(
                char_lines, keep_spaces=align == TextAlign.NONE
            )
        else:
            new_width, height, lines = self._get_word_tasks(text, width, compact)
        surface = self._render_word_lines(
            new_width, height, lines, align, color, selection
        )
        return RenderedText(lines, surface, self._font_sizes)

    def _render_word_lines_old(
        self,
        width: int,
        height: int,
        lines: list[Line[WordTask]],
        align: TextAlign,
        color: Color,
        selection: tuple[int, int] | None = None,
    ) -> Surface:
        align_words(lines, width, align)
        size = self._size
        out = self.new_surface(width, height)
        for rect in self._get_selection_rects(lines, selection):
            pygame.gfxdraw.box(out, rect, (100, 100, 255, 100))
        for line in lines:
            self._draw_underline(line, out, color)
            ly = line.y
            lx = line.x
            for word in line.elements:
                wx = lx + word.x
                for ch in word.tasks:
                    ch.font.render_to(
                        out, (wx + ch.x, ly), ch.el, size=size, fgcolor=color
                    )
        return out

    def _render_word_lines_new(
        self,
        width: int,
        height: int,
        lines: list[Line[WordTask]],
        align: TextAlign,
        color: Color,
        selection: tuple[int, int] | None = None,
    ) -> Surface:
        align_words(lines, width, align)
        size = self._size
        out = self.new_surface(width, height)
        if selection:
            for rect in self._get_selection_rects(lines, selection):
                pygame.gfxdraw.box(out, rect, (100, 100, 255, 100))
        for ly, lx, wx, chars in self._get_rendering_blocks(lines):
            first = chars[0]
            s = "".join(ch.el for ch in chars)
            first.font.render_to(
                out, (lx + wx + first.x, ly), s, size=size, fgcolor=color
            )
        if self._underline:
            for line in lines:
                self._draw_underline(line, out, color)
        return out

    @classmethod
    def _get_rendering_blocks(cls, lines: list[Line[WordTask]]):
        nb_chars = 0
        blocks: list[tuple[int, int, int, list[CharTask]]] = []
        for line in lines:
            for word in line.elements:
                nb_chars += len(word.tasks)
                current: list[CharTask] = []
                for char in word.tasks:
                    if not current or current[0].font == char.font:
                        current.append(char)
                    else:
                        blocks.append((line.y, line.x, word.x, current))
                        current = [char]
                if current:
                    blocks.append((line.y, line.x, word.x, current))
        # print(f"Blocks: {len(blocks)} vs characters: {nb_chars}")
        return blocks

    def _get_selection_rects(
        self, lines: list[Line[WordTask]], selection: tuple[int, int] | None
    ) -> list[pygame.Rect]:
        if selection is None:
            return []

        start, end = selection
        if start == end:
            return []
        assert start < end

        rects = []
        for line in lines:
            if not line.elements:
                continue

            line_start = line.elements[0].tasks[0].pos
            line_end = line.elements[-1].tasks[-1].pos + 1

            if line_end <= start or line_start >= end:
                continue

            # Calculate x coordinates for this line
            if line_start < start:
                start_x = None
                for word in line.elements:
                    for char in word.tasks:
                        if char.pos >= start:
                            start_x = word.x + char.x
                            break
                    if start_x is not None:
                        break
                assert start_x is not None
            else:
                start_x = line.elements[0].x

            if line_end > end:
                end_x = None
                for word in line.elements:
                    for char in word.tasks:
                        if char.pos >= end:
                            end_x = word.x + char.x
                            break
                    if end_x is not None:
                        break
                assert end_x is not None
            else:
                end_x = line.elements[-1].x + line.elements[-1].width

            # Create selection rectangle for this line
            rect = pygame.Rect(
                start_x,
                line.y - self._font_sizes.ascender,
                end_x - start_x,
                self._font_sizes.ascender + self._font_sizes.descender,
            )
            rects.append(rect)

        return rects

    def _draw_underline(self, line: Line[WordTask], out: Surface, color):
        if self._underline and line:
            c = "_"
            x1 = line.elements[0].x + line.elements[0].tasks[0].bounds.x
            x2 = line.limit()
            font = self._get_font(c)
            font.antialiased = False
            surface, box = font.render(
                c, size=self._size, fgcolor=color or Colors.black
            )
            font.antialiased = True
            us = surface.convert_alpha()
            width = x2 - x1
            height = box.height
            underline = pygame.transform.smoothscale(us, (width, height))
            out.blit(underline, (x1, line.y - box.y))

    def _get_char_tasks(
        self, text: str, width: int | None, compact: bool
    ) -> tuple[int, int, list[Line[CharTask]]]:
        return self._get_tasks(self._get_chars, self._parse_char, text, width, compact)

    def _get_word_tasks(
        self, text: str, width: int, compact: bool
    ) -> tuple[int, int, list[Line[WordTask]]]:
        return self._get_tasks(self._get_words, self._parse_word, text, width, compact)

    def _get_tasks[T](
        self,
        get_elements: Callable[[str], Iterable[Any]],
        parse_element: Callable[[Any], T],
        text: str,
        width: int | None,
        compact: bool,
    ) -> tuple[int, int, list[Line[T]]]:
        lines = []
        task_line = Line[T]()
        x = 0
        for el in get_elements(text):
            info = parse_element(el)
            if info.is_newline():
                lines.append(task_line)
                task_line = Line[T](newline=True)
                x = 0
            elif info.is_printable():
                if width is not None and x and x + info.width > width:
                    lines.append(task_line)
                    task_line = Line[T]()
                    x = 0
                task_line.add(info.at(x))
                x += info.horizontal_shift
        # Add remaining line if necessary
        if task_line:
            lines.append(task_line)
        # Compute width, height and ys
        new_width, height = self._get_text_dimensions(lines, compact)
        return new_width, height, lines

    def _get_text_dimensions(self, lines: list[Line], compact: bool) -> tuple[int, int]:
        # Compute width, height and ys
        new_width, height = 0, 0
        if lines:
            first_line = lines[0]
            first_line.y = (
                self._font_sizes.ascender + self._height_delta
                if compact and first_line.elements
                else self._font_sizes.line_spacing
            )
            for i in range(1, len(lines)):
                lines[i].y = lines[i - 1].y + self._font_sizes.line_spacing
            height = lines[-1].y + self._font_sizes.descender
            new_width = max(
                (line.limit() for line in lines if line.elements), default=0
            )
        return new_width, height

    @classmethod
    def _get_chars(cls, text: str) -> Iterable[tuple[int, str]]:
        return enumerate(text)

    @classmethod
    def _get_words(cls, text: str) -> Iterable[str]:
        first_line, *next_lines = text.split("\n")
        words = [word for word in first_line.split(" ") if word]
        for line in next_lines:
            words.append("\n")
            words.extend(word for word in line.split(" ") if word)
        return words

    def _parse_char(self, ic: tuple[int, str]):
        charpos, c = ic
        font = self._get_font(c)

        bounds = font.get_rect(c, size=self._size)
        width = bounds.x + bounds.width

        (metric,) = font.get_metrics(c, size=self._size)
        horizontal_shift = metric[4] if metric else width

        return CharTask(c, font, width, horizontal_shift, bounds, charpos)

    def _parse_word(self, word: str):
        width, height, lines = self._get_char_tasks(word, None, False)
        if width:
            (line,) = lines
            tasks = line.elements
            last_char = tasks[-1]
            shift = last_char.x + last_char.horizontal_shift
        else:
            tasks = []
            shift = 0
        return WordTask(width, 0, tasks, height, shift + self._font_sizes.space_shift)
