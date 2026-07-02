import io
from abc import ABC, abstractmethod
from typing import Callable

from videre.core.constants import WINDOW_FPS
from videre.core.dpi import DevicePx, LogicalPx, to_device
from videre.core.drawer import Drawer
from videre.core.events import VidereEvent
from videre.core.rendering_result import Rendering
from videre.core.tasks import TaskManager, VidereTask


class AbstractRenderer(ABC):
    """The rendering half of a backend: turn a `Drawer` into pixels.

    Pure rasterization — no window, event loop or OS state. A backend is free
    to rasterize however it likes (cache or not, software or GPU). Two seams:
    `render_drawer` (paint a drawer onto a surface) and `materialize` (turn a
    drawer into its own surface). Instantiable on its own (no windowing), so
    the rasterization can be benchmarked in isolation.

    DPI is not the renderer's concern: Drawer commands are already in
    device pixels (the scale is applied at record time — see
    videre/core/drawing.py), so a renderer allocates each drawer's
    `device_width` × `device_height` and replays commands 1:1.
    """

    __slots__ = ()

    @abstractmethod
    def render_drawer(self, drawer: Drawer, dst: Rendering) -> None:
        """Paint `drawer`'s commands onto `dst` — the root frame paint.

        `dst` (the screen, from `Window._refresh`) must cover the drawer. This
        is the once-per-frame root entry, so a backend may use it as the
        boundary to cycle any per-frame cache. It draws onto `dst` and returns
        nothing; to obtain a drawer as its own surface, use `materialize`.
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
        "_dpi_aware",
        "_scale_factor",
        "_device_width",
        "_device_height",
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
        dpi_aware: bool = False,
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
        # DPI opt-in: when True, the windowing declares OS DPI awareness,
        # opens the window at device size, reports the scale through
        # `scale_factor` and converts pointer coordinates back to logical.
        # Everything else stays logical (the scale is applied at record
        # time — see videre/core/drawing.py).
        self._dpi_aware = dpi_aware
        self._scale_factor: float = 1.0
        # Real OS buffer size (`_set_device_size`); -1 = window not open yet.
        self._device_width: int = -1
        self._device_height: int = -1

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
    def width(self) -> LogicalPx:
        return self._width

    @property
    def height(self) -> LogicalPx:
        return self._height

    @property
    def title(self) -> str:
        return self._title

    @property
    def scale_factor(self) -> float:
        """Device-pixel ratio of the window (1.0 = 100%, 1.5 = 150%).

        Whatever the platform mechanism, a windowing reduces it to this one
        multiplier. Stays 1.0 unless the windowing was created with
        `dpi_aware=True` *and* the platform reports a scale."""
        return self._scale_factor

    @property
    def device_width(self) -> DevicePx:
        """Width of the OS screen buffer, in device pixels.

        Stored, not derived: after an OS resize the buffer has whatever
        size the OS chose, which can differ by one pixel from
        ceil(logical width × scale). E.g. at 150%: buffer 484 → logical
        floor(484/1.5) = 322 → re-derived ceil(322 × 1.5) = 483 ≠ 484.
        Before the window opens, returns the expected size instead."""
        if self._device_width < 0:
            return to_device(self._width, self._scale_factor)
        return self._device_width

    @property
    def device_height(self) -> DevicePx:
        """Height of the OS screen buffer, in device pixels (see
        `device_width`)."""
        if self._device_height < 0:
            return to_device(self._height, self._scale_factor)
        return self._device_height

    def _set_device_size(self, width: DevicePx, height: DevicePx) -> None:
        """Record the real buffer size, on every screen (re)allocation."""
        self._device_width, self._device_height = width, height

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
    def create_renderer(self) -> AbstractRenderer:
        """Create the rendering half. Scale-free: Drawer commands reach
        the renderer already in device pixels."""
        ...

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
        dpi_aware: bool = False,
    ) -> AbstractWindowing: ...
