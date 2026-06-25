import io
from abc import ABC, abstractmethod
from typing import Callable

from videre.core.constants import WINDOW_FPS
from videre.core.drawer import Drawer
from videre.core.events import VidereEvent
from videre.core.rendering_result import Rendering
from videre.core.tasks import TaskManager, VidereTask


class AbstractRenderer(ABC):
    """The rendering half of a backend: turn a `Drawer` into pixels.

    Pure rasterization — no window, event loop or OS state. A backend is free
    to rasterize however it likes (cache or not, software or GPU); the only
    obligation is `render_drawer`. Instantiable on its own (no windowing), so
    the rasterization can be benchmarked in isolation.
    """

    __slots__ = ()

    @abstractmethod
    def render_drawer(self, drawer: Drawer, dst: Rendering | None = None) -> Rendering:
        """Rasterize a Drawer to a Rendering — the sole rendering seam.

        Replay `drawer`'s commands and return the surface. With `dst` given,
        paint onto it (the root screen, from `Window._refresh`) and return it;
        with `dst=None`, produce a fresh surface (a nested sub-drawer, or a
        one-shot rasterization in tests).

        The contract says nothing about *how*: a software backend may memoize
        materialized surfaces by Drawer value (Drawers hash/compare by content),
        while an immediate-mode GPU backend may flatten the tree into draw calls
        and cache nothing. Whichever the strategy, callers must treat a returned
        surface as read-only (`Drawer.copy()` shields in-place edits).
        """
        ...


class AbstractWindowing(ABC):
    """The windowing half of a backend: the OS-facing surface of contact.

    Owns the window, the screen size, the event loop and the cursor; carries all
    the mutable backend state. It produces a screen `Rendering` and hands it to
    the `render_manager` (`Window._refresh`), which paints it with a renderer —
    so windowing never calls `render_drawer` itself and needs no reference to the
    renderer.
    """

    __slots__ = (
        "_width",
        "_height",
        "_title",
        "_hide",
        "_fps",
        "_nb_frames",
        "_event_dispatcher",
        "_render_manager",
        "_task_manager",
        "_cursor_is_default",
        "_running",
    )

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        event_manager: Callable[[VidereEvent], VidereTask | None],
        render_manager: Callable[[Rendering], None],
        task_manager: TaskManager,
        hide: bool = False,
        fps: int = WINDOW_FPS,
    ) -> None:
        self._width = width
        self._height = height
        self._title = title
        self._hide = hide
        self._fps = fps
        self._nb_frames: int = 0
        self._event_dispatcher = event_manager
        self._render_manager = render_manager
        self._task_manager = task_manager
        self._running: bool = True

        self._cursor_is_default = True

    @property
    def running(self) -> bool:
        return self._running

    @running.setter
    def running(self, running: bool) -> None:
        self._running = running

    @property
    def nb_frames(self) -> int:
        return self._nb_frames

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def title(self) -> str:
        return self._title

    @abstractmethod
    def _set_text_cursor(self) -> None: ...

    @abstractmethod
    def _set_default_cursor(self) -> None: ...

    @abstractmethod
    def screenshot(self) -> io.BytesIO: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def resize_screen(self, width: int, height: int) -> None: ...

    @abstractmethod
    def _step(self, fps: int | None = None) -> None:
        """
        Render a frame.
        If fps is None, should use self._fps.
        If fps is valid (> 0), should wait enough so that interface frame rate is almost fps.
        If fps is invalid (<= 0), do not wait. May be used to get a single step without any waiting.
        """
        ...

    def run(self) -> None:
        try:
            self.start()
            while self._running:
                self.step()
        finally:
            self.stop()

    def step(self, fps: int | None = None) -> None:
        self._step(fps)
        self._nb_frames += 1

    def set_text_cursor(self) -> None:
        self._set_text_cursor()
        self._cursor_is_default = False

    def set_default_cursor(self) -> None:
        self._set_default_cursor()
        self._cursor_is_default = True

    def cursor_is_default(self) -> bool:
        return self._cursor_is_default

    def _handle_exit(self) -> None:
        self._running = False

    def _handle_resize(self, width: int, height: int) -> None:
        self._width, self._height = width, height

    @abstractmethod
    def post_event(self, event: VidereEvent) -> None: ...


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
        event_manager: Callable[[VidereEvent], VidereTask | None],
        render_manager: Callable[[Rendering], None],
        task_manager: TaskManager,
        hide: bool = False,
        fps: int = WINDOW_FPS,
    ) -> AbstractWindowing: ...
