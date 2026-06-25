from abc import ABC, abstractmethod

from videre.colors import Color
from videre.core.caret_position import CaretPosition
from videre.core.constants import TextAlign, TextSpacePolicy
from videre.core.drawer import Drawer
from videre.core.text_editing import EditUnit


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
    """Cursor / hit-test + size contract that `TextInput` and the Drawer
    sizing path rely on.

    Navigation is state-based: obtain a `CursorState` (via `visual_state` /
    `visual_state_at` / `visual_state_at_pixel`), feed it back unchanged to
    `next_visual` / `prev_visual` / `next_visual_word` / `prev_visual_word`,
    and read `pos` / `visual_pos` / `pixel` off it. The state-based path keeps
    navigation unambiguous at LTR/RTL boundaries on a bidi-aware backend.
    `get_width` / `get_height` give the rendered extent — needed by the
    surface-less sizing path (`Drawer` / text_sizing), where there is no
    `Rendering` to measure.

    Deliberately NOT part of this contract (only ever used internally by an
    implementation, never through the interface): the source<->pixel mapping
    that fills `CursorState.pixel`, and the selection-rectangle computation
    (each backend paints the highlight itself inside `render_text`).
    """

    __slots__ = ()

    @abstractmethod
    def get_width(self) -> int:
        """Rendered width in pixels (used by the surface-less sizing path)."""
        ...

    @abstractmethod
    def get_height(self) -> int:
        """Rendered height in pixels (used by the surface-less sizing path)."""
        ...

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
    def total_visual_count(self) -> int:
        """Number of visual positions in the rendered text — the
        upper bound that a `visual_pos` can take. Used by `TextInput`
        for Ctrl+A (select-all)."""
        ...


class AbstractTextRendering(ABC):
    __slots__ = ()

    @abstractmethod
    def render_char(self, c: str, color: Color | None = None) -> Drawer: ...

    @abstractmethod
    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
        underline: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[TextRenderingResult, Drawer]: ...

    @abstractmethod
    def document(self, text: str) -> "AbstractTextDocument":
        """Build a cacheable document for `text` (text-only shape, replayed per
        width by `document.render`). See docs/text-document-and-contract.md."""
        ...


class AbstractTextDocument(ABC):
    """A shaped document: the text-only half of rendering — partition + shape +
    edit-unit segmentation — meant to be cached across resizes. `render(width,
    ...)` replays only the width-dependent half (wrap + layout + paint), so a
    resize never re-shapes. `edit_units` is the single segmentation shared with
    `TextInput`. See docs/text-document-and-contract.md.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def text(self) -> str: ...

    @property
    @abstractmethod
    def edit_units(self) -> tuple[EditUnit, ...]: ...

    @abstractmethod
    def layout(
        self,
        width: int | None = None,
        *,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
    ) -> TextRenderingResult:
        """Width-dependent layout WITHOUT painting: the caret / hit-test
        `TextRenderingResult` alone, from the same computation `render` paints
        from (a shared per-width cache, so `layout` then `render` at one width
        costs a single layout). For navigation / measurement that must not force
        a repaint — e.g. refreshing the caret between a text mutation and the next
        draw. See docs/text-document-and-contract.md."""
        ...

    @abstractmethod
    def render(
        self,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
        underline: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[TextRenderingResult, Drawer]: ...
