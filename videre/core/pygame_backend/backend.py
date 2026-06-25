import io
import logging
from collections import OrderedDict
from collections.abc import Callable
from typing import Sequence

import pygame
import pygame.gfxdraw
from PIL.Image import Image

from videre.colors import Color
from videre.core.abstract_backend import (
    AbstractBackend,
    AbstractRenderer,
    AbstractWindowing,
)
from videre.core.constants import WINDOW_FPS
from videre.core.drawer import (
    Args,
    BlitArgs,
    BoxArgs,
    CopyArgs,
    Drawer,
    FillArgs,
    FilledPolygonArgs,
    ImageArgs,
    ImageFromBytesArgs,
    LineArgs,
    PositionTuple,
    RectangleArgs,
    SmoothScaleArgs,
)
from videre.core.events import (
    ExitEvent,
    KeyDownEvent,
    MouseButtonDownEvent,
    MouseButtonUpEvent,
    MouseMotionEvent,
    MouseWheelEvent,
    TextInputEvent,
    VidereEvent,
    WindowLeaveEvent,
)
from videre.core.pygame_backend.definitions import (
    Event,
    PygameColor,
    PygameRendering,
    Rect,
    Surface,
)
from videre.core.pygame_backend.mapping import (
    keyboard_entry_to_pygame_dict,
    mouse_button_to_pygame,
    pygame_to_keyboard_entry,
    pygame_to_mouse_button,
    pygame_to_mouse_buttons,
)
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import Rendering
from videre.core.tasks import TaskManager, VidereTask
from videre.core.utils import OnEvent

logger = logging.getLogger(__name__)


