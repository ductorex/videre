from abc import ABC, abstractmethod

from videre.colors import Color
from videre.core.caret_position import CaretPosition
from videre.core.constants import TextAlign
from videre.core.rectangle import Rectangle


class Rendering(ABC):
    __slots__ = ()

    @abstractmethod
    def get_width(self) -> int: ...

    @abstractmethod
    def get_height(self) -> int: ...

    @abstractmethod
    def get_at(self, position: tuple[int, int]) -> Color:
        """Return the color of pixel at given position."""
        ...


class CursorState(ABC):
    """Backend-owned navigation state for a TextInput cursor. Carries
    whatever internal info the backend needs to keep arrow-key
    movement unambiguous in mixed bidi.

    Three properties are exposed to consumers:

    - `pos`: the source position the state points at — used to slice
      the source string for insertion, selection, etc.
    - `visual_pos`: the position in the *visual* codepoint sequence
      (= the sequence of clusters in left-to-right pixel order). For
      the legacy backend, `visual_pos == pos` (no bidi). For a
      shaped backend, may be a globally-counted index across lines.
      Used by `TextInput` to express selections in visual order so
      the highlighted region is always a contiguous ribbon on screen,
      even when the underlying source positions are not contiguous in
      bidi-mixed text.
    - `pixel`: the visual caret to paint. Unlike `pos_to_pixel(pos)`,
      this is unambiguous at LTR/RTL boundaries because the backend
      derives it from the same internal anchor as `next_visual` /
      `prev_visual`, so the caret painted on screen matches exactly
      where the next arrow press will move from.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def pos(self) -> int: ...

    @property
    @abstractmethod
    def visual_pos(self) -> int: ...

    @property
    @abstractmethod
    def pixel(self) -> CaretPosition: ...


class TextRenderingResult(ABC):
    """Common surface that the cursor / hit-test code in `TextInput` relies on.

    Visual navigation uses a `CursorState` object each backend owns.
    TextInput stores it next to the source-position cursor and feeds
    it back unchanged to `next_visual` / `prev_visual` etc. Direct
    source-position queries (`pos_to_pixel`, `pixel_to_pos`) don't
    take a state and may be ambiguous at LTR/RTL boundaries on a
    shaped backend; the state-based path is the reliable one for
    arrow / mouse navigation.
    """

    __slots__ = ()

    @abstractmethod
    def get_width(self) -> int:
        """Get width of text rendering surface"""
        ...

    @abstractmethod
    def get_height(self) -> int:
        """Get height of text rendering surface"""
        ...

    @abstractmethod
    def pos_to_pixel(self, pos: int) -> CaretPosition: ...

    @abstractmethod
    def pixel_to_pos(self, x: int, y: int) -> int: ...

    @abstractmethod
    def visual_state(self, pos: int) -> CursorState:
        """Build an initial visual navigation state anchored on a
        source position. At a bidi boundary the backend picks a
        convention (typically the leftmost-visual cursor matching the
        source pos)."""
        ...

    @abstractmethod
    def visual_state_at(self, visual_pos: int) -> CursorState:
        """Build a navigation state anchored on a visual position.
        Inverse of reading `state.visual_pos`. Used when restoring a
        selection endpoint from a stored visual index."""
        ...

    @abstractmethod
    def visual_state_at_pixel(self, x: int, y: int) -> CursorState:
        """Build a navigation state from a pixel coordinate. Read the
        derived source position from `state.pos`."""
        ...

    @abstractmethod
    def next_visual(self, state: CursorState) -> CursorState:
        """One visual glyph-step to the right. Clamps at end of
        document (returns an equal state)."""
        ...

    @abstractmethod
    def prev_visual(self, state: CursorState) -> CursorState:
        """Symmetric to `next_visual`."""
        ...

    @abstractmethod
    def next_visual_word(self, state: CursorState, text: str) -> CursorState:
        """Next word boundary visually to the right. `text` is the
        source string the backend can use to compute word boundaries
        (via cursword on the source) and project them through the
        layout."""
        ...

    @abstractmethod
    def prev_visual_word(self, state: CursorState, text: str) -> CursorState:
        """Symmetric to `next_visual_word`."""
        ...

    @abstractmethod
    def visual_range_to_source_set(self, start: int, end: int) -> frozenset[int]:
        """Source indices covered by the half-open visual range
        `[start, end)`. For LTR-only content the result is
        ``frozenset(range(start, end))``; in bidi-mixed content it may
        be non-contiguous. Used by `TextInput` for selection-based
        editing (delete, copy)."""
        ...

    @abstractmethod
    def visual_selection_rects(self, start: int, end: int) -> list[Rectangle]:
        """Pixel rectangles to paint for a contiguous visual selection
        `[start, end)`. One rectangle per visual line touched by the
        range. Used by the selection-highlight pass."""
        ...

    @abstractmethod
    def total_visual_count(self) -> int:
        """Number of visual positions in the rendered text — the
        upper bound that a `visual_pos` can take. Used by `TextInput`
        for Ctrl+A (select-all)."""
        ...


class AbstractTextRendering(ABC):
    __slots__ = ()

    @abstractmethod
    def render_char(self, c: str, color: Color | None = None) -> Rendering: ...

    @abstractmethod
    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[TextRenderingResult, Rendering]: ...
