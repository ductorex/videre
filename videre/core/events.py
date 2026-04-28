from dataclasses import dataclass, field
from typing import Sequence

import pygame
from pygame.event import Event

from videre import MouseButton


@dataclass(slots=True)
class MouseEvent:
    x: int = 0
    y: int = 0
    dx: int = 0
    dy: int = 0
    buttons: Sequence[MouseButton] = field(default_factory=list)

    @property
    def button(self) -> MouseButton:
        (button,) = self.buttons
        return button

    @property
    def button_left(self) -> bool:
        return MouseButton.BUTTON_LEFT in self.buttons

    @property
    def button_middle(self) -> bool:
        return MouseButton.BUTTON_MIDDLE in self.buttons

    @property
    def button_right(self) -> bool:
        return MouseButton.BUTTON_RIGHT in self.buttons

    @classmethod
    def from_mouse_motion(cls, event: Event, x=None, y=None):
        buttons = []
        if event.buttons[0]:
            buttons.append(MouseButton.BUTTON_LEFT)
        if event.buttons[1]:
            buttons.append(MouseButton.BUTTON_MIDDLE)
        if event.buttons[2]:
            buttons.append(MouseButton.BUTTON_RIGHT)
        return cls(
            x=event.pos[0] if x is None else x,
            y=event.pos[1] if y is None else y,
            dx=event.rel[0],
            dy=event.rel[1],
            buttons=buttons,
        )

    def with_coordinates(self, x: int, y: int):
        return MouseEvent(x=x, y=y, dx=self.dx, dy=self.dy, buttons=list(self.buttons))


class KeyboardEntry:
    __slots__ = ("_mod", "_key", "unicode")

    def __init__(self, event: Event):
        self._mod = event.mod
        self._key = event.key
        self.unicode = event.unicode

    lshift = property(lambda self: self._mod & pygame.KMOD_LSHIFT)
    rshift = property(lambda self: self._mod & pygame.KMOD_RSHIFT)
    lctrl = property(lambda self: self._mod & pygame.KMOD_LCTRL)
    rctrl = property(lambda self: self._mod & pygame.KMOD_RCTRL)
    ralt = property(lambda self: self._mod & pygame.KMOD_RALT)
    lalt = property(lambda self: self._mod & pygame.KMOD_LALT)

    backspace = property(lambda self: self._key == pygame.K_BACKSPACE)
    tab = property(lambda self: self._key == pygame.K_TAB)
    enter = property(lambda self: self._key == pygame.K_RETURN)
    escape = property(lambda self: self._key == pygame.K_ESCAPE)
    delete = property(lambda self: self._key == pygame.K_DELETE)
    up = property(lambda self: self._key == pygame.K_UP)
    down = property(lambda self: self._key == pygame.K_DOWN)
    left = property(lambda self: self._key == pygame.K_LEFT)
    right = property(lambda self: self._key == pygame.K_RIGHT)
    home = property(lambda self: self._key == pygame.K_HOME)
    end = property(lambda self: self._key == pygame.K_END)
    pageup = property(lambda self: self._key == pygame.K_PAGEUP)
    pagedown = property(lambda self: self._key == pygame.K_PAGEDOWN)
    printscreen = property(lambda self: self._key == pygame.K_PRINTSCREEN)

    a = property(lambda self: self._key == pygame.K_a)
    c = property(lambda self: self._key == pygame.K_c)
    v = property(lambda self: self._key == pygame.K_v)

    @property
    def caps(self) -> int:
        return self._mod & pygame.KMOD_CAPS

    @property
    def ctrl(self) -> int:
        return self._mod & pygame.KMOD_CTRL

    @property
    def alt(self) -> int:
        return self._mod & pygame.KMOD_ALT

    @property
    def shift(self) -> int:
        return self._mod & pygame.KMOD_SHIFT

    def __repr__(self):
        return " + ".join(
            key for key in ("caps", "ctrl", "alt", "shift") if getattr(self, key)
        )


class CustomEvents:
    CALLBACK_EVENT = pygame.event.custom_type()
    NOTIFICATION_EVENT = pygame.event.custom_type()

    @classmethod
    def callback_event(cls, function, *args, **kwargs):
        return Event(
            cls.CALLBACK_EVENT, {"function": function, "args": args, "kwargs": kwargs}
        )

    @classmethod
    def notification_event(cls, something):
        return Event(cls.NOTIFICATION_EVENT, {"notification": something})
