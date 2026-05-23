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

_Position: TypeAlias = tuple[int | float, int | float]


class Pygame:
    __slots__ = ()

    @classmethod
    def new_surface(cls, width: int | float, height: int | float) -> Surface:
        return Surface((width, height), flags=pygame.SRCALPHA)

    @classmethod
    def zero(cls) -> Surface:
        return Surface((0, 0), flags=pygame.SRCALPHA)

    @classmethod
    def new_color(cls, color: Color) -> PygameColor:
        return PygameColor(color.r, color.g, color.b, color.a)

    @classmethod
    def fill(cls, surface: Surface, color: Color) -> None:
        surface.fill(cls.new_color(color))

    @classmethod
    def blit(cls, dst: Surface, src: Surface, position: _Position) -> None:
        dst.blit(src, position)

    @classmethod
    def line(
        cls, surface: Surface, color: Color, start: _Position, end: _Position
    ) -> None:
        # `pygame.draw.line` over `pygame.gfxdraw.line`: faster on tight
        # loops (gradients trace hundreds of lines per frame) and supports
        # a `width` parameter if we ever need thicker strokes. `gfxdraw`
        # only offers pixel-exact non-AA single-pixel lines.
        pygame.draw.line(surface, Pygame.new_color(color), start, end)

    @classmethod
    def rectangle(cls, surface: Surface, rectangle: Rect, color: Color) -> None:
        pygame.gfxdraw.rectangle(surface, rectangle, Pygame.new_color(color))

    @classmethod
    def box(cls, surface: Surface, rectangle: Rect, color: Color) -> None:
        pygame.gfxdraw.box(surface, rectangle, Pygame.new_color(color))

    @classmethod
    def filled_polygon(
        cls, surface: Surface, points: Sequence[_Position], color: Color
    ) -> None:
        pygame.gfxdraw.filled_polygon(surface, points, Pygame.new_color(color))

    @classmethod
    def smoothscale(
        cls, surface: Surface, width: int | float, height: int | float
    ) -> Surface:
        return pygame.transform.smoothscale(surface, (width, height))

    @classmethod
    def image(cls, image: Image) -> Surface:
        # `frombytes` copies the buffer; `frombuffer` would share it and
        # require the PIL image to stay alive for as long as the Surface
        # exists. A self-contained Surface is safer at this boundary and
        # the copy cost is dwarfed by the upstream PIL decode + tobytes.
        return pygame.image.frombytes(image.tobytes(), image.size, "RGBA")

    @classmethod
    def post_event(cls, event: VidereEvent) -> None:
        event_type = type(event)
        if isinstance(event, MouseButtonDownEvent):
            event_data = {
                "pos": (event.x, event.y),
                "button": mouse_button_to_pygame(event.button),
            }
            pygame.event.post(Event(pygame.MOUSEBUTTONDOWN, event_data))
        elif isinstance(event, MouseButtonUpEvent):
            event_data = {
                "pos": (event.x, event.y),
                "button": mouse_button_to_pygame(event.button),
            }
            pygame.event.post(Event(pygame.MOUSEBUTTONUP, event_data))
        elif isinstance(event, MouseMotionEvent):
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
        elif isinstance(event, MouseWheelEvent):
            event_data = {"x": event.wheel_dx, "y": event.wheel_dy}
            pygame.event.post(Event(pygame.MOUSEWHEEL, event_data))
        elif isinstance(event, KeyDownEvent):
            pygame.event.post(
                Event(pygame.KEYDOWN, keyboard_entry_to_pygame_dict(event.entry))
            )
        elif isinstance(event, TextInputEvent):
            event_data = {"text": event.text}
            pygame.event.post(Event(pygame.TEXTINPUT, event_data))
        elif isinstance(event, WindowLeaveEvent):
            pygame.event.post(Event(pygame.WINDOWLEAVE))
        elif isinstance(event, ExitEvent):
            pygame.event.post(Event(pygame.QUIT))
        else:
            raise NotImplementedError(event_type, event)
