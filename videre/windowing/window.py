import functools
import logging
import threading
from typing import Any, Callable, Sequence

import pygame

from videre.colors import Color, ColorDef, Colors, parse_color
from videre.core.constants import WINDOW_FPS, Alignment
from videre.core.events import (
    CallbackTask,
    CustomTasks,
    EscapeTask,
    ExitTask,
    NotificationCallback,
    NotificationTask,
    SizeTask,
    VidereTask,
)
from videre.core.fontfactory.pygame_font_factory import PygameFontFactory
from videre.core.fontfactory.pygame_text_rendering import PygameTextRendering
from videre.core.pygame_backend import Event, Pygame, Surface
from videre.core.utils import Procedure, launch_thread
from videre.fonts.font_utils import FontUtils
from videre.fonts.provider import FontProvider
from videre.layouts.container import Container
from videre.widgets.button import Button
from videre.widgets.text import Text
from videre.widgets.widget import Widget
from videre.windowing.context import Context
from videre.windowing.event_manager import WindowEventManager
from videre.windowing.fancybox import Fancybox
from videre.windowing.fancyclosebutton import FancyCloseButton
from videre.windowing.windowlayout import WindowLayout
from videre.windowing.windowutils import OnEvent, WidgetByKeyGetter

logger = logging.getLogger(__name__)


class Window:
    __slots__ = (
        "_exit_code",
        "_exit_exception",
        "_running",
        "_layout",
        "_controls",
        "_fancybox",
        "_context",
        "_fonts",
        "_notif_cbks",
        "_lock",
        "_nb_frames",
        "data",
        "_handled_exceptions",
        "_subpixel",
        "_pending_tasks",
        "_event_manager",
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
        self._backend = Pygame(width, height, str(title) or "Window", bool(hide))
        self._font_size_pts = font_size
        self._font_height: int | None = None

        self._exit_code = 0
        self._exit_exception: Exception | None = None
        self._lock = threading.Lock()

        self._layout = WindowLayout(parse_color(background or Colors.white))

        # Videre-specific events
        self._running = True
        self._pending_tasks: list[VidereTask] = []
        self._notif_cbks: list[NotificationCallback] = []

        self._controls: list[Widget] = []
        self._fancybox: Fancybox | None = None
        self._context: Context | None = None

        self._fonts = PygameFontFactory(size=self._font_size_pts)

        self._nb_frames = 0

        self._handled_exceptions = tuple(alert_on_exceptions)
        self._subpixel: bool | None = handle_text_sub_pixels

        self.data = None
        self._event_manager = WindowEventManager(self._layout)

    def _is_running(self) -> bool:
        return self._running

    def _stop_running(self):
        self._running = False

    def __repr__(self):
        return f"[{type(self).__name__}][{id(self)}]"

    @property
    def backend(self) -> Pygame:
        return self._backend

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

    def get_screen(self) -> Surface:
        return self._backend.get_screen()

    def text_rendering(
        self,
        size: int | None = None,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int | None = None,
    ):
        return PygameTextRendering(
            self._fonts,
            size=size or self._font_size_pts,
            strong=strong,
            italic=italic,
            underline=underline,
            height_delta=height_delta,
        )

    def run(self) -> int:
        if not self._running:
            raise RuntimeError("Window has already run. Cannot run again.")

        with self._backend:
            clock = pygame.time.Clock()
            while self._running:
                self._render()
                clock.tick(WINDOW_FPS)

        if self._exit_exception:
            raise self._exit_exception
        return self._exit_code

    def _render(self):
        # Handle interface events.
        # Also check if we got a mouse motion event.
        has_mouse_motion = False
        for event in pygame.event.get():
            has_mouse_motion = has_mouse_motion or event.type == pygame.MOUSEMOTION
            self.__on_event(event)

        # If we haven't already handled a mouse motion event but mouse if over screen,
        # then we process a custom mouse motion event.
        # TODO We might need to process a custom mouse motion event anyway,
        #   event if there was a mouse motion event above, for example
        #   if supplementary events changed the interface between
        #   the mouse motion event found above and
        #   the end of loop above.
        if not has_mouse_motion and pygame.mouse.get_focused():
            self.__on_event(
                Event(
                    pygame.MOUSEMOTION,
                    pos=pygame.mouse.get_pos(),
                    rel=(0, 0),
                    buttons=(0, 0, 0),
                    touch=False,
                )
            )

        # Refresh screen.
        self._layout.render(self)
        pygame.display.flip()
        self._nb_frames += 1

        # Post manual events.
        with self._lock:
            tasks = self._pending_tasks
            self._pending_tasks = []
        for task in tasks:
            task_callback = self.on_task.get(type(task))
            assert task_callback is not None
            task_callback(self, task)

    def __refresh_controls(self):
        self._layout.controls = (
            self.controls
            + ((self._fancybox,) if self._fancybox else ())
            + ((self._context,) if self._context else ())
        )

    def notify(self, notification: Any):
        self._post_event(CustomTasks.notification_task(notification))

    def call_later(self, function, *args, **kwargs):
        wrapper = self._with_exc_handled(function)
        self._post_event(CustomTasks.callback_task(wrapper, *args, **kwargs))

    def call_async(self, function, *args, **kwargs):
        wrapper = self._with_exc_handled(function)
        self._post_event(
            CustomTasks.callback_task(launch_thread, wrapper, *args, **kwargs)
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
            self._post_event(CustomTasks.exit_task(exc))

    def _force_alert(self, exception: Exception):
        self.clear_context()
        self.clear_fancybox()
        self._post_event(CustomTasks.callback_task(self.error, exception))

    def _post_event(self, task: VidereTask):
        with self._lock:
            self._pending_tasks.append(task)

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

    def clear_context(self, relative: Widget | None = None) -> bool:
        """
        Clear current context.
        Return True if context was cleared, False otherwise.
        """
        if self.has_context(relative):
            self._context = None
            self.__refresh_controls()
            return True
        return False

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
        if callback not in self._notif_cbks:
            self._notif_cbks.append(callback)

    def remove_notification_callback(self, callback: NotificationCallback):
        if callback in self._notif_cbks:
            self._notif_cbks.remove(callback)

    def clear_notification_callbacks(self):
        self._notif_cbks.clear()

    def get_element_by_key(self, key: str) -> Widget | None:
        results = self._layout.collect_matches(WidgetByKeyGetter(key))
        return results[0] if results else None

    def __on_event(self, event: Event):
        """
        Handle a pygame event.
        """
        ret = self._event_manager.manage(event)
        if ret is not None:
            task_callback = self.on_task.get(type(ret))
            if task_callback:
                task_callback(self, ret)

    def focus_out(self, widget: Widget | None = None) -> None:
        self._event_manager.focus_out(widget)

    on_task = OnEvent[type[VidereTask]]()

    @on_task(ExitTask)
    def _task_exit(self, task: ExitTask):
        logger.warning("Quit.")
        self._exit_exception = task.exception
        self._stop_running()

    @on_task(SizeTask)
    def _task_size(self, task: SizeTask):
        logger.debug(f"Window resized: {task}")
        self._backend.width, self._backend.height = task.width, task.height

    @on_task(EscapeTask)
    def _task_escape(self, task: EscapeTask):
        if self.has_context():
            self.clear_context()
        elif self.has_fancybox():
            self.clear_fancybox()

    @on_task(NotificationTask)
    def _task_notification(self, task: NotificationTask):
        task.dispatch(self._notif_cbks)

    @on_task(CallbackTask)
    def _task_callback(self, task: CallbackTask):
        task.run()