class PygameRenderer(AbstractRenderer):
    """Pygame rasterizer: replays a Drawer's command IR onto pygame surfaces.

    Holds no window/event state — it can be instantiated and benchmarked on its
    own. The by-value LRU cache is private here (the abstract contract is silent
    on caching), so a GPU backend can ignore it.
    """

    __slots__ = ("_drawer_cache",)

    _DRAWER_CACHE_SIZE = 512

    def __init__(self) -> None:
        # By-value LRU of materialized sub-surfaces. This caching is a software
        # / "retained" strategy private to this renderer, not part of the
        # abstract contract: an immediate-mode GPU backend would skip it.
        self._drawer_cache: OrderedDict[Drawer, Rendering] = OrderedDict()

    def render_drawer(self, drawer: Drawer, dst: Rendering | None = None) -> Rendering:
        """Rasterize a Drawer, memoizing materialized surfaces by value.

        Drawers hash/compare by content, so an unchanged sub-tree (a clean
        widget reuses its cached Drawer frame to frame) hits the cache instead
        of being repainted. Only `dst=None` calls are cached: the root screen
        (painted onto `dst`) changes almost every frame and is never stored.
        Backed by a bounded LRU. Cached surfaces are read-only — the visitor
        only ever mutates `dst` or a fresh surface, and `copy()` shields the
        in-place edits (`TextInput`), so sharing a cached surface is safe.
        """
        if dst is not None:
            return self._paint_drawer(drawer, dst)
        cache = self._drawer_cache
        cached = cache.get(drawer)
        if cached is not None:
            cache.move_to_end(drawer)
            return cached
        surface = self._paint_drawer(drawer, None)
        cache[drawer] = surface
        if len(cache) > self._DRAWER_CACHE_SIZE:
            cache.popitem(last=False)
        return surface

    def _paint_drawer(self, drawer: Drawer, dst: Rendering | None) -> Rendering:
        """Replay a Drawer's command IR onto a real pygame surface — the
        rasterization seam behind `render_drawer` (which adds the value cache).

        A drawer is a flat list of commands expressed in its own local
        coordinates. A *generative* command (image / image_from_bytes /
        smoothscale / copy) yields the base surface and, by construction, comes
        first; every other command *mutates* that surface. The surface is
        created lazily at the drawer's own size when no generative command
        opened it (so a purely generative drawer allocates nothing extra, and an
        empty drawer still yields a zero-size surface). Nested drawers — blit,
        smoothscale, copy — recurse through `render_drawer`, so they hit the
        cache too.

        `dst`, when given, is drawn onto directly and returned — no intermediate
        full-surface allocation (used by `Window._refresh` to paint the screen).
        It must cover the drawer and is the *root* surface only: it is never
        propagated into the recursion. A generative command composites onto
        `dst` instead of replacing it.
        """
        surface: Rendering | None = dst
        for args in drawer:
            match args:
                case ImageArgs(image=image):
                    surface = self._compose(surface, self.image(image))
                case ImageFromBytesArgs(data=data, width=width, height=height):
                    surface = self._compose(
                        surface, self.image_from_bytes(data, (int(width), int(height)))
                    )
                case SmoothScaleArgs(drawer=source):
                    surface = self._compose(
                        surface,
                        self.smoothscale(
                            self.render_drawer(source),
                            drawer.get_width(),
                            drawer.get_height(),
                        ),
                    )
                case CopyArgs(drawer=source):
                    surface = self._compose(
                        surface, self.copy(self.render_drawer(source))
                    )
                case _:
                    if surface is None:
                        surface = self.new_surface(
                            drawer.get_width(), drawer.get_height()
                        )
                    self._replay(surface, args)
        if surface is None:
            surface = self.new_surface(drawer.get_width(), drawer.get_height())
        return surface

    def _compose(self, surface: Rendering | None, produced: Rendering) -> Rendering:
        """Place a *generative* command's output. With no surface yet, the
        produced surface *becomes* the surface (the lazy / no-`dst` case); onto
        an existing surface (e.g. `dst`) it composites at the origin, so a
        caller-supplied `dst` is never silently dropped."""
        if surface is None:
            return produced
        self.blit(surface, produced, (0, 0))
        return surface

    def _replay(self, surface: Rendering, args: Args) -> None:
        """Apply one *mutating* Drawer command onto an existing surface."""
        match args:
            case FillArgs(color=color, rectangle=rectangle):
                self.fill(surface, color, rectangle)
            case BlitArgs(drawer=source, position=position):
                self.blit(surface, self.render_drawer(source), (position.x, position.y))
            case LineArgs(color=color, start=start, end=end):
                self.line(surface, color, (start.x, start.y), (end.x, end.y))
            case RectangleArgs(rectangle=rectangle, color=color):
                self.rectangle(surface, rectangle, color)
            case BoxArgs(rectangle=rectangle, color=color):
                self.box(surface, rectangle, color)
            case FilledPolygonArgs(points=points, color=color):
                self.filled_polygon(surface, [(p.x, p.y) for p in points], color)
            case _:
                raise NotImplementedError(type(args).__name__, args)

    def new_color(self, color: Color) -> PygameColor:
        return PygameColor(color.r, color.g, color.b, color.a)

    def new_rect(self, rectangle: Rectangle) -> Rect:
        return Rect(rectangle.left, rectangle.top, rectangle.width, rectangle.height)

    def new_surface(self, width: int | float, height: int | float) -> Rendering:
        return PygameRendering(Surface((width, height), flags=pygame.SRCALPHA))

    def fill(
        self, surface: Rendering, color: Color, rectangle: Rectangle | None = None
    ) -> None:
        _deref(surface).fill(
            self.new_color(color),
            self.new_rect(rectangle) if rectangle is not None else None,
        )

    def blit(self, dst: Rendering, src: Rendering, position: PositionTuple) -> None:
        _deref(dst).blit(_deref(src), position)

    def line(
        self, surface: Rendering, color: Color, start: PositionTuple, end: PositionTuple
    ) -> None:
        # `pygame.draw.line` over `pygame.gfxdraw.line`: faster on tight
        # loops (gradients trace hundreds of lines per frame) and supports
        # a `width` parameter if we ever need thicker strokes. `gfxdraw`
        # only offers pixel-exact non-AA single-pixel lines.
        pygame.draw.line(_deref(surface), self.new_color(color), start, end)

    def rectangle(self, surface: Rendering, rectangle: Rectangle, color: Color) -> None:
        pygame.gfxdraw.rectangle(
            _deref(surface), self.new_rect(rectangle), self.new_color(color)
        )

    def box(self, surface: Rendering, rectangle: Rectangle, color: Color) -> None:
        pygame.gfxdraw.box(
            _deref(surface), self.new_rect(rectangle), self.new_color(color)
        )

    def filled_polygon(
        self, surface: Rendering, points: Sequence[PositionTuple], color: Color
    ) -> None:
        pygame.gfxdraw.filled_polygon(_deref(surface), points, self.new_color(color))

    def smoothscale(
        self, surface: Rendering, width: int | float, height: int | float
    ) -> Rendering:
        return PygameRendering(
            pygame.transform.smoothscale(_deref(surface), (width, height))
        )

    def copy(self, surface: Rendering) -> Rendering:
        return PygameRendering(_deref(surface).copy())

    def image(self, image: Image) -> Rendering:
        # `frombytes` copies the buffer; `frombuffer` would share it and
        # require the PIL image to stay alive for as long as the Surface
        # exists. A self-contained Surface is safer at this boundary and
        # the copy cost is dwarfed by the upstream PIL decode + tobytes.

        # NB: convert_alpha() changes the pixel format of image
        # to match the display while preserving transparency (alpha).
        return PygameRendering(
            pygame.image.frombytes(image.tobytes(), image.size, "RGBA").convert_alpha()
        )

    def image_from_bytes(self, data: bytes, size: tuple[int, int]) -> Rendering:
        # No `convert_alpha()` here (unlike `image`): keep this independent of
        # the display so glyph rasterization works before a display mode is
        # set. The source buffer is straight RGBA with alpha.
        return PygameRendering(pygame.image.frombytes(data, size, "RGBA"))


