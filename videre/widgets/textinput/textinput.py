import bisect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pygame
import pygame.gfxdraw
from cursword import get_next_word_end_position, get_previous_word_start_position

from videre.colors import Colors
from videre.core.events import KeyboardEntry, MouseEvent
from videre.core.fontfactory.pygame_text_rendering import RenderedText
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_utils import Surface
from videre.layouts.abstractlayout import AbstractLayout
from videre.layouts.container import Container
from videre.widgets.text import Text
from videre.widgets.textinput.keyboard_handling import compute_key_x
from videre.widgets.widget import Widget


@dataclass(slots=True)
class _CursorDefinition:
    x: int
    y: int
    pos: int


class _CursorEvent(ABC):
    __slots__ = ()

    @abstractmethod
    def handle(self, rendered: RenderedText) -> _CursorDefinition:
        raise NotImplementedError()

    @classmethod
    def null(cls, rendered: RenderedText) -> _CursorDefinition:
        return _CursorDefinition(x=0, y=rendered.font_sizes.height_delta, pos=0)


class _CursorMouseEvent:
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
        right = char.x + char.horizontal_shift

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


class _CursorCharPosEvent(_CursorEvent):
    __slots__ = ("pos",)

    def __init__(self, pos: int):
        self.pos = pos

    def __repr__(self):
        return f"{type(self).__name__}({self.pos})"

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.pos == other.pos

    def handle(self, rendered: RenderedText) -> _CursorDefinition:
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
        assert pos in (
            char.pos,
            char.pos + 1,
        ), f"Unexpected char pos {char.pos} for cursor pos {pos}; char: {char}"

        left = char.x
        right = char.x + char.horizontal_shift

        cursor_y = line.y - rendered.font_sizes.ascender
        if pos > char.pos:
            cursor_x = right
        else:
            cursor_x = left
        return _CursorDefinition(x=cursor_x, y=cursor_y, pos=pos)


class _InputText(Text):
    __wprops__ = {}
    __slots__ = ()


