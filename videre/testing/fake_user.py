from typing import Sequence

from videre.core.abstract_backend import AbstractWindowing
from videre.core.dpi import DevicePx, LogicalPx, to_device
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
    WindowLeaveEvent,
)
from videre.core.pygame_backend.mapping import pygame_to_mouse_buttons
from videre.widgets.widget import Widget


class FakeUser:
    __slots__ = ("_windowing",)

    def __init__(self, windowing: AbstractWindowing):
        self._windowing = windowing

    def _to_device(self, value: LogicalPx) -> DevicePx:
        # FakeUser speaks logical (widget positions); posted events mimic
        # the OS, which delivers device pixels. Identity at scale 1.0.
        scale = self._windowing.scale_factor
        return value if scale == 1.0 else to_device(value, scale)

    def click(self, button: Widget):
        x = button.global_x + button.rendered_width // 2
        y = button.global_y + button.rendered_height // 2
        self.click_at(x, y)

    def click_at(self, x: int, y: int, button: MouseButton = MouseButton.BUTTON_LEFT):
        """Click at specific coordinates"""
        x, y = self._to_device(x), self._to_device(y)
        self._windowing.post_event(MouseButtonDownEvent(x=x, y=y, buttons=(button,)))
        self._windowing.post_event(MouseButtonUpEvent(x=x, y=y, buttons=(button,)))

    def mouse_motion(
        self, x: int, y: int, button_left=False, button_middle=False, button_right=False
    ):
        self._windowing.post_event(
            MouseMotionEvent(
                x=self._to_device(x),
                y=self._to_device(y),
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
        x, y = self._to_device(x), self._to_device(y)
        self._windowing.post_event(MouseButtonDownEvent(x=x, y=y, buttons=(button,)))

    def mouse_up(self, x: int, y: int, button: MouseButton = MouseButton.BUTTON_LEFT):
        """Simulate mouse up at specific coordinates"""
        x, y = self._to_device(x), self._to_device(y)
        self._windowing.post_event(MouseButtonUpEvent(x=x, y=y, buttons=(button,)))

    def mouse_wheel(
        self, x: int, y: int, shift: bool = False, mouse_x: int = 0, mouse_y: int = 0
    ):
        self._windowing.post_event(
            MouseWheelEvent(
                wheel_dx=x,
                wheel_dy=y,
                mouse_x=self._to_device(mouse_x),
                mouse_y=self._to_device(mouse_y),
                shift=shift,
            )
        )

    def key_down(self, key: Key, modifiers: Sequence[KeyMod] = (), unicode: str = ""):
        """Simulate key down event"""
        self._windowing.post_event(
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
        self._windowing.post_event(TextInputEvent(text))

    def quit(self):
        """Simulate quitting the application"""
        self._windowing.post_event(ExitEvent())

    def leave(self):
        self._windowing.post_event(WindowLeaveEvent())

    def resize(self, width: int, height: int):
        self._windowing.resize_screen(width, height)
