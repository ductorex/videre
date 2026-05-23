import functools
import logging
from typing import Any, Callable, Sequence

from videre.colors import Color, ColorDef, Colors, parse_color
from videre.core.constants import Alignment
from videre.core.pygame_backend.backend import PygameBackend
from videre.core.pygame_backend.definitions import Surface
from videre.core.tasks import (
    CallbackTask,
    EscapeTask,
    ExitTask,
    NotificationCallback,
    NotificationTask,
    TaskManager,
    VidereTask,
)
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
        "_controls",
        "_fancybox",
        "_context",
        "_notification_callbacks",
        "data",
        "_handled_exceptions",
        "_subpixel",
        "_event_manager",
        "_task_manager",
        "_backend",
        "_font_size_pts",
        "_font_height",
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
    ):
        self._layout = WindowLayout(parse_color(background or Colors.white))
        self._event_manager = WindowEventManager(self._layout)
        self._task_manager = TaskManager(self._manage_task)
        self._backend = PygameBackend(
            width=width,
            height=height,
            title=str(title) or "Window",
            hide=bool(hide),
            event_manager=self._event_manager.manage,
            render_manager=self._refresh,
            task_manager=self._task_manager,
        )
        self._font_size_pts = font_size
        self._font_height: int | None = None

        self._exit_code = 0
        self._exit_exception: Exception | None = None

        # Videre-specific events
        self._notification_callbacks: list[NotificationCallback] = []

        self._controls: list[Widget] = []
        self._fancybox: Fancybox | None = None
        self._context: Context | None = None

        self._handled_exceptions = tuple(alert_on_exceptions)
        self._subpixel: bool | None = handle_text_sub_pixels

        self.data = None

    def _is_running(self) -> bool:
        return self._backend.running

    def _stop_running(self):
        self._backend.running = False

    def __repr__(self):
        return f"[{type(self).__name__}][{id(self)}]"

    @property
    def backend(self) -> PygameBackend:
        return self._backend

    @property
    def background(self) -> Color:
        return self._layout.background

    @background.setter
    def background(self, value: ColorDef | None):
        self._layout.background = parse_color(value or Colors.white)

    @property
    def nb_frames(self) -> int:
        return self._backend.nb_frames

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
        return tuple(self._controls)

    @controls.setter
    def controls(self, controls: Sequence[Widget]):
        self._controls = list(controls)
        self.__refresh_controls()

    @property
    def width(self) -> int:
        return self._backend.width

    @property
    def height(self) -> int:
        return self._backend.height

    @property
    def title(self) -> str:
        return self._backend.title

    def text_rendering(
        self,
        size: int | None = None,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int | None = None,
    ):
        return self._backend.text_rendering(
            size=size or self._font_size_pts,
            strong=strong,
            italic=italic,
            underline=underline,
            height_delta=height_delta,
        )

    def run(self) -> int:
        if not self._is_running():
            raise RuntimeError("Window has already run. Cannot run again.")

        self._backend.run()

        if self._exit_exception:
            raise self._exit_exception
        return self._exit_code

    def __refresh_controls(self):
        self._layout.controls = (
            self.controls
            + ((self._fancybox,) if self._fancybox else ())
            + ((self._context,) if self._context else ())
        )

    def _refresh(self, screen: Surface) -> None:
        self._layout.screen = screen
        self._layout.render(self)

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
        assert not self._fancybox
        self._event_manager.focus_out()
        self._fancybox = Fancybox(content, title, buttons, expand_buttons)
        self.__refresh_controls()

    def clear_fancybox(self):
        self._fancybox = None
        self.__refresh_controls()

    def has_fancybox(self) -> bool:
        return self._fancybox is not None

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
        self._context = Context(relative, control, x=x, y=y)
        self.__refresh_controls()

    def clear_context(self, relative: Widget | None = None) -> None:
        """Clear current context."""
        if self.has_context(relative):
            self._context = None
            self.__refresh_controls()

    def has_context(self, relative: Widget | None = None) -> bool:
        """
        Return True if a context is currently active.
        :param relative: optional relative.
            If given, return True only if
            current context is attached to this relative.
        """
        return self._context is not None and (
            relative is None or self._context.relative is relative
        )

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

    @on_task(EscapeTask)
    def _task_escape(self, task: EscapeTask):
        if self.has_context():
            self.clear_context()
        elif self.has_fancybox():
            self.clear_fancybox()

    @on_task(NotificationTask)
    def _task_notification(self, task: NotificationTask):
        task.dispatch(self._notification_callbacks)

    @on_task(CallbackTask)
    def _task_callback(self, task: CallbackTask):
        task.run()
