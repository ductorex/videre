import functools
import logging
import threading
from typing import Any, Callable, Sequence, TypeVar

import pygame
from pygame.event import Event

from videre.colors import ColorDef, Colors, parse_color
from videre.core.clipboard import Clipboard
from videre.core.constants import Alignment, MouseButton, WINDOW_FPS
from videre.core.events import CustomEvents, KeyboardEntry, MouseEvent
from videre.core.fontfactory.pygame_font_factory import PygameFontFactory
from videre.core.fontfactory.pygame_text_rendering import PygameTextRendering
from videre.core.pygame_utils import Color, PygameUtils, Surface
from videre.core.utils import launch_thread
from videre.layouts.container import Container
from videre.widgets.button import Button
from videre.widgets.text import Text
from videre.widgets.widget import Widget
from videre.windowing.context import Context
from videre.windowing.event_propagator import EventPropagator
from videre.windowing.fancybox import Fancybox
from videre.windowing.windowlayout import WindowLayout
from videre.windowing.windowutils import OnEvent, WidgetByKeyGetter

logger = logging.getLogger(__name__)


NotificationCallback = Callable[[Any], None]


WidgetBase = TypeVar("WidgetBase", bound=Widget)


def _handle_exception(on_except, function):

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            if not on_except(e):
                raise e

    return wrapper


