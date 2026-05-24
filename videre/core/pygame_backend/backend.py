import io
import logging
from collections.abc import Callable

import pygame

from videre.core.constants import WINDOW_FPS
from videre.core.events import (
    KeyDownEvent,
    MouseButtonDownEvent,
    MouseButtonUpEvent,
    MouseMotionEvent,
    MouseWheelEvent,
    TextInputEvent,
    VidereEvent,
    WindowLeaveEvent,
)
from videre.core.pygame_backend.definitions import Event, Surface
from videre.core.pygame_backend.font_factory import PygameFontFactory
from videre.core.pygame_backend.mapping import (
    pygame_to_keyboard_entry,
    pygame_to_mouse_button,
    pygame_to_mouse_buttons,
)
from videre.core.pygame_backend.primitives import Pygame
from videre.core.pygame_backend.text_rendering import PygameTextRendering
from videre.core.tasks import TaskManager, VidereTask
from videre.core.utils import OnEvent

logger = logging.getLogger(__name__)


class PygameBackend(Pygame):
    __slots__ = (
        "__default_cursor",
        "__text_cursor",
        "_title",
        "_hide",
        "_width",
        "_height",
        "_screen",
        "_fonts",
        "_fps",
        "_running",
        "_nb_frames",
        "_event_dispatcher",
        "_task_manager",
        "_render_manager",
    )

    def __init__(
        self,
        width: int,
        height: int,
        title: str,
        event_manager: Callable[[VidereEvent], VidereTask | None],
        render_manager: Callable[[Surface], None],
        task_manager: TaskManager,
        hide: bool = False,
        fps: int = WINDOW_FPS,
    ) -> None:
        # Init pygame here.
        pygame.init()

        self.__default_cursor = pygame.mouse.get_cursor()
        self.__text_cursor = pygame.cursors.compile(pygame.cursors.textmarker_strings)
        self._fonts = PygameFontFactory()
        self._width = width
        self._height = height
        self._title = title
        self._hide = hide
        self._fps = fps
        self._screen: Surface | None = None
        self._running: bool = True
        self._nb_frames: int = 0

        self._event_dispatcher = event_manager
        self._render_manager = render_manager
        self._task_manager = task_manager

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

    @property
    def running(self) -> bool:
        return self._running

    @running.setter
    def running(self, running: bool) -> None:
        self._running = running

    def set_text_cursor(self):
        pygame.mouse.set_cursor((8, 16), (0, 0), *self.__text_cursor)

    def set_default_cursor(self):
        pygame.mouse.set_cursor(*self.__default_cursor)

    def cursor_is_default(self) -> bool:
        return pygame.mouse.get_cursor() == self.__default_cursor

    def screenshot(self) -> io.BytesIO:
        assert self._screen is not None
        data = io.BytesIO()
        pygame.image.save(self._screen, data)
        data.flush()
        return data

    def run(self) -> None:
        try:
            self.start()
            clock = pygame.time.Clock()
            while self._running:
                self.step()
                clock.tick(self._fps)
        finally:
            self.stop()

    def start(self) -> None:
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

    def stop(self):
        pygame.quit()

    def resize_screen(self, width: int, height: int) -> None:
        flags = pygame.RESIZABLE
        if self._hide:
            flags |= pygame.HIDDEN
        self._screen = pygame.display.set_mode((width, height), flags=flags)
        pygame.event.post(Event(pygame.WINDOWRESIZED, x=width, y=height))

    def step(self):
        # Handle interface events.
        # Also check if we got a mouse motion event.
        has_mouse_motion = False
        for event in pygame.event.get():
            has_mouse_motion = has_mouse_motion or event.type == pygame.MOUSEMOTION
            self.__on_event(event)

        # Synthesize a no-op MOUSEMOTION when none arrived this frame and the
        # cursor is over the window. This compensates for two pygame gaps:
        #   - WINDOWENTER / WINDOWFOCUSGAINED are unreliable across platforms
        #     (not fired when the mouse is already over the window at startup,
        #     missing on Windows in some setups, late or absent on macOS,
        #     bogus on KDE/Plasma) — so hover state would not refresh when the
        #     user returns to the window without moving the mouse.
        #   - Widget-tree mutations (e.g. closing a fancybox) do not emit any
        #     pygame event, so the widget newly exposed under an immobile
        #     cursor would never receive its hover transition.
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
        assert self._screen is not None
        self._render_manager(self._screen)
        pygame.display.flip()
        self._nb_frames += 1

        # Process pending tasks.
        self._task_manager.manage_tasks()

    def __on_event(self, event: Event):
        """Handle a pygame event."""
        ret = self._manage_event(event)
        if ret is not None:
            self._task_manager.one_shot(ret)

    def text_rendering(
        self,
        size: int,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int | None = None,
    ) -> PygameTextRendering:
        return PygameTextRendering(
            self._fonts,
            size=size,
            strong=strong,
            italic=italic,
            underline=underline,
            height_delta=height_delta,
        )

    def _manage_event(self, event: Event) -> VidereTask | None:
        callback = self._on_event.get(event.type)
        if callback is not None:
            return callback(self, event)
        logger.debug(f"Unhandled pygame event: {pygame.event.event_name(event.type)}")
        return None

    _on_event = OnEvent[int]()

    @_on_event(pygame.QUIT)
    def _quit(self, event: Event) -> None:
        # This method immediately handles event without dispatching to videre event manager.
        logger.warning("Quit Pygame.")
        self._running = False

    @_on_event(pygame.WINDOWRESIZED)
    def _resize_window(self, event: Event) -> None:
        # This method immediately handles event without dispatching to videre event manager.
        width, height = event.x, event.y
        if self._screen is not None:
            assert self._screen.get_width() == width
            assert self._screen.get_height() == height
        self._width, self._height = width, height

    @_on_event(pygame.MOUSEWHEEL)
    def _on_mouse_wheel(self, event: Event) -> VidereTask | None:
        mouse_x, mouse_y = pygame.mouse.get_pos()
        wheel_dx = event.x
        wheel_dy = event.y
        shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        return self._event_dispatcher(
            MouseWheelEvent(
                mouse_x=mouse_x,
                mouse_y=mouse_y,
                wheel_dx=wheel_dx,
                wheel_dy=wheel_dy,
                shift=shift,
            )
        )

    @_on_event(pygame.MOUSEBUTTONDOWN)
    def _on_mouse_button_down(self, event: Event) -> VidereTask | None:
        x, y = event.pos
        button = pygame_to_mouse_button(event.button)
        return self._event_dispatcher(MouseButtonDownEvent(x=x, y=y, buttons=(button,)))

    @_on_event(pygame.MOUSEBUTTONUP)
    def _on_mouse_button_up(self, event: Event) -> VidereTask | None:
        x, y = event.pos
        button = pygame_to_mouse_button(event.button)
        return self._event_dispatcher(MouseButtonUpEvent(x=x, y=y, buttons=(button,)))

    @_on_event(pygame.MOUSEMOTION)
    def _on_mouse_motion(self, event: Event) -> VidereTask | None:
        return self._event_dispatcher(
            MouseMotionEvent(
                x=event.pos[0],
                y=event.pos[1],
                dx=event.rel[0],
                dy=event.rel[1],
                buttons=pygame_to_mouse_buttons(event.buttons),
            )
        )

    @_on_event(pygame.WINDOWLEAVE)
    def _on_window_leave(self, event: Event) -> VidereTask | None:
        return self._event_dispatcher(WindowLeaveEvent())

    @_on_event(pygame.TEXTINPUT)
    def _on_text_input(self, event: Event) -> VidereTask | None:
        return self._event_dispatcher(TextInputEvent(event.text))

    @_on_event(pygame.KEYDOWN)
    def _on_keydown(self, event: Event) -> VidereTask | None:
        return self._event_dispatcher(KeyDownEvent(pygame_to_keyboard_entry(event)))
