import functools
import logging
from typing import Any, Callable, Sequence

from videre.colors import Color, ColorDef, Colors, parse_color
from videre.core.abstract_backend import (
    AbstractBackend,
    AbstractRenderer,
    AbstractWindowing,
)
from videre.core.constants import WINDOW_FPS, Alignment
from videre.core.events import ExitEvent, VidereEvent, WindowResizeEvent
from videre.core.pygame_backend.backend import PygameBackend
from videre.core.rendering_result import AbstractTextRendering
from videre.core.tasks import (
    CallbackTask,
    ExitTask,
    NotificationCallback,
    NotificationTask,
    TaskManager,
    VidereTask,
)
from videre.core.text_rendering import GlyphRasterizer, Shaper, TextRendering
from videre.core.utils import OnEvent, Procedure, launch_thread
from videre.fonts.font_utils import FontUtils
from videre.fonts.provider import FontProvider
from videre.layouts.container import Container
from videre.widgets.button import Button
from videre.widgets.text import Text
from videre.widgets.widget import Widget
from videre.widgets.widget_utils import WidgetByKeyGetter
from videre.windowing.context import Context
from videre.windowing.event_manager import WindowEventManager
from videre.windowing.fancybox import Fancybox
from videre.windowing.fancyclosebutton import FancyCloseButton
from videre.windowing.windowlayout import WindowLayout

logger = logging.getLogger(__name__)


