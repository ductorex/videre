from typing import Self

from cursword import get_next_word_end_position, get_previous_word_start_position

from videre.colors import Colors
from videre.core.caret_position import CaretPosition
from videre.core.clipboard import Clipboard
from videre.core.events import KeyboardEntry, MouseEvent
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import CursorState, Rendering
from videre.core.text_editing import (
    EditUnit,
    align_to_boundary,
    expand_to_edit_units,
    next_edit_unit,
    previous_edit_unit,
    segment_edit_units,
)
from videre.layouts.abstractlayout import AbstractLayout
from videre.layouts.container import Container
from videre.layouts.div.div import Div
from videre.widgets.text import Text
from videre.widgets.textinput.keyboard_handling import compute_key_x
from videre.widgets.widget import Widget
from videre.widgets.widget_utils import MouseOwnership


class TextInput(AbstractLayout):
    __wprops__ = {"has_focus", "name"}
    __slots__ = (
        "_text",
        "_container",
        "_cursor_pos",
        "_cursor_state",
        "_selecting_pivot",
        "_edit_segmentation",
    )
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
        # Source-position cursor: authoritative for `text` slicing
        # (insertion, deletion). Initialized eagerly to the end of the
        # text — a convention that needs no rendering. The visual
        # `_cursor_state` is a cache derived from the rendering and is
        # filled lazily (see `_ensure_state`); it stays None until the
        # first navigation or the first draw with focus, both of which
        # are post-render.
        self._cursor_pos: int = len(self._text.text)
        self._cursor_state: CursorState | None = None
        self._selecting_pivot: int | None = None
        # Cache of (text, edit_units, boundaries) for the current text,
        # so editing/navigation re-uses one segmentation per keystroke
        # instead of re-segmenting on every operation.
        self._edit_segmentation: tuple[str, tuple[EditUnit, ...], tuple[int, ...]] | (
            None
        ) = None

        self._set_focus(False)
        self._set_selection(None)

    @property
    def value(self) -> str:
        """Returns the current text value."""
        return self._text.text

    @value.setter
    def value(self, text: str):
        """Sets the text value."""
        self._text.text = text
        self._set_cursor_to_pos(len(text))
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

    def _set_cursor_to_pos(self, pos: int):
        """Move the cursor to a source position. Drops the cached
        visual state so the next `_ensure_state` re-derives it from
        the current rendering. Use this for mutations (insertion,
        deletion, value setter) and for moves where only the source
        position is known."""
        if self._cursor_pos != pos or self._cursor_state is not None:
            self._cursor_pos = pos
            self._cursor_state = None
            self.update()

    def _set_cursor_to_state(self, state: CursorState):
        """Move the cursor to a backend-produced navigation state.
        Caches the state so consecutive arrow presses stay
        bidi-unambiguous on the shaped backend. Use this after
        navigation (mouse click, mouse drag, arrow keys) where the
        backend has handed out a state."""
        self._cursor_pos = state.pos
        self._cursor_state = state
        self.update()

    def _get_cursor(self) -> int:
        return self._cursor_pos

    def _ensure_state(self) -> CursorState:
        """Return a valid navigation state for the current cursor.
        Derives one from the backend if the cache is empty."""
        if self._cursor_state is None:
            rendered = self._text._rendered
            assert rendered is not None
            self._cursor_state = rendered.visual_state(self._cursor_pos)
        return self._cursor_state

    def _segmentation(self) -> tuple[tuple[EditUnit, ...], tuple[int, ...]]:
        """Return `(edit_units, boundaries)` for the current text, cached.

        `boundaries` is the sorted tuple of edit-unit boundary offsets
        (`(0, *(u.source_end for u in units))`), used to snap positions
        onto grapheme-cluster edges. Re-computed only when `text` changes."""
        text = self._text.text
        cache = self._edit_segmentation
        if cache is None or cache[0] != text:
            units = segment_edit_units(text)
            boundaries = (0, *(unit.source_end for unit in units))
            cache = (text, units, boundaries)
            self._edit_segmentation = cache
        return cache[1], cache[2]

    def _snap_state_to_cluster(
        self, state: CursorState, direction: int = 0
    ) -> CursorState:
        """Snap a navigation state's source position onto an edit-unit
        boundary, re-deriving the state only when it actually moves. On a
        bidi-aware backend the click/step already lands on a cluster edge,
        so this is a no-op and the original (bidi-anchored) state is kept."""
        _, boundaries = self._segmentation()
        snapped = align_to_boundary(boundaries, state.pos, direction)
        if snapped == state.pos:
            return state
        rendered = self._text._rendered
        assert rendered is not None
        return rendered.visual_state(snapped)

    def _selection_source_indices(self) -> tuple[int, ...]:
        """Sorted tuple of source indices covered by the current
        selection (which is stored in visual order). Empty when no
        selection or when the visual range is degenerate.

        The raw visual-to-source set is expanded to whole edit units, so a
        selection that visually clips a multi-codepoint grapheme still
        deletes / copies the entire cluster (never a partial one)."""
        selection = self._get_selection()
        if selection is None or selection[0] == selection[1]:
            return ()
        rendered = self._text._rendered
        assert rendered is not None
        start, end = selection
        raw = rendered.visual_range_to_source_set(start, end)
        units, _ = self._segmentation()
        return tuple(sorted(expand_to_edit_units(units, raw)))

    def _delete_selection(self) -> int:
        """Remove the currently selected source indices from `text`
        and clear the selection. Return the new cursor source
        position (the smallest source index removed, which is where
        any follow-up insertion belongs)."""
        indices = self._selection_source_indices()
        if not indices:
            self._set_selection(None)
            return self._get_cursor()
        keep = frozenset(indices)
        in_text = self._text.text
        out_text = "".join(c for i, c in enumerate(in_text) if i not in keep)
        cursor = indices[0]
        self._text.text = out_text
        self._set_cursor_to_pos(cursor)
        self._set_selection(None)
        return cursor

    def _selection_text(self) -> str:
        """Source-order concatenation of the codepoints under the
        current selection. Empty string when no selection. Used by
        Ctrl+C: copy preserves the source order so pasting into
        another bidi-aware app re-renders correctly."""
        indices = self._selection_source_indices()
        if not indices:
            return ""
        in_text = self._text.text
        return "".join(in_text[i] for i in indices)

    def handle_mouse_enter(self, event: MouseEvent):
        self.get_window().backend.set_text_cursor()

    def handle_mouse_exit(self):
        self.get_window().backend.set_default_cursor()

    def handle_mouse_down(self, event: MouseEvent):
        self._debug("mouse_down")
        # NB: Mouse position is relative to widget parent.
        # Character positions are relative to widget itself.
        # To make correct comparisons between mouse and characters,
        # we convert mouse position into widget coordinates.
        rendered = self._text._rendered
        assert rendered is not None
        state = self._snap_state_to_cluster(
            rendered.visual_state_at_pixel(event.x - self.x, event.y - self.y)
        )
        # `_selecting_pivot` is a visual position (= index in the
        # visual codepoint sequence), so the selection ribbon stays
        # contiguous on screen even when the underlying source range
        # is non-contiguous in bidi-mixed text.
        self._selecting_pivot = state.visual_pos
        self._set_selection(state.visual_pos, state.visual_pos)
        self._set_cursor_to_state(state)

    def handle_mouse_down_move(self, event: MouseEvent):
        assert self._selecting_pivot is not None
        assert self._has_selection()
        self._debug("mouse_down_move")
        rendered = self._text._rendered
        assert rendered is not None
        state = self._snap_state_to_cluster(
            rendered.visual_state_at_pixel(event.x - self.x, event.y - self.y)
        )

        pivot = self._selecting_pivot
        if state.visual_pos < pivot:
            self._set_selection(state.visual_pos, pivot)
        else:
            self._set_selection(pivot, state.visual_pos)
        self._set_cursor_to_state(state)

    def handle_mouse_up(self, event: MouseEvent):
        self._debug("mouse_up")
        self._selecting_pivot = None

    def handle_focus_in(self) -> Self:
        self._debug("focus_in")
        self._set_focus(True)
        return self

    def handle_focus_out(self):
        self._debug("focus_out")
        self._set_focus(False)
        self._set_selection(None)

    def _insert_text(self, inserted: str):
        """Insert `inserted` at the cursor, replacing any selection first.
        Insertion point and the resulting cursor are both aligned to
        edit-unit boundaries so a grapheme cluster is never split open
        (insertion in the middle of a cluster, or a cursor left mid-cluster
        after the text re-segments around the inserted run)."""
        if self._has_selection():
            # Replace selected text. `_delete_selection` removes the
            # source indices under the visual selection and returns the
            # cursor source position where insertion should happen (the
            # start of the first removed edit unit — already a boundary).
            insert_at = self._delete_selection()
        else:
            insert_at = self._get_cursor()
        _, boundaries = self._segmentation()
        insert_at = align_to_boundary(boundaries, insert_at)
        in_text = self._text.text
        self._text.text = in_text[:insert_at] + inserted + in_text[insert_at:]
        _, new_boundaries = self._segmentation()
        self._set_cursor_to_pos(
            align_to_boundary(new_boundaries, insert_at + len(inserted))
        )

    def handle_text_input(self, text: str):
        self._debug("text_input", repr(text))
        self._insert_text(text)

    def handle_keydown(self, key: KeyboardEntry):
        self._debug("key_down")
        if key.escape:
            self.get_window().focus_out(self)
        elif key.backspace or key.delete:
            if self._has_selection() and self._selection_source_indices():
                # Delete selected text — visually-contiguous range,
                # potentially non-contiguous source indices.
                self._delete_selection()
            else:
                # Normal backspace or delete — operate on a whole edit unit
                # (grapheme cluster) so a multi-codepoint cluster is removed
                # as one, even when the cursor sits inside it.
                in_text = self._text.text
                in_pos = self._get_cursor()
                units, _ = self._segmentation()
                if key.backspace:
                    if key.ctrl:
                        out_pos = get_previous_word_start_position(in_text, in_pos)
                        next_pos = in_pos
                    else:
                        unit = previous_edit_unit(units, in_pos)
                        if unit is None:
                            return
                        out_pos = unit.source_start
                        next_pos = unit.source_end
                else:
                    if key.ctrl:
                        out_pos = in_pos
                        next_pos = get_next_word_end_position(in_text, in_pos)
                    else:
                        unit = next_edit_unit(units, in_pos)
                        if unit is None:
                            return
                        out_pos = unit.source_start
                        next_pos = unit.source_end
                out_text = in_text[:out_pos] + in_text[next_pos:]
                self._text.text = out_text
                self._set_cursor_to_pos(out_pos)
        elif key.left or key.right:
            rendered = self._text._rendered
            assert rendered is not None
            _, boundaries = self._segmentation()
            ret = compute_key_x(
                text=self._text.text,
                cursor_state=self._ensure_state(),
                selection=self._get_selection(),
                ctrl=key.ctrl,
                shift=key.shift,
                right=bool(key.right),
                rendered=rendered,
                boundaries=frozenset(boundaries),
            )
            self._set_cursor_to_state(ret.out_state)
            self._set_selection(*ret.out_selection)
        elif key.ctrl:
            if key.A:
                # Select all — span the entire visual sequence so the
                # ribbon covers the whole text on screen.
                rendered = self._text._rendered
                assert rendered is not None
                total = rendered.total_visual_count()
                self._set_selection(0, total)
                self._set_cursor_to_pos(len(self._text.text))
            elif key.C and self._has_selection():
                content = self._selection_text()
                Clipboard.set_clipboard(content)
                self._debug("copied", repr(content))
            elif key.V:
                inserted = Clipboard.get_clipboard()
                if inserted:
                    self._insert_text(inserted)

    def _get_cursor_rect(self, caret: CaretPosition) -> Rectangle:
        container = self._container
        margin = container.padding + container.border.margin()
        cursor_width = 2
        cursor_height = caret.y_bottom - caret.y_top
        return Rectangle(
            margin.left + caret.x, margin.top + caret.y_top, cursor_width, cursor_height
        )

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Rendering:
        backend = window.backend
        text_surface = self._control.render(window, width, height)
        surface = backend.copy(text_surface)

        # Draw cursor if focused. Read the pixel caret from the
        # navigation state so it's unambiguous at LTR/RTL boundaries
        # (the bare `pos_to_pixel(pos)` route picks a convention that
        # may not match where the cursor visually came from after an
        # arrow press).
        if self._has_focus():
            caret = self._ensure_state().pixel
            cursor_rect = self._get_cursor_rect(caret)
            backend.box(surface, cursor_rect, Colors.black)

        return surface
