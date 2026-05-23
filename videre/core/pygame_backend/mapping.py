from typing import Sequence

import pygame

from videre.core.events import Key, KeyboardEntry, KeyMod, MouseButton
from videre.core.pygame_backend.definitions import Event

_PYGAME_MOUSE_BUTTON: dict[int, MouseButton] = {
    pygame.BUTTON_LEFT: MouseButton.BUTTON_LEFT,
    pygame.BUTTON_MIDDLE: MouseButton.BUTTON_MIDDLE,
    pygame.BUTTON_RIGHT: MouseButton.BUTTON_RIGHT,
    pygame.BUTTON_WHEELDOWN: MouseButton.BUTTON_WHEELDOWN,
    pygame.BUTTON_WHEELUP: MouseButton.BUTTON_WHEELUP,
    pygame.BUTTON_X1: MouseButton.BUTTON_X1,
    pygame.BUTTON_X2: MouseButton.BUTTON_X2,
}

_PYGAME_KEY: dict[int, Key] = {
    pygame.K_BACKSPACE: Key.BACKSPACE,
    pygame.K_TAB: Key.TAB,
    pygame.K_RETURN: Key.ENTER,
    pygame.K_ESCAPE: Key.ESCAPE,
    pygame.K_DELETE: Key.DELETE,
    pygame.K_UP: Key.UP,
    pygame.K_DOWN: Key.DOWN,
    pygame.K_LEFT: Key.LEFT,
    pygame.K_RIGHT: Key.RIGHT,
    pygame.K_HOME: Key.HOME,
    pygame.K_END: Key.END,
    pygame.K_PAGEUP: Key.PAGEUP,
    pygame.K_PAGEDOWN: Key.PAGEDOWN,
    pygame.K_PRINTSCREEN: Key.PRINTSCREEN,
    pygame.K_SPACE: Key.SPACE,
    pygame.K_a: Key.a,
    pygame.K_c: Key.c,
    pygame.K_v: Key.v,
}

_PYGAME_KEYMOD: dict[int, KeyMod] = {
    pygame.KMOD_LSHIFT: KeyMod.LSHIFT,
    pygame.KMOD_RSHIFT: KeyMod.RSHIFT,
    pygame.KMOD_LCTRL: KeyMod.LCTRL,
    pygame.KMOD_RCTRL: KeyMod.RCTRL,
    pygame.KMOD_RALT: KeyMod.RALT,
    pygame.KMOD_LALT: KeyMod.LALT,
    pygame.KMOD_CAPS: KeyMod.CAPS,
}


_INDEX_BUTTONS = (
    MouseButton.BUTTON_LEFT,
    MouseButton.BUTTON_MIDDLE,
    MouseButton.BUTTON_RIGHT,
)


def pygame_to_mouse_button(inp: int) -> MouseButton:
    return _PYGAME_MOUSE_BUTTON[inp]


def pygame_to_mouse_buttons(flags: Sequence[int]) -> tuple[MouseButton, ...]:
    return tuple(button for button, flag in zip(_INDEX_BUTTONS, flags) if flag)


def pygame_to_keyboard_entry(event: Event) -> KeyboardEntry:
    return KeyboardEntry(
        modifiers=frozenset(
            mod for py_mod, mod in _PYGAME_KEYMOD.items() if event.mod & py_mod
        ),
        key=_PYGAME_KEY.get(event.key),
        unicode=event.unicode,
    )
