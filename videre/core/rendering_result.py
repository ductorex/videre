from typing import Protocol

from videre.core.caret_position import CaretPosition
from videre.core.pygame_backend import Rect, Surface


class RenderingResult(Protocol):
    surface: Surface


class CursorState(Protocol):
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

    @property
    def pos(self) -> int: ...

    @property
    def visual_pos(self) -> int: ...

    @property
    def pixel(self) -> CaretPosition: ...


class TextRenderingResult(Protocol):
    """Common surface that the cursor / hit-test code in `TextInput` relies on.

    Visual navigation uses a `CursorState` object each backend owns.
    TextInput stores it next to the source-position cursor and feeds
    it back unchanged to `next_visual` / `prev_visual` etc. Direct
    source-position queries (`pos_to_pixel`, `pixel_to_pos`) don't
    take a state and may be ambiguous at LTR/RTL boundaries on a
    shaped backend; the state-based path is the reliable one for
    arrow / mouse navigation.
    """

    def pos_to_pixel(self, pos: int) -> CaretPosition: ...

    def pixel_to_pos(self, x: int, y: int) -> int: ...

    def visual_state(self, pos: int) -> CursorState:
        """Build an initial visual navigation state anchored on a
        source position. At a bidi boundary the backend picks a
        convention (typically the leftmost-visual cursor matching the
        source pos)."""
        ...

    def visual_state_at(self, visual_pos: int) -> CursorState:
        """Build a navigation state anchored on a visual position.
        Inverse of reading `state.visual_pos`. Used when restoring a
        selection endpoint from a stored visual index."""
        ...

    def visual_state_at_pixel(self, x: int, y: int) -> CursorState:
        """Build a navigation state from a pixel coordinate. Read the
        derived source position from `state.pos`."""
        ...

    def next_visual(self, state: CursorState) -> CursorState:
        """One visual glyph-step to the right. Clamps at end of
        document (returns an equal state)."""
        ...

    def prev_visual(self, state: CursorState) -> CursorState:
        """Symmetric to `next_visual`."""
        ...

    def next_visual_word(self, state: CursorState, text: str) -> CursorState:
        """Next word boundary visually to the right. `text` is the
        source string the backend can use to compute word boundaries
        (via cursword on the source) and project them through the
        layout."""
        ...

    def prev_visual_word(self, state: CursorState, text: str) -> CursorState:
        """Symmetric to `next_visual_word`."""
        ...

    def visual_range_to_source_set(self, start: int, end: int) -> frozenset[int]:
        """Source indices covered by the half-open visual range
        `[start, end)`. For LTR-only content the result is
        ``frozenset(range(start, end))``; in bidi-mixed content it may
        be non-contiguous. Used by `TextInput` for selection-based
        editing (delete, copy)."""
        ...

    def visual_selection_rects(self, start: int, end: int) -> list[Rect]:
        """Pixel rectangles to paint for a contiguous visual selection
        `[start, end)`. One rectangle per visual line touched by the
        range. Used by the selection-highlight pass."""
        ...

    def total_visual_count(self) -> int:
        """Number of visual positions in the rendered text — the
        upper bound that a `visual_pos` can take. Used by `TextInput`
        for Ctrl+A (select-all)."""
        ...