class TextInput(AbstractLayout):
    __wprops__ = {"has_focus", "name"}
    __slots__ = ("_text", "_container", "_cursor_event", "_selecting_pivot")
    __size__ = 1
    __capture_mouse__ = True

    def __init__(self, text="", size=0, **kwargs):
        # self._text = _InputText(text="Hello, 炎炎ノ消防隊: ", size=80)
        self._text = Text(text=text, size=size)
        self._container = Container(self._text, background_color=(240, 240, 240))
        super().__init__([self._container], **kwargs)
        self._cursor_event: _CursorCharPosEvent | None = None
        self._selecting_pivot: int | None = None

        self._set_focus(False)
        self._set_selection(None)
        self._set_cursor(len(self._text.text))

    @property
    def value(self) -> str:
        """Returns the current text value."""
        return self._text.text

    @value.setter
    def value(self, text: str):
        """Sets the text value."""
        self._text.text = text
        self._set_cursor(len(text))
        self._set_selection(None)

    @property
    def _control(self) -> Widget:
        (control,) = self._controls()
        return control

    def __selection(self) -> tuple[int, int] | None:
        """Returns current selection definition if available, else None."""
        return self._text.selection

    def _has_selection(self) -> bool:
        return self.__selection() is not None

    def _get_selection(self) -> tuple[int, int]:
        return self.__selection()

    def _set_selection(self, start: int | None = None, end: int | None = None):
        prev_selection = self.__selection()
        if start is None and end is None:
            selection = None
        elif start is None:
            assert prev_selection
            selection = (prev_selection[0], end)
        elif end is None:
            assert prev_selection
            selection = (start, prev_selection[1])
        else:
            selection = (start, end)
        self._text.selection = selection

    def _has_focus(self) -> bool:
        return self._get_wprop("has_focus")

    def _set_focus(self, value):
        self._set_wprop("has_focus", bool(value))

    def get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        """
        The mouse owner must be this widget itself, not any of its children.
        """
        return Widget.get_mouse_owner(self, x_in_parent, y_in_parent)

    def _mouse_to_pos(self, x: int, y: int) -> int:
        return _CursorMouseEvent(x, y).to_pos(self._text._rendered)

    def _set_cursor(self, pos: int):
        event = _CursorCharPosEvent(pos)
        if self._cursor_event:
            assert type(self._cursor_event) is type(event), (
                f"Unexpected different consecutive cursor event types: "
                f"{self._cursor_event}, {event}"
            )
        if self._cursor_event != event:
            self._cursor_event = event
            self.update()

    def _get_cursor(self) -> int:
        return self._cursor_event.pos

    def handle_mouse_enter(self, event: MouseEvent):
        self.get_window().set_text_cursor()

    def handle_mouse_exit(self):
        self.get_window().set_default_cursor()

    def handle_mouse_down(self, event: MouseEvent):
        self._debug("mouse_down")
        # NB: Mouse position is relative to widget parent.
        # Character positions are relative to widget itself.
        # To make correct comparisons between mouse and characters,
        # we convert mouse position into widget coordinates.
        pos = self._mouse_to_pos(event.x - self.x, event.y - self.y)
        self._selecting_pivot = pos
        self._set_selection(pos, pos)
        self._set_cursor(pos)

    def handle_mouse_down_move(self, event: MouseEvent):
        assert self._selecting_pivot is not None
        assert self._has_selection()
        self._debug("mouse_down_move")
        # We convert mouse position into widget coordinates
        # before setting the cursor event.
        pos = self._mouse_to_pos(event.x - self.x, event.y - self.y)

        pivot = self._selecting_pivot
        if pos < pivot:
            # If the cursor is before the pivot, we select from the cursor to the pivot.
            self._set_selection(pos, pivot)
        else:
            # If the cursor is after the pivot, we select from the pivot to the cursor.
            self._set_selection(pivot, pos)
        # Set the cursor event to the current cursor position.
        self._set_cursor(pos)

    def handle_mouse_up(self, event: MouseEvent):
        self._debug("mouse_up")
        self._selecting_pivot = None

    def handle_focus_in(self) -> bool:
        self._debug("focus_in")
        self._set_focus(True)
        if not self._cursor_event:
            self._set_cursor(0)
        return True

    def handle_focus_out(self):
        self._debug("focus_out")
        self._set_focus(False)
        self._set_selection(None)

    def handle_text_input(self, text: str):
        self._debug("text_input", repr(text))
        if self._has_selection():
            # Replace selected text
            start, end = self._get_selection()
            in_text = self._text.text
            out_text = in_text[:start] + text + in_text[end:]
            self._text.text = out_text
            self._set_cursor(start + len(text))
            self._set_selection(None)
        else:
            # Normal insertion
            in_text = self._text.text
            in_pos = self._get_cursor()
            out_text = in_text[:in_pos] + text + in_text[in_pos:]
            out_pos = in_pos + len(text)
            self._text.text = out_text
            self._set_cursor(out_pos)

    def handle_keydown(self, key: KeyboardEntry):
        self._debug("key_down")
        if key.backspace or key.delete:
            selection = self._get_selection()
            if selection and selection[0] != selection[1]:
                # Delete selected text
                start, end = selection
                in_text = self._text.text
                out_text = in_text[:start] + in_text[end:]
                self._text.text = out_text
                self._set_cursor(start)
                self._set_selection(None)
            else:
                # Normal backspace or delete
                in_text = self._text.text
                in_pos = self._get_cursor()
                if key.backspace:
                    if key.ctrl:
                        out_pos = get_previous_word_start_position(in_text, in_pos)
                    else:
                        out_pos = max(0, in_pos - 1)
                    next_pos = in_pos
                else:
                    out_pos = in_pos
                    if key.ctrl:
                        next_pos = get_next_word_end_position(in_text, in_pos)
                    else:
                        next_pos = in_pos + 1
                out_text = in_text[:out_pos] + in_text[next_pos:]
                self._text.text = out_text
                self._set_cursor(out_pos)
        elif key.left:
            ret = compute_key_x(
                text=self._text.text,
                cursor=self._get_cursor(),
                selection=self._get_selection(),
                ctrl=key.ctrl,
                shift=key.shift,
                right=False,
            )
            self._set_cursor(ret.out_pos)
            self._set_selection(*ret.out_selection)
        elif key.right:
            ret = compute_key_x(
                text=self._text.text,
                cursor=self._get_cursor(),
                selection=self._get_selection(),
                ctrl=key.ctrl,
                shift=key.shift,
                right=True,
            )
            self._set_cursor(ret.out_pos)
            self._set_selection(*ret.out_selection)
        elif key.ctrl:
            if key.a:
                # Select all
                self._set_selection(0, len(self._text.text))
                self._set_cursor(len(self._text.text))
            elif key.c and self._has_selection():
                start, end = self._get_selection()
                content = self._text.text[start:end]
                self.get_window().set_clipboard(content)
                self._debug("copied", repr(content))
            elif key.v:
                inserted = self.get_window().get_clipboard()
                if inserted:
                    in_text = self._text.text
                    if self._has_selection():
                        start, end = self._get_selection()
                        out_text = in_text[:start] + inserted + in_text[end:]
                        self._text.text = out_text
                        self._set_cursor(start + len(inserted))
                        self._set_selection(None)
                    else:
                        in_pos = self._get_cursor()
                        out_text = in_text[:in_pos] + inserted + in_text[in_pos:]
                        self._text.text = out_text
                        self._set_cursor(in_pos + len(inserted))

    @classmethod
    def _get_cursor_rect(cls, cursor: _CursorDefinition, rendered: RenderedText):
        cursor_width = 2
        cursor_height = rendered.font_sizes.ascender + rendered.font_sizes.descender
        return pygame.Rect(cursor.x, cursor.y, cursor_width, cursor_height)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        text_surface = self._control.render(window, width, height)
        rendered = self._text._rendered
        surface = text_surface.copy()

        # Draw cursor if focused
        if self._has_focus() and self._cursor_event:
            cursor_def = self._cursor_event.handle(rendered)
            cursor = self._get_cursor_rect(cursor_def, rendered)
            pygame.gfxdraw.box(surface, cursor, Colors.black)

        return surface