class Window:
    __slots__ = (
        "_exit_code",
        "_exit_exception",
        "_layout",
        "_notification_callbacks",
        "data",
        "_handled_exceptions",
        "_subpixel",
        "_text_shaper",
        "_text_glyph_rasterizer",
        "_event_manager",
        "_task_manager",
        "_renderer",
        "_windowing",
        "_font_size_pts",
        "_font_height",
        "_fps",
        "_running",
        "_nb_frames",
    )

    def __init__(
        self,
        title="Window",
        width=1280,
        height=720,
        background: ColorDef | None = None,
        font_size=14,
        hide=False,
        alert_on_exceptions: Sequence[type[Exception]] = (),
        handle_text_sub_pixels: bool | None = None,
        fps: int = WINDOW_FPS,
        backend: AbstractBackend | None = None,
        dpi_aware: bool = False,
    ):
        self._layout = WindowLayout(parse_color(background or Colors.white))
        self._event_manager = WindowEventManager(self._layout)
        self._task_manager = TaskManager(self._manage_task)
        backend = backend or PygameBackend()
        self._renderer = backend.create_renderer()
        self._windowing = backend.create_windowing(
            width=width,
            height=height,
            title=str(title) or "Window",
            hide=bool(hide),
            dpi_aware=dpi_aware,
        )
        self._fps = fps
        self._running = True
        self._nb_frames = 0
        self._font_size_pts = font_size
        self._font_height: int | None = None

        self._exit_code = 0
        self._exit_exception: Exception | None = None

        # Videre-specific events
        self._notification_callbacks: list[NotificationCallback] = []

        self._handled_exceptions = tuple(alert_on_exceptions)
        self._subpixel: bool = bool(handle_text_sub_pixels)
        self._text_shaper = Shaper()
        self._text_glyph_rasterizer = GlyphRasterizer()

        self.data = None

    def _is_running(self) -> bool:
        return self.running

    def _stop_running(self):
        self.stop()

    def __repr__(self):
        return f"[{type(self).__name__}][{id(self)}]"

    @property
    def renderer(self) -> AbstractRenderer:
        return self._renderer

    @property
    def windowing(self) -> AbstractWindowing:
        return self._windowing

    @property
    def background(self) -> Color:
        return self._layout.background

    @background.setter
    def background(self, value: ColorDef | None):
        self._layout.background = parse_color(value or Colors.white)

    @property
    def nb_frames(self) -> int:
        return self._nb_frames

    @property
    def running(self) -> bool:
        """Whether the event loop is active: `run()` loops while this holds and
        `stop()` clears it."""
        return self._running

    @property
    def symbol_size(self) -> int:
        return int(round(self._font_size_pts * 1.625))

    @property
    def font_height(self) -> int:
        if self._font_height is None:
            _, path = FontProvider().get_font_info(" ")
            self._font_height = FontUtils(path, self._font_size_pts).sized_height
        assert self._font_height is not None
        return self._font_height

    @property
    def controls(self) -> tuple[Widget, ...]:
        return tuple(self._layout.controls)

    @controls.setter
    def controls(self, controls: Sequence[Widget]):
        self._layout.controls = list(controls)

    @property
    def width(self) -> int:
        return self._windowing.width

    @property
    def height(self) -> int:
        return self._windowing.height

    @property
    def title(self) -> str:
        return self._windowing.title

    def text_rendering(
        self,
        size: int | None = None,
        strong: bool = False,
        italic: bool = False,
        height_delta: int = 2,
        compact: bool = True,
    ) -> AbstractTextRendering:
        return TextRendering(
            size=size or self._font_size_pts,
            bold=strong,
            italic=italic,
            height_delta=height_delta,
            compact=compact,
            subpixel=self._subpixel,
            shaper=self._text_shaper,
            rasterizer=self._text_glyph_rasterizer,
        )

    def run(self) -> int:
        if not self._running:
            raise RuntimeError("Window has already run. Cannot run again.")

        self._windowing.start()
        try:
            while self._running:
                self._step()
        finally:
            self._windowing.stop()

        if self._exit_exception:
            raise self._exit_exception
        return self._exit_code

    def stop(self) -> None:
        """Request the event loop to exit after the current frame. `run()`'s
        `finally` then tears the window down once (via the windowing's `stop`),
        so callers must not stop the windowing themselves mid-frame."""
        self._running = False

    def _step(self, fps: int | None = None) -> None:
        """One loop iteration: dispatch pending OS events, paint, present, run
        scheduled tasks, then pace the frame. `fps=0` skips the wait (tests)."""
        for event in self._windowing.poll_events():
            self._dispatch_event(event)
        self._refresh()
        self._windowing.present()
        self._task_manager.manage_tasks()
        self._nb_frames += 1
        self._windowing.tick(self._fps if fps is None else fps)

    def _dispatch_event(self, event: VidereEvent) -> None:
        # Window-level events are handled here; everything else goes to the
        # widget tree via the event manager.
        if isinstance(event, ExitEvent):
            self.stop()
            return
        if isinstance(event, WindowResizeEvent):
            # A resize is window-global (no target widget): force a relayout and
            # repaint. `_refresh` reads the new size from `window.width/height`;
            # the repaint is needed because a resize clears the buffer even at
            # unchanged size. Not forwarded to widgets (no per-widget resize hook
            # yet).
            self._layout.update()
            return
        task = self._event_manager.manage(event)
        if task is not None:
            self._task_manager.one_shot(task)

    def _refresh(self) -> None:
        # Build the root drawer at the current window size and hand it to the
        # renderer (which owns the paint target and the frame-to-frame skip). A
        # resize forces a repaint via `_dispatch_event` (a resize clears the
        # buffer even at unchanged size).
        self._renderer.render_drawer(self._layout.render(self, self.width, self.height))

    def notify(self, notification: Any):
        self._post_event(NotificationTask(notification))

    def call_later(self, function, *args, **kwargs):
        wrapper = self._with_exc_handled(function)
        self._post_event(CallbackTask(function=wrapper, args=args, kwargs=kwargs))

    def call_async(self, function, *args, **kwargs):
        wrapper = self._with_exc_handled(function)
        self._post_event(
            CallbackTask(function=launch_thread, args=(wrapper, *args), kwargs=kwargs)
        )

    def call_now(self, function, *args, **kwargs):
        wrapper = self._with_exc_handled(function)
        return wrapper(*args, **kwargs)

    def _with_exc_handled(self, function: Callable) -> Callable:
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as e:
                self._force_quit(e)

        return wrapper

    def _force_quit(self, exc: Exception):
        if self._handled_exceptions and isinstance(exc, self._handled_exceptions):
            self._force_alert(exc)
        else:
            self._post_event(ExitTask(exc))

    def _force_alert(self, exception: Exception):
        self.clear_context()
        self.clear_fancybox()
        self._post_event(CallbackTask.new(self.error, exception))

    def _post_event(self, task: VidereTask):
        self._task_manager.post_task(task)

    def set_fancybox(
        self,
        content: Widget,
        title: str | Text = "Fancybox",
        buttons: Sequence[Button] = (),
        expand_buttons=True,
    ):
        self._event_manager.focus_out()
        self._layout.set_fancybox(Fancybox(content, title, buttons, expand_buttons))

    def clear_fancybox(self):
        self._layout.set_fancybox(None)

    def has_fancybox(self) -> bool:
        return self._layout.has_fancybox()

    def alert(self, message: str | Text, title: str | Text = "Alert"):
        if isinstance(message, str):
            message = Text(message)
        self.set_fancybox(
            Container(
                message,
                horizontal_alignment=Alignment.CENTER,
                vertical_alignment=Alignment.CENTER,
            ),
            title,
        )

    def error(self, exception: Exception):
        self.alert(
            f"{type(exception).__name__}: {exception}",
            title=f"Error: {type(exception).__name__}",
        )

    def confirm(
        self,
        confirmation: str | Widget,
        title: str | Text = "Confirm",
        on_confirm: Callable[[], None] | None = None,
    ):
        if isinstance(confirmation, str):
            confirmation = Text(confirmation)
        if isinstance(title, str):
            title = Text(title)
        self.set_fancybox(
            Container(
                confirmation,
                horizontal_alignment=Alignment.CENTER,
                vertical_alignment=Alignment.CENTER,
            ),
            title,
            buttons=[
                FancyCloseButton(
                    title.text,
                    on_click=Procedure(on_confirm) if on_confirm is not None else None,
                ),
                FancyCloseButton("cancel"),
            ],
        )

    def set_context(self, relative: Widget, control: Widget, x=0, y=0):
        self._layout.set_context(Context(relative, control, x=x, y=y))

    def clear_context(self, relative: Widget | None = None) -> None:
        """Clear current context."""
        if self._layout.has_context(relative):
            self._layout.set_context(None)

    def has_context(self, relative: Widget | None = None) -> bool:
        """
        Return True if a context is currently active.
        :param relative: optional relative.
            If given, return True only if
            current context is attached to this relative.
        """
        return self._layout.has_context(relative)

    def set_notification_callback(self, callback: NotificationCallback | None):
        if callback is None:
            self.clear_notification_callbacks()
        else:
            self.add_notification_callback(callback)

    def add_notification_callback(self, callback: NotificationCallback):
        if callback not in self._notification_callbacks:
            self._notification_callbacks.append(callback)

    def remove_notification_callback(self, callback: NotificationCallback):
        if callback in self._notification_callbacks:
            self._notification_callbacks.remove(callback)

    def clear_notification_callbacks(self):
        self._notification_callbacks.clear()

    def get_element_by_key(self, key: str) -> Widget | None:
        results = self._layout.collect_matches(WidgetByKeyGetter(key))
        return results[0] if results else None

    def focus_out(self, widget: Widget | None = None) -> None:
        self._event_manager.focus_out(widget)

    def _manage_task(self, task: VidereTask) -> None:
        task_callback = self.on_task.get(type(task))
        assert task_callback is not None
        task_callback(self, task)

    on_task = OnEvent[type[VidereTask]]()

    @on_task(ExitTask)
    def _task_exit(self, task: ExitTask):
        logger.warning("Quit.")
        self._exit_exception = task.exception
        self._stop_running()

    @on_task(NotificationTask)
    def _task_notification(self, task: NotificationTask):
        task.dispatch(self._notification_callbacks)

    @on_task(CallbackTask)
    def _task_callback(self, task: CallbackTask):
        task.run()