class Window(PygameUtils, Clipboard):
    __slots__ = (
        "_exit_code",
        "_title",
        "_width",
        "_height",
        "_running",
        "_screen",
        "_down",
        "_motion",
        "_focus",
        "_manual_events_after",
        "_layout",
        "_controls",
        "_fancybox",
        "_context",
        "_fonts",
        "_hide",
        "_notification_callback",
        "_lock",
        "_nb_frames",
        "_text_cursor",
        "_default_cursor",
        "data",
    )

    def __init__(
        self,
        title="Window",
        width=1280,
        height=720,
        background: ColorDef = None,
        font_size=14,
        hide=False,
    ):
        super().__init__()
        self._exit_code = 0

        self._lock = threading.Lock()

        self._title = str(title) or "Window"
        self._width = width
        self._height = height
        self._hide = bool(hide)

        self._running = True
        self._screen: Surface | None = None

        self._down: dict[MouseButton, Widget | None] = {
            button: None for button in MouseButton
        }
        self._motion: Widget | None = None
        self._focus: Widget | None = None
        self._manual_events_after: list[Event] = []
        self._layout = WindowLayout(parse_color(background or Colors.white))

        self._controls: list[Widget] = []
        self._fancybox: Fancybox | None = None
        self._context = None

        self._fonts = PygameFontFactory(size=font_size)

        self._notification_callback: NotificationCallback | None = None
        self._nb_frames = 0

        self._default_cursor = pygame.mouse.get_cursor()
        self._text_cursor = pygame.cursors.compile(pygame.cursors.textmarker_strings)

        self.data = None

    def __repr__(self):
        return f"[{type(self).__name__}][{id(self)}]"

    def set_text_cursor(self):
        pygame.mouse.set_cursor((8, 16), (0, 0), *self._text_cursor)

    def set_default_cursor(self):
        pygame.mouse.set_cursor(*self._default_cursor)

    @property
    def background(self) -> Color:
        return self._layout.background

    @background.setter
    def background(self, value: ColorDef):
        self._layout.background = parse_color(value or Colors.white)

    @property
    def nb_frames(self) -> int:
        return self._nb_frames

    @property
    def fonts(self) -> PygameFontFactory:
        return self._fonts

    @property
    def controls(self) -> tuple[Widget, ...]:
        return tuple(self._controls)

    @controls.setter
    def controls(self, controls: Sequence[Widget]):
        self._controls = controls
        self.__refresh_controls()

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def get_screen(self) -> Surface:
        assert self._screen is not None
        return self._screen

    def text_rendering(
        self,
        size: int = None,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int = None,
    ) -> PygameTextRendering:
        return PygameTextRendering(
            self.fonts,
            size=size,
            strong=strong,
            italic=italic,
            underline=underline,
            height_delta=height_delta,
        )

    def run(self) -> int:
        if not self._running:
            raise RuntimeError("Window has already run. Cannot run again.")

        self._init_display()

        clock = pygame.time.Clock()
        while self._running:
            self._render()
            clock.tick(WINDOW_FPS)
        pygame.quit()
        return self._exit_code

    def _init_display(self):
        flags = pygame.RESIZABLE
        if self._hide:
            flags |= pygame.HIDDEN
        self._screen = pygame.display.set_mode((self._width, self._height), flags=flags)
        pygame.display.set_caption(self._title)

        # Initialize keyboard repeat.
        # NB: TEXTINPUT events already handle repeat,
        # but we still need manual initialization for KEYDOWN/KEYUP events.
        # I don't know how to get default delay and interval values for TEXTINPUT,
        # so I tried here to set empiric values so that key repeat
        # is the most like textinput repeat.
        pygame.key.set_repeat(500, 35)

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
        # event if there was a mouse motion event above, for example
        # if supplementary events changed the interface between
        # the mouse motion event found above and
        # the end of loop above.
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
            if self._manual_events_after:
                for event in self._manual_events_after:
                    pygame.event.post(event)
                self._manual_events_after.clear()

    def __refresh_controls(self):
        self._layout.controls = (
            self.controls
            + ((self._fancybox,) if self._fancybox else ())
            + ((self._context,) if self._context else ())
        )

    def notify(self, notification: Any):
        self._post_event(CustomEvents.notification_event(notification))

    def run_later(self, function, *args, **kwargs):
        wrapper = _handle_exception(self._force_quit, function)
        self._post_event(CustomEvents.callback_event(wrapper, *args, **kwargs))

    def run_async(self, function, *args, **kwargs):
        wrapper = _handle_exception(self._force_quit, function)
        self._post_event(
            CustomEvents.callback_event(launch_thread, wrapper, *args, **kwargs)
        )

    def _force_quit(self, exception: Exception = None):
        self._exit_code = -int(exception is not None)
        self._post_event(pygame.event.Event(pygame.QUIT))

    def _post_event(self, event: Event):
        with self._lock:
            self._manual_events_after.append(event)

    def set_fancybox(
        self,
        content: Widget,
        title: str | Text = "Fancybox",
        buttons: Sequence[Button] = (),
        expand_buttons=True,
    ):
        assert not self._fancybox
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

    def set_context(self, relative: Widget, control: Widget, x=0, y=0):
        self._context = Context(relative, control, x=x, y=y)
        self.__refresh_controls()

    def clear_context(self):
        self._context = None
        self.__refresh_controls()

    def set_notification_callback(self, callback: NotificationCallback | None):
        self._notification_callback = callback

    def get_element_by_key(self, key: str) -> WidgetBase | None:
        results = self._layout.collect_matches(WidgetByKeyGetter(key))
        return results[0] if results else None

    def __on_event(self, event: Event):
        """
        Handle a pygame event.

        :param event: event to handle
        :return: `skip_render`: tell whether the screen update must be skipped
            after this event handling.

            By default, callbacks return None (=> False),
            so the screen is immediately updated.
            Some callbacks may return True to prevent this.

            NB: Returned value is not yet used.
        """
        callback = self.on_event.get(event.type)
        if callback:
            return callback(self, event)
        else:
            logger.debug(
                f"Unhandled pygame event: {pygame.event.event_name(event.type)}"
            )
            return True

    on_event = OnEvent[int]()

    @on_event(pygame.QUIT)
    def _on_quit(self, event: Event):
        logger.warning("Quit pygame.")
        self._running = False

    @on_event(pygame.MOUSEWHEEL)
    def _on_mouse_wheel(self, event: Event):
        owner = self._layout.get_mouse_wheel_owner(*pygame.mouse.get_pos())
        if owner:
            shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            owner.widget.handle_mouse_wheel(event.x, event.y, shift)

    @on_event(pygame.MOUSEBUTTONDOWN)
    def _on_mouse_button_down(self, event: Event):
        owner = self._layout.get_mouse_owner(*event.pos)
        if owner:
            # Handle mouse down
            button = MouseButton(event.button)
            self._down[button] = owner.widget
            EventPropagator.handle_mouse_down(
                owner.widget,
                MouseEvent(x=owner.x_in_parent, y=owner.y_in_parent, buttons=[button]),
            )
            # Handle focus
            focus = EventPropagator.handle_focus_in(owner.widget)
            if self._focus and self._focus != focus:
                self._focus.handle_focus_out()
            self._focus = focus

    @on_event(pygame.MOUSEBUTTONUP)
    def _on_mouse_button_up(self, event: Event):
        button = MouseButton(event.button)
        owner = self._layout.get_mouse_owner(*event.pos)
        if owner:
            EventPropagator.handle_mouse_up(
                owner.widget,
                MouseEvent(x=owner.x_in_parent, y=owner.y_in_parent, buttons=[button]),
            )
            if self._down[button] == owner.widget:
                EventPropagator.handle_click(owner.widget, button)
            elif self._down[button]:
                EventPropagator.handle_mouse_down_canceled(self._down[button], button)
        elif self._down[button]:
            EventPropagator.handle_mouse_down_canceled(self._down[button], button)
        self._down[button] = None

    @on_event(pygame.MOUSEMOTION)
    def _on_mouse_motion(self, event: Event):
        m_event = MouseEvent.from_mouse_motion(event)
        owner = self._layout.get_mouse_owner(*event.pos)
        if owner:
            m_event = MouseEvent.from_mouse_motion(
                event, owner.x_in_parent, owner.y_in_parent
            )
            if not self._motion:
                EventPropagator.handle_mouse_enter(owner.widget, m_event)
            elif self._motion is owner.widget:
                EventPropagator.handle_mouse_over(owner.widget, m_event)
            else:
                EventPropagator.manage_mouse_motion(event, owner, self._motion)
            self._motion = owner.widget
        elif self._motion:
            EventPropagator.handle_mouse_exit(self._motion)
            self._motion = None
        for button in m_event.buttons:
            if self._down[button]:
                down = self._down[button]
                parent_x = 0 if down.parent is None else down.parent.global_x
                parent_y = 0 if down.parent is None else down.parent.global_y
                EventPropagator.handle_mouse_down_move(
                    down,
                    MouseEvent.from_mouse_motion(
                        event, event.pos[0] - parent_x, event.pos[1] - parent_y
                    ),
                )

    @on_event(pygame.WINDOWLEAVE)
    def _on_window_leave(self, event: Event):
        if self._motion:
            EventPropagator.handle_mouse_exit(self._motion)
            self._motion = None

    @on_event(pygame.WINDOWRESIZED)
    def _on_window_resized(self, event: Event):
        logger.debug(f"Window resized: {event}")
        self._width, self._height = event.x, event.y

    @on_event(pygame.TEXTINPUT)
    def _on_text_input(self, event: Event):
        if self._focus:
            self._focus.handle_text_input(event.text)

    @on_event(pygame.KEYDOWN)
    def _on_keydown(self, event: Event):
        if self._focus:
            self._focus.handle_keydown(KeyboardEntry(event))

    @on_event(CustomEvents.CALLBACK_EVENT)
    def _on_custom_callback(self, event: Event):
        event.function(*event.args, **event.kwargs)

    @on_event(CustomEvents.NOTIFICATION_EVENT)
    def _on_notification(self, event: Event):
        if self._notification_callback:
            self._notification_callback(event.notification)
