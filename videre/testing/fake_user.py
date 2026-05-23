from typing import Sequence

from videre.core.events import (
    ExitEvent,
    Key,
    KeyboardEntry,
    KeyDownEvent,
    KeyMod,
    MouseButton,
    MouseButtonDownEvent,
    MouseButtonUpEvent,
    MouseMotionEvent,
    MouseWheelEvent,
    TextInputEvent,
)
from videre.core.pygame_backend.backend import PygameBackend
from videre.core.pygame_backend.mapping import pygame_to_mouse_buttons
from videre.widgets.widget import Widget


class FakeUser:
    __slots__ = ("_backend",)

    def __init__(self, backend: PygameBackend):
        self._backend = backend

    def click(self, button: Widget):
        x = button.global_x + button.rendered_width // 2
        y = button.global_y + button.rendered_height // 2
        self.click_at(x, y)

    def click_at(self, x: int, y: int, button: MouseButton = MouseButton.BUTTON_LEFT):
        """Click at specific coordinates"""
        self._backend.post_event(MouseButtonDownEvent(x=x, y=y, buttons=(button,)))
        self._backend.post_event(MouseButtonUpEvent(x=x, y=y, buttons=(button,)))

    def mouse_motion(
        self, x: int, y: int, button_left=False, button_middle=False, button_right=False
    ):
        self._backend.post_event(
            MouseMotionEvent(
                x=x,
                y=y,
                buttons=pygame_to_mouse_buttons(
                    (button_left, button_middle, button_right)
                ),
            )
        )

    def mouve_over(self, widget: Widget):
        """Move mouse over a widget"""
        x = widget.global_x + widget.rendered_width // 2
        y = widget.global_y + widget.rendered_height // 2
        self.mouse_motion(x, y)

    def mouse_down(self, x: int, y: int, button: MouseButton = MouseButton.BUTTON_LEFT):
        """Simulate mouse down at specific coordinates"""
        self._backend.post_event(MouseButtonDownEvent(x=x, y=y, buttons=(button,)))

    def mouse_up(self, x: int, y: int, button: MouseButton = MouseButton.BUTTON_LEFT):
        """Simulate mouse up at specific coordinates"""
        self._backend.post_event(MouseButtonUpEvent(x=x, y=y, buttons=(button,)))

    def mouse_wheel(self, x: int, y: int):
        self._backend.post_event(
            MouseWheelEvent(wheel_dx=x, wheel_dy=y, mouse_x=0, mouse_y=0, shift=False)
        )

    def key_down(self, key: Key, modifiers: Sequence[KeyMod] = (), unicode: str = ""):
        """Simulate key down event"""
        self._backend.post_event(
            KeyDownEvent(
                entry=KeyboardEntry(
                    modifiers=frozenset(modifiers), key=key, unicode=unicode
                )
            )
        )

    def keyboard_entry(
        self,
        key_string: str,
        ctrl: bool = False,
        alt: bool = False,
        shift: bool = False,
    ):
        """Simulate keyboard entry with character and modifiers"""
        key = getattr(Key, key_string.upper())
        modifiers = []
        if ctrl:
            modifiers.append(KeyMod.LCTRL)
        if alt:
            modifiers.append(KeyMod.LALT)
        if shift:
            modifiers.append(KeyMod.LSHIFT)
        self.key_down(key, modifiers)

    def text_input(self, text: str):
        """Simulate text input"""
        self._backend.post_event(TextInputEvent(text))

    def quit(self):
        """Simulate quitting the application"""
        self._backend.post_event(ExitEvent())
