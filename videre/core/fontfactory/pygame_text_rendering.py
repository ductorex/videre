import bisect
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import pygame
import pygame.freetype
import pygame.gfxdraw
import pygame.transform

from videre.colors import Color
from videre.core.caret_position import CaretPosition
from videre.core.constants import TextAlign
from videre.core.fontfactory.font_factory_utils import (
    AbstractTextElement,
    CharTask,
    Line,
    WordsLine,
    WordTask,
    align_words,
)
from videre.core.fontfactory.pygame_font_factory import CharMeasures, PygameFontFactory
from videre.core.pygame_backend import Pygame, PygameRendered, Surface, Rect


class FontSizes:
    __slots__ = (
        "height_delta",
        "line_spacing",
        "ascender",
        "descender",
        "space_width",
        "space_shift",
    )

    def __init__(self, base: CharMeasures, size: int, height_delta=2):
        base_font = base.font
        metric = base.metrics

        self.height_delta: int = height_delta
        self.line_spacing: int = base_font.get_sized_height(size) + height_delta
        self.ascender: int = abs(base_font.get_sized_ascender(size)) + 1
        self.descender: int = abs(base_font.get_sized_descender(size))
        self.space_width: int = base.rect.width
        self.space_shift: int | float = metric[4] if metric else self.space_width


@dataclass(slots=True)
class RenderedText:
    _rendered_lines: list[Line[WordTask]]
    _rendered_font_sizes: FontSizes

    def pos_to_pixel(self, pos: int) -> CaretPosition:
        """Caret position for a logical source character position.

        Mirrors the helper exposed by `ShapedRenderedText` so consumers
        like `TextInput` can target the same API regardless of which
        renderer is in use. The legacy pipeline lays out characters
        with absolute x coordinates inside a single `WordTask` per
        line (TextInput uses Text with `keep_spaces=True`, which
        triggers `WordsLine._chars_to_word`); we leverage that
        invariant to return `char.x` directly as the caret x.
        """
        nonempty = [ln for ln in self._rendered_lines if ln.elements]
        if not nonempty:
            return self._null_caret()
        keys = [ln.elements[0].tasks[0].pos for ln in nonempty]
        line_idx = max(0, bisect.bisect_right(keys, pos) - 1)
        line = nonempty[line_idx]
        word_idx = max(
            0, bisect.bisect_right(line.elements, pos, key=lambda w: w.tasks[0].pos) - 1
        )
        word = line.elements[word_idx]
        char_idx = max(
            0, bisect.bisect_right(word.tasks, pos, key=lambda chr: chr.pos) - 1
        )
        char = word.tasks[char_idx]
        cursor_x = char.x + (char.horizontal_shift if pos > char.pos else 0)
        asc = self._rendered_font_sizes.ascender
        desc = self._rendered_font_sizes.descender
        return CaretPosition(
            x=int(cursor_x), y_top=int(line.y - asc), y_bottom=int(line.y + desc)
        )

    def pixel_to_pos(self, x: int, y: int) -> int:
        """Source character position closest to a pixel coordinate.

        Mirrors the helper exposed by `ShapedRenderedText`. Snaps to
        the nearer of `char.x` (start) and `char.x +
        char.horizontal_shift` (end). `y` clamps to the line whose
        baseline is just above; out-of-range x snaps to the nearest
        edge of the line's content.
        """
        if not self._rendered_lines:
            return 0
        ys = [line.y for line in self._rendered_lines]
        line_pos = max(0, bisect.bisect_right(ys, y) - 1)
        line = self._rendered_lines[line_pos]
        if not line.elements:
            return 0
        xs = [el.x for el in line.elements]
        word_pos = max(0, bisect.bisect_right(xs, x) - 1)
        word = line.elements[word_pos]
        char_xs = [word.x + ch.x for ch in word.tasks]
        char_pos = max(0, bisect.bisect_right(char_xs, x) - 1)
        char = word.tasks[char_pos]
        left = char.x
        right = char.x + char.horizontal_shift
        if abs(x - left) <= abs(x - right):
            return char.pos
        return char.pos + 1

    def _null_caret(self) -> CaretPosition:
        """Caret for the degenerate empty-text case. Lands at the
        line's left edge, height = ascender + descender."""
        asc = self._rendered_font_sizes.ascender
        desc = self._rendered_font_sizes.descender
        height_delta = self._rendered_font_sizes.height_delta
        return CaretPosition(
            x=0, y_top=int(height_delta), y_bottom=int(height_delta + asc + desc)
        )