class PygameWindowing(AbstractWindowing):
    """Pygame windowing: the display, clock, cursor, and pygame event loop.

    Owns the OS-facing state and drives `_step`. Posts videre events back into
    pygame's queue (`post_event`) so `FakeUser` drives the real event path.
    """

    __slots__ = (
        "__default_cursor",
        "__text_cursor",
        "_screen",
        "_screen_rendering",
        "_clock",
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
        super().__init__(
            width=width,
            height=height,
            title=title,
            event_manager=event_manager,
            render_manager=render_manager,
            task_manager=task_manager,
            hide=hide,
            fps=fps,
        )

        # Init pygame here.
        pygame.init()

        self.__default_cursor = pygame.mouse.get_cursor()
        self.__text_cursor = pygame.cursors.compile(pygame.cursors.textmarker_strings)
        self._screen: Surface | None = None
        # Stable wrapper over `_screen`: recreated only when the underlying
        # buffer is (re)allocated (start / resize_screen), never per-frame. Its
        # identity lets `Window._refresh` skip repainting an unchanged screen
        # while still detecting a buffer swap (e.g. a same-size resize).
        self._screen_rendering: PygameRendering | None = None
        self._clock: pygame.time.Clock | None = None

    def _set_text_cursor(self) -> None:
        pygame.mouse.set_cursor((8, 16), (0, 0), *self.__text_cursor)

    def _set_default_cursor(self) -> None:
        pygame.mouse.set_cursor(*self.__default_cursor)

    def screenshot(self) -> io.BytesIO:
        assert self._screen is not None
        data = io.BytesIO()
        pygame.image.save(self._screen, data)
        data.flush()
        return data

    def start(self) -> None:
        flags = pygame.RESIZABLE
        if self._hide:
            flags |= pygame.HIDDEN
        self._screen = pygame.display.set_mode((self._width, self._height), flags=flags)
        self._screen_rendering = PygameRendering(self._screen)
        pygame.display.set_caption(self._title)

        # Initialize keyboard repeat.
        # NB: TEXTINPUT events already handle repeat,
        # but we still need manual initialization for KEYDOWN/KEYUP events.
        # I don't know how to get default delay and interval values for TEXTINPUT,
        # so I tried here to set empiric values so that key repeat
        # is the most like textinput repeat.
        pygame.key.set_repeat(500, 35)

        self._clock = pygame.time.Clock()

    def stop(self) -> None:
        pygame.quit()

    def resize_screen(self, width: int, height: int) -> None:
        flags = pygame.RESIZABLE
        if self._hide:
            flags |= pygame.HIDDEN
        self._screen = pygame.display.set_mode((width, height), flags=flags)
        self._screen_rendering = PygameRendering(self._screen)
        pygame.event.post(Event(pygame.WINDOWRESIZED, x=width, y=height))

    def _step(self, fps: int | None = None) -> None:
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
        assert self._screen_rendering is not None
        self._render_manager(self._screen_rendering)
        pygame.display.flip()

        # Process pending tasks.
        self._task_manager.manage_tasks()

        if fps is None:
            fps = self._fps
        if fps > 0:
            assert self._clock is not None
            self._clock.tick(fps)

    def __on_event(self, event: Event):
        """Handle a pygame event."""
        ret = self._manage_event(event)
        if ret is not None:
            self._task_manager.one_shot(ret)

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
        self._handle_exit()

    @_on_event(pygame.WINDOWRESIZED)
    def _resize_window(self, event: Event) -> None:
        # This method immediately handles event without dispatching to videre event manager.
        width, height = event.x, event.y
        if self._screen is not None:
            assert self._screen.get_width() == width
            assert self._screen.get_height() == height
        self._handle_resize(width, height)

    @_on_event(pygame.MOUSEWHEEL)
    def _on_mouse_wheel(self, event: Event) -> VidereTask | None:
        # Real OS wheel events have no position; fall back to pygame.mouse.get_pos().
        # Test-posted events carry mouse_x/mouse_y as custom attributes
        # (see PygameWindowing._post_mouse_wheel) so they can route to a specific widget.
        if hasattr(event, "mouse_x"):
            mouse_x, mouse_y = event.mouse_x, event.mouse_y
        else:
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

    def post_event(self, event: VidereEvent) -> None:
        event_type = type(event)
        callback = self._on_post.get(type(event))
        if callback is None:
            raise NotImplementedError(event_type, event)
        callback(self, event)

    _on_post = OnEvent[type[VidereEvent]]()

    @classmethod
    @_on_post(MouseButtonDownEvent)
    def _post_mouse_button_down(cls, event: MouseButtonDownEvent) -> None:
        event_data = {
            "pos": (event.x, event.y),
            "button": mouse_button_to_pygame(event.button),
        }
        pygame.event.post(Event(pygame.MOUSEBUTTONDOWN, event_data))

    @classmethod
    @_on_post(MouseButtonUpEvent)
    def _post_mouse_button_up(cls, event: MouseButtonUpEvent) -> None:
        event_data = {
            "pos": (event.x, event.y),
            "button": mouse_button_to_pygame(event.button),
        }
        pygame.event.post(Event(pygame.MOUSEBUTTONUP, event_data))

    @classmethod
    @_on_post(MouseMotionEvent)
    def _post_mouse_motion(cls, event: MouseMotionEvent) -> None:
        event_data = {
            "pos": (event.x, event.y),
            "rel": (event.dx, event.dy),
            "touch": False,
            "buttons": (
                int(event.button_left),
                int(event.button_middle),
                int(event.button_right),
            ),
        }
        pygame.event.post(Event(pygame.MOUSEMOTION, event_data))

    @classmethod
    @_on_post(MouseWheelEvent)
    def _post_mouse_wheel(cls, event: MouseWheelEvent) -> None:
        pygame.key.set_mods(pygame.KMOD_SHIFT if event.shift else 0)
        event_data = {
            "x": event.wheel_dx,
            "y": event.wheel_dy,
            "mouse_x": event.mouse_x,
            "mouse_y": event.mouse_y,
        }
        pygame.event.post(Event(pygame.MOUSEWHEEL, event_data))

    @classmethod
    @_on_post(KeyDownEvent)
    def _post_key_down(cls, event: KeyDownEvent) -> None:
        pygame.event.post(
            Event(pygame.KEYDOWN, keyboard_entry_to_pygame_dict(event.entry))
        )

    @classmethod
    @_on_post(TextInputEvent)
    def _post_text_input(cls, event: TextInputEvent) -> None:
        event_data = {"text": event.text}
        pygame.event.post(Event(pygame.TEXTINPUT, event_data))

    @classmethod
    @_on_post(WindowLeaveEvent)
    def _post_window_leave(cls, event: WindowLeaveEvent) -> None:
        pygame.event.post(Event(pygame.WINDOWLEAVE))

    @classmethod
    @_on_post(ExitEvent)
    def _post_exit(cls, event: ExitEvent) -> None:
        pygame.event.post(Event(pygame.QUIT))


class PygameBackend(AbstractBackend):
    """The pygame backend: pairs a `PygameRenderer` with a `PygameWindowing`.

    A coherent provider — `Window` asks it for both halves; they are never mixed
    with another backend's.
    """

    __slots__ = ()

    def create_renderer(self) -> AbstractRenderer:
        return PygameRenderer()

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
    ) -> AbstractWindowing:
        return PygameWindowing(
            width=width,
            height=height,
            title=title,
            event_manager=event_manager,
            render_manager=render_manager,
            task_manager=task_manager,
            hide=hide,
            fps=fps,
        )


def _deref(rendering: Rendering) -> Surface:
    """Dereference a Rendering object into a Pygame surface."""
    assert isinstance(rendering, PygameRendering), type(rendering)
    return rendering.surface
