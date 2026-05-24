from dataclasses import dataclass
from typing import Sequence, TypeAlias

import pygame
import pygame.gfxdraw
from PIL.Image import Image

from videre.colors import Color
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
from videre.core.pygame_backend.definitions import Event, PygameColor, Rect, Surface
from videre.core.pygame_backend.mapping import (
    keyboard_entry_to_pygame_dict,
    mouse_button_to_pygame,
)
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import Rendering
from videre.core.utils import OnEvent

_Position: TypeAlias = tuple[int | float, int | float]


@dataclass(frozen=True, slots=True)
class PygameRendering(Rendering):
    surface: Surface

    def get_width(self) -> int:
        return self.surface.get_width()

    def get_height(self) -> int:
        return self.surface.get_height()

    def get_at(self, position: tuple[int, int]) -> Color:
        color = self.surface.get_at(position)
        return Color(color.r, color.g, color.b, color.a)


def deref(rendering: Rendering) -> Surface:
    assert isinstance(rendering, PygameRendering), type(rendering)
    return rendering.surface


class Pygame:
    __slots__ = ()

    @classmethod
    def new_surface(cls, width: int | float, height: int | float) -> PygameRendering:
        return PygameRendering(Surface((width, height), flags=pygame.SRCALPHA))

    @classmethod
    def zero(cls) -> Rendering:
        return cls.new_surface(0, 0)

    @classmethod
    def new_color(cls, color: Color) -> PygameColor:
        return PygameColor(color.r, color.g, color.b, color.a)

    @classmethod
    def new_rect(cls, rectangle: Rectangle) -> Rect:
        return Rect(rectangle.left, rectangle.top, rectangle.width, rectangle.height)

    @classmethod
    def fill(
        cls, surface: Rendering, color: Color, rectangle: Rectangle | None = None
    ) -> None:
        deref(surface).fill(
            cls.new_color(color),
            cls.new_rect(rectangle) if rectangle is not None else None,
        )

    @classmethod
    def blit(cls, dst: Rendering, src: Rendering, position: _Position) -> None:
        deref(dst).blit(deref(src), position)

    @classmethod
    def line(
        cls, surface: Rendering, color: Color, start: _Position, end: _Position
    ) -> None:
        # `pygame.draw.line` over `pygame.gfxdraw.line`: faster on tight
        # loops (gradients trace hundreds of lines per frame) and supports
        # a `width` parameter if we ever need thicker strokes. `gfxdraw`
        # only offers pixel-exact non-AA single-pixel lines.
        pygame.draw.line(deref(surface), Pygame.new_color(color), start, end)

    @classmethod
    def rectangle(cls, surface: Rendering, rectangle: Rectangle, color: Color) -> None:
        pygame.gfxdraw.rectangle(
            deref(surface), cls.new_rect(rectangle), Pygame.new_color(color)
        )

    @classmethod
    def box(cls, surface: Rendering, rectangle: Rectangle, color: Color) -> None:
        pygame.gfxdraw.box(
            deref(surface), cls.new_rect(rectangle), Pygame.new_color(color)
        )

    @classmethod
    def filled_polygon(
        cls, surface: Rendering, points: Sequence[_Position], color: Color
    ) -> None:
        pygame.gfxdraw.filled_polygon(deref(surface), points, Pygame.new_color(color))

    @classmethod
    def smoothscale(
        cls, surface: Rendering, width: int | float, height: int | float
    ) -> Rendering:
        return PygameRendering(
            pygame.transform.smoothscale(deref(surface), (width, height))
        )

    @classmethod
    def copy(cls, surface: Rendering) -> Rendering:
        return PygameRendering(deref(surface).copy())

    @classmethod
    def image(cls, image: Image) -> Rendering:
        # `frombytes` copies the buffer; `frombuffer` would share it and
        # require the PIL image to stay alive for as long as the Surface
        # exists. A self-contained Surface is safer at this boundary and
        # the copy cost is dwarfed by the upstream PIL decode + tobytes.

        # NB: convert_alpha() changes the pixel format of image
        # to match the display while preserving transparency (alpha).
        return PygameRendering(
            pygame.image.frombytes(image.tobytes(), image.size, "RGBA").convert_alpha()
        )

    @classmethod
    def post_event(cls, event: VidereEvent) -> None:
        event_type = type(event)
        callback = cls._on_post.get(type(event))
        if callback is None:
            raise NotImplementedError(event_type, event)
        callback(cls, event)

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