class PygameTextRendering:
    def __init__(
        self,
        fonts: PygameFontFactory,
        size=0,
        strong=False,
        italic=False,
        underline=False,
        height_delta=2,
        compact: bool = True,
    ):
        size = size or fonts.size
        height_delta = 2 if height_delta is None else height_delta
        strong = bool(strong)
        italic = bool(italic)
        base = fonts.get_char_measures(" ", size, strong, italic)

        self._fonts = fonts
        self._size: int = size
        self._strong: bool = strong
        self._italic: bool = italic
        self._underline: bool = bool(underline)

        self._height_delta = height_delta
        self._font_sizes = FontSizes(base, size, height_delta)

        self._compact = compact

    def render_char(self, c: str, color: Color | None = None) -> Surface:
        fgcolor = None if color is None else Pygame.new_color(color)
        surface, box = self._fonts.get_font(
            c, strong=self._strong, italic=self._italic
        ).render(c, size=self._size, fgcolor=fgcolor)
        return surface

    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[RenderedText, PygameRendered]:
        compact = self._compact
        if width is None or not wrap_words:
            new_width, height, char_lines = self._get_char_tasks(text, width, compact)
            lines = WordsLine.from_chars(char_lines, keep_spaces=align is None)
        else:
            new_width, height, lines = self._get_word_tasks(text, width, compact)
        surface = self._render_word_lines(
            new_width, height, lines, align, color, selection
        )
        return RenderedText(lines, self._font_sizes), PygameRendered(surface)

    def _render_word_lines(
        self,
        width: int | float,
        height: int | float,
        lines: list[Line[WordTask]],
        align: TextAlign | None,
        color: Color | None,
        selection: tuple[int, int] | None = None,
    ) -> Surface:
        align_words(lines, width, align)
        size = self._size
        out = self._fonts.new_surface(width, height)
        for rect in self._get_selection_rects(lines, selection):
            pygame.gfxdraw.box(out, rect, (100, 100, 255, 100))
        pygame_color = None if color is None else Pygame.new_color(color)
        for line in lines:
            self._draw_underline(line, out, pygame_color)
            ly = line.y
            lx = line.x
            for word in line.elements:
                wx = lx + word.x
                for ch in word.tasks:
                    ch.font.render_to(
                        out, (wx + ch.x, ly), ch.el, size=size, fgcolor=pygame_color
                    )
        return out

    @classmethod
    def _get_rendering_blocks(cls, lines: list[Line[WordTask]]):
        nb_chars = 0
        blocks: list[tuple[int | float, int | float, int | float, list[CharTask]]] = []
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
    ) -> list[Rect]:
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
            rect = Rect(
                start_x,
                line.y - self._font_sizes.ascender,
                end_x - start_x,
                self._font_sizes.ascender + self._font_sizes.descender,
            )
            rects.append(rect)

        return rects

    def _draw_underline(
        self, line: Line[WordTask], out: Surface, color: pygame.Color | None
    ):
        if self._underline and line:
            c = "_"
            x1 = line.elements[0].x + line.elements[0].tasks[0].bounds.x
            x2 = line.limit()
            font = self._fonts.get_font(c, strong=self._strong, italic=self._italic)
            font.antialiased = False
            surface, box = font.render(c, size=self._size, fgcolor=color)
            font.antialiased = True
            us = surface.convert_alpha()
            width = x2 - x1
            height = box.height
            underline = pygame.transform.smoothscale(us, (width, height))
            out.blit(underline, (x1, line.y - box.y))

    def _get_char_tasks(
        self, text: str, width: int | None, compact: bool
    ) -> tuple[int | float, int | float, list[Line[CharTask]]]:
        return self._get_tasks(self._get_chars, self._parse_char, text, width, compact)

    def _get_word_tasks(
        self, text: str, width: int, compact: bool
    ) -> tuple[int | float, int | float, list[Line[WordTask]]]:
        return self._get_tasks(self._get_words, self._parse_word, text, width, compact)

    def _get_tasks[T: AbstractTextElement](
        self,
        get_elements: Callable[[str], Iterable[Any]],
        parse_element: Callable[[Any], T],
        text: str,
        width: int | None,
        compact: bool,
    ) -> tuple[int | float, int | float, list[Line[T]]]:
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

    def _get_text_dimensions(
        self, lines: list[Line], compact: bool
    ) -> tuple[int | float, int | float]:
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
        else:
            height = (
                self._font_sizes.ascender + self._height_delta
                if compact
                else self._font_sizes.line_spacing
            ) + self._font_sizes.descender
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

    def _parse_char(self, ic: tuple[int, str]) -> CharTask:
        charpos, c = ic

        char_measures = self._fonts.get_char_measures(
            c, self._size, self._strong, self._italic
        )
        font = char_measures.font
        bounds = char_measures.rect
        # todo: should instead be: width = bounds.width ?
        width = bounds.x + bounds.width

        metric = char_measures.metrics
        horizontal_shift = metric[4] if metric else width

        return CharTask(c, font, width, horizontal_shift, bounds, charpos)

    def _parse_word(self, word: str) -> WordTask:
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
