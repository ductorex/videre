import pygame
import pygame.gfxdraw
from cursword import get_next_word_end_position, get_previous_word_start_position

from videre.colors import Colors
from videre.core.caret_position import CaretPosition
from videre.core.events import KeyboardEntry, MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_backend import Pygame, Surface, Rect
from videre.layouts.abstractlayout import AbstractLayout
from videre.layouts.container import Container
from videre.layouts.div.div import Div
from videre.widgets.text import Text
from videre.widgets.textinput.keyboard_handling import compute_key_x
from videre.widgets.widget import Widget


class TextInput(AbstractLayout):
    __wprops__ = {"has_focus", "name"}
    __slots__ = ("_text", "_container", "_cursor_pos", "_selecting_pivot")
    __size__ = 1
    __capture_mouse__ = True
    __padding__ = Div.__style__.default.padding
    __border__ = Div.__style__.default.border

    def __init__(self, text: str = "", size: int = 0, border: bool = True, **kwargs):
        # self._text = _InputText(text="Hello, 炎炎ノ消防隊: ", size=80)
        self._text = Text(text=text, size=size, height_delta=0)
        container_border = self.__border__ if border else None
        container_padding = self.__padding__ if border else None
        self._container = Container(
            self._text,
            background_color=(240, 240, 240),
            border=container_border,
            padding=container_padding,
        )
        super().__init__([self._container], **kwargs)
        self._cursor_pos: int | None = None
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

    def _get_selection(self) -> tuple[int, int] | None:
        return self.__selection()

    def _required_selection(self) -> tuple[int, int]:
        selection = self.__selection()
        assert selection is not None
        return selection

    def _set_selection(self, start: int | None = None, end: int | None = None):
        prev_selection = self.__selection()
        selection: tuple[int, int] | None
        if start is None and end is None:
            selection = None
        elif start is None:
            assert end is not None
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
        rendered = self._text._rendered
        assert rendered is not None
        return rendered.pixel_to_pos(x, y)

    def _set_cursor(self, pos: int):
        if self._cursor_pos != pos:
            self._cursor_pos = pos
            self.update()

    def _get_cursor(self) -> int:
        assert self._cursor_pos is not None
        return self._cursor_pos

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
        if self._cursor_pos is None:
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
            start, end = self._required_selection()
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
        if key.escape:
            self.get_window().focus_out(self)
        elif key.backspace or key.delete:
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
            assert ret.out_pos is not None
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
            assert ret.out_pos is not None
            self._set_cursor(ret.out_pos)
            self._set_selection(*ret.out_selection)
        elif key.ctrl:
            if key.a:
                # Select all
                self._set_selection(0, len(self._text.text))
                self._set_cursor(len(self._text.text))
            elif key.c and self._has_selection():
                start, end = self._required_selection()
                content = self._text.text[start:end]
                self.get_window().set_clipboard(content)
                self._debug("copied", repr(content))
            elif key.v:
                inserted = self.get_window().get_clipboard()
                if inserted:
                    in_text = self._text.text
                    if self._has_selection():
                        start, end = self._required_selection()
                        out_text = in_text[:start] + inserted + in_text[end:]
                        self._text.text = out_text
                        self._set_cursor(start + len(inserted))
                        self._set_selection(None)
                    else:
                        in_pos = self._get_cursor()
                        out_text = in_text[:in_pos] + inserted + in_text[in_pos:]
                        self._text.text = out_text
                        self._set_cursor(in_pos + len(inserted))

    def _get_cursor_rect(self, caret: CaretPosition):
        container = self._container
        margin = container.padding + container.border.margin()
        cursor_width = 2
        cursor_height = caret.y_bottom - caret.y_top
        return Rect(
            margin.left + caret.x, margin.top + caret.y_top, cursor_width, cursor_height
        )

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Surface:
        text_surface = self._control.render(window, width, height)
        rendered = self._text._rendered
        surface = text_surface.copy()

        # Draw cursor if focused
        if self._has_focus() and self._cursor_pos is not None:
            assert rendered is not None
            caret = rendered.pos_to_pixel(self._cursor_pos)
            cursor_rect = self._get_cursor_rect(caret)
            pygame.gfxdraw.box(surface, cursor_rect, Pygame.new_color(Colors.black))

        return surface
