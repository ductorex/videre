from dataclasses import dataclass
from typing import Any, Callable, Iterable

from videre.colors import Colors
from videre.core.constants import TextAlign
from videre.core.drawer import Color, Drawer, Position, Rectangle
from videre.core.fontfactory.font_factory_utils import (
    CharTask,
    Line,
    WordsLine,
    WordTask,
    align_words,
    AbstractTextElement,
)
from videre.core.fontfactory.pygame_font_factory import CharMeasures, PygameFontFactory
from videre.core.pygame_drawer_executor import PygameDrawerExecutor


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
    lines: list[Line[WordTask]]
    font_sizes: FontSizes
    drawer: Drawer

    def first_x(self) -> int | float:
        if self.lines:
            line = self.lines[0]
            if line.elements:
                return line.elements[0].x
        return 0


class PygameTextRendering:
    def __init__(
        self,
        fonts: PygameFontFactory,
        size=0,
        strong=False,
        italic=False,
        underline=False,
        height_delta=2,
    ):
        size = size or fonts.default_size
        height_delta = 2 if height_delta is None else height_delta
        strong = bool(strong)
        italic = bool(italic)
        base = fonts.get_char_measures(" ", size, strong, italic)

        self._fonts = fonts
        self._executor = PygameDrawerExecutor(fonts)
        self._size: int = size
        self._strong: bool = strong
        self._italic: bool = italic
        self._underline: bool = bool(underline)

        self._height_delta = height_delta
        self._font_sizes = FontSizes(base, size, height_delta)

    def render_char_drawer(self, c: str, color: Color | None = None) -> Drawer:
        df = self._fonts.resolve(c, strong=self._strong, italic=self._italic)
        cm = self._fonts.char_metrics(df, c, self._size)
        drawer = Drawer(cm.width, cm.height)
        drawer.text(df, Position(-cm.x, cm.y), c, size=self._size, fgcolor=color)
        return drawer

    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        compact=True,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> RenderedText:
        if width is None or not wrap_words:
            new_width, height, char_lines = self._get_char_tasks(text, width, compact)
            lines = WordsLine.from_chars(char_lines, keep_spaces=align is None)
        else:
            new_width, height, lines = self._get_word_tasks(text, width, compact)
        drawer = self._render_word_lines(
            new_width, height, lines, align, color, selection
        )
        return RenderedText(lines, self._font_sizes, drawer)

    def _render_word_lines(
        self,
        width: int | float,
        height: int | float,
        lines: list[Line[WordTask]],
        align: TextAlign | None,
        color: Color | None,
        selection: tuple[int, int] | None = None,
    ) -> Drawer:
        align_words(lines, width, align)
        size = self._size
        drawer = Drawer(width, height)
        selection_color = Color(100, 100, 255, 100)
        for rect in self._get_selection_rects(lines, selection):
            drawer.box(rect, selection_color)
        fg = color
        underline_color = fg if fg is not None else Colors.black
        for line in lines:
            urect = self._underline_rect(line)
            if urect is not None:
                drawer.box(urect, underline_color)
            ly = line.y
            lx = line.x
            for word in line.elements:
                wx = lx + word.x
                for ch in word.tasks:
                    df = self._fonts.resolve(
                        ch.el, strong=self._strong, italic=self._italic
                    )
                    drawer.text(
                        df, Position(wx + ch.x, ly), ch.el, size=size, fgcolor=fg
                    )
        return drawer

    def _get_selection_rects(
        self, lines: list[Line[WordTask]], selection: tuple[int, int] | None
    ) -> list[Rectangle]:
        if selection is None:
            return []

        start, end = selection
        if start == end:
            return []
        assert start < end

        rects: list[Rectangle] = []
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

            rects.append(
                Rectangle(
                    start_x,
                    line.y - self._font_sizes.ascender,
                    end_x - start_x,
                    self._font_sizes.ascender + self._font_sizes.descender,
                )
            )

        return rects

    def _underline_rect(self, line: Line[WordTask]) -> Rectangle | None:
        if not (self._underline and line and line.elements):
            return None
        df = self._fonts.resolve(" ", strong=self._strong, italic=self._italic)
        um = self._fonts.underline_metrics(df, self._size)
        first_word = line.elements[0]
        x1 = line.x + first_word.x + first_word.tasks[0].bounds.x
        x2 = line.x + line.limit()
        return Rectangle(x1, line.y + um.offset, x2 - x1, um.thickness)

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
