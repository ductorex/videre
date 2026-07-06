import io
from abc import ABC, abstractmethod
from typing import Iterator

from videre.core.drawer import Drawer
from videre.core.events import VidereEvent
from videre.core.rendering_result import Rendering


class AbstractRenderer(ABC):
    """The rendering half of a backend: turn a `Drawer` into pixels.

    Pure rasterization — no window, event loop or OS state. A backend is free
    to rasterize however it likes (cache or not, software or GPU). Two seams:
    `render_drawer` (paint the root drawer onto the backend's own screen) and
    `materialize` (turn a drawer into its own surface). Instantiable on its own;
    `materialize` needs no windowing, so the rasterization can be benchmarked in
    isolation.
    """

    __slots__ = ()

    @abstractmethod
    def render_drawer(self, drawer: Drawer) -> None:
        """Paint the root `drawer` onto the backend's own screen / framebuffer.

        The once-per-frame root entry. The renderer owns the paint target (the
        pygame display surface, a GPU backend's bound framebuffer, …) and any
        frame-to-frame optimization: a software backend may skip an unchanged
        frame and cycle a per-frame cache, while an immediate-mode GPU backend
        just redraws. Draws and returns nothing; to obtain a drawer as its own
        surface, use `materialize`.
        """
        ...

    @abstractmethod
    def materialize(self, drawer: Drawer) -> Rendering:
        """Turn `drawer` into its own surface — a nested sub-drawer, or a
        one-shot rasterization in tests.

        The contract says nothing about *how*: a software backend may memoize
        materialized surfaces by Drawer value (Drawers hash/compare by content),
        while an immediate-mode GPU backend may render to a texture. Whichever
        the strategy, callers must treat the result as read-only
        (`Drawer.copy()` shields in-place edits).
        """
        ...


class AbstractWindowing(ABC):
    """The windowing half of a backend: the OS-facing surface of contact.

    A passive provider — it owns the window, its current size and the cursor. It
    does two backend-specific jobs and nothing else: translate OS events into
    `VidereEvent`s (`poll_events`) and present the painted frame (`present`). It
    drives no loop and holds no application callbacks; `Window` owns the loop and
    calls `start` → (`poll_events`, `present`, `tick`)* → `stop`.
    """

    __slots__ = ("_width", "_height", "_title", "_hide", "_cursor_is_default")

    def __init__(self, width: int, height: int, title: str, hide: bool = False) -> None:
        self._width = width
        self._height = height
        self._title = title
        self._hide = hide
        self._cursor_is_default = True

    @property
    def width(self) -> int:
        # NB: width must always be current screen width, so that code can get screen width from this property.
        return self._width

    @property
    def height(self) -> int:
        # NB: height must always be current screen height, so that code can get screen height from this property.
        return self._height

    @property
    def title(self) -> str:
        return self._title

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def poll_events(self) -> Iterator[VidereEvent]:
        """Drain the OS event queue and yield translated `VidereEvent`s.

        Backend-specific: OS events become videre events, the window's own
        events are handled internally (a resize updates the tracked size; a
        close yields an `ExitEvent`), and any quirk-compensation (e.g. a
        synthetic hover motion) is emitted here. `Window` dispatches whatever is
        yielded and stops on an `ExitEvent`.
        """
        ...

    @abstractmethod
    def present(self) -> None:
        """Present the frame the renderer just painted (swap / flip buffers)."""
        ...

    @abstractmethod
    def tick(self, fps: int) -> None:
        """Wait so the frame rate is about `fps`; no wait when `fps <= 0`."""
        ...

    @abstractmethod
    def screenshot(self) -> io.BytesIO: ...

    @abstractmethod
    def resize_screen(self, width: int, height: int) -> None: ...

    @abstractmethod
    def post_event(self, event: VidereEvent) -> None:
        """Inject a videre event so it resurfaces through `poll_events` — the
        real OS event path, used by `FakeUser`."""
        ...

    @abstractmethod
    def _set_text_cursor(self) -> None: ...

    @abstractmethod
    def _set_default_cursor(self) -> None: ...

    def set_text_cursor(self) -> None:
        self._set_text_cursor()
        self._cursor_is_default = False

    def set_default_cursor(self) -> None:
        self._set_default_cursor()
        self._cursor_is_default = True

    def cursor_is_default(self) -> bool:
        return self._cursor_is_default

    def _handle_resize(self, width: int, height: int) -> None:
        self._width, self._height = width, height


class AbstractBackend(ABC):
    """A backend: a provider of a coherent (renderer, windowing) pair.

    `Window` asks one backend for both halves and never mixes providers, so a
    renderer and a windowing from the same backend may freely share types or an
    OS context (e.g. an OpenGL context for a GPU backend). This is what `Window`
    receives and what `PygameBackend` (and a future `SfmlBackend`) implement.
    """

    __slots__ = ()

    @abstractmethod
    def create_renderer(self) -> AbstractRenderer: ...

    @abstractmethod
    def create_windowing(
        self,
        *,
        width: int,
        height: int,
        title: str,
        hide: bool = False,
        dpi_aware: bool = False,
    ) -> AbstractWindowing: ...
