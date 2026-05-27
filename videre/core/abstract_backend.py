import io
from abc import ABC, abstractmethod
from typing import Callable, Sequence, TypeAlias

from PIL.Image import Image

from videre.colors import Color
from videre.core.constants import WINDOW_FPS
from videre.core.events import VidereEvent
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import AbstractTextRendering, Rendering
from videre.core.tasks import TaskManager, VidereTask

_Position: TypeAlias = tuple[int | float, int | float]


class AbstractBackend(ABC):
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

    @abstractmethod
    def text_rendering(
        self,
        size: int,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int | None = None,
    ) -> AbstractTextRendering: ...

    def set_text_cursor(self) -> None:
        self._set_text_cursor()
        self._cursor_is_default = False

    def set_default_cursor(self) -> None:
        self._set_default_cursor()
        self._cursor_is_default = True

    def cursor_is_default(self) -> bool:
        return self._cursor_is_default

    def zero(self) -> Rendering:
        return self.new_surface(0, 0)

    def _handle_exit(self) -> None:
        self._running = False

    def _handle_resize(self, width: int, height: int) -> None:
        self._width, self._height = width, height

    @abstractmethod
    def new_surface(self, width: int | float, height: int | float) -> Rendering: ...

    @abstractmethod
    def fill(
        self, surface: Rendering, color: Color, rectangle: Rectangle | None = None
    ) -> None: ...

    @abstractmethod
    def blit(self, dst: Rendering, src: Rendering, position: _Position) -> None: ...

    @abstractmethod
    def line(
        self, surface: Rendering, color: Color, start: _Position, end: _Position
    ) -> None: ...

    @abstractmethod
    def rectangle(
        self, surface: Rendering, rectangle: Rectangle, color: Color
    ) -> None: ...

    @abstractmethod
    def box(self, surface: Rendering, rectangle: Rectangle, color: Color) -> None: ...

    @abstractmethod
    def filled_polygon(
        self, surface: Rendering, points: Sequence[_Position], color: Color
    ) -> None: ...

    @abstractmethod
    def smoothscale(
        self, surface: Rendering, width: int | float, height: int | float
    ) -> Rendering: ...

    @abstractmethod
    def copy(self, surface: Rendering) -> Rendering: ...

    @abstractmethod
    def image(self, image: Image) -> Rendering: ...

    @abstractmethod
    def image_from_bytes(self, data: bytes, size: tuple[int, int]) -> Rendering: ...

    @abstractmethod
    def post_event(self, event: VidereEvent) -> None: ...
