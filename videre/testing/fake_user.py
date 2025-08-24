import pygame
from pygame.event import Event

from videre.widgets.widget import Widget


class FakeUser:
    @classmethod
    def click(cls, button: Widget):
        x = button.global_x + button.rendered_width // 2
        y = button.global_y + button.rendered_height // 2
        return cls.click_at(x, y)

    @classmethod
    def click_at(cls, x: int, y: int, button=pygame.BUTTON_LEFT):
        """Click at specific coordinates"""
        event_data = {"pos": (x, y), "button": button}
        pygame.event.post(Event(pygame.MOUSEBUTTONDOWN, event_data))
        pygame.event.post(Event(pygame.MOUSEBUTTONUP, event_data))

    @classmethod
    def mouse_motion(
        cls, x: int, y: int, button_left=False, button_middle=False, button_right=False
    ):
        event_data = {
            "pos": (x, y),
            "rel": (0, 0),
            "touch": False,
            "buttons": (int(button_left), int(button_middle), int(button_right)),
        }
        pygame.event.post(Event(pygame.MOUSEMOTION, event_data))

    @classmethod
    def mouve_over(cls, widget: Widget):
        """Move mouse over a widget"""
        x = widget.global_x + widget.rendered_width // 2
        y = widget.global_y + widget.rendered_height // 2
        cls.mouse_motion(x, y)

    @classmethod
    def mouse_down(cls, x: int, y: int, button=pygame.BUTTON_LEFT):
        """Simulate mouse down at specific coordinates"""
        event_data = {"pos": (x, y), "button": button}
        pygame.event.post(Event(pygame.MOUSEBUTTONDOWN, event_data))

    @classmethod
    def mouse_up(cls, x: int, y: int, button=pygame.BUTTON_LEFT):
        """Simulate mouse up at specific coordinates"""
        event_data = {"pos": (x, y), "button": button}
        pygame.event.post(Event(pygame.MOUSEBUTTONUP, event_data))

    @classmethod
    def mouse_wheel(cls, x: int, y: int):
        event_data = {"x": x, "y": y}
        pygame.event.post(Event(pygame.MOUSEWHEEL, event_data))

    @classmethod
    def key_down(cls, key: int, mod: int = 0, unicode: str = ""):
        """Simulate key down event"""
        event_data = {"key": key, "mod": mod, "unicode": unicode}
        pygame.event.post(Event(pygame.KEYDOWN, event_data))

    @classmethod
    def keyboard_entry(
        cls, key: str, ctrl: bool = False, alt: bool = False, shift: bool = False
    ):
        """Simulate keyboard entry with character and modifiers"""
        # Build modifier mask
        mod = 0
        if ctrl:
            mod |= pygame.KMOD_CTRL
        if alt:
            mod |= pygame.KMOD_ALT
        if shift:
            mod |= pygame.KMOD_SHIFT

        # Convert character to pygame key code
        key_map = {
            "backspace": pygame.K_BACKSPACE,
            "tab": pygame.K_TAB,
            "enter": pygame.K_RETURN,
            "escape": pygame.K_ESCAPE,
            "delete": pygame.K_DELETE,
            "up": pygame.K_UP,
            "down": pygame.K_DOWN,
            "left": pygame.K_LEFT,
            "right": pygame.K_RIGHT,
            "home": pygame.K_HOME,
            "end": pygame.K_END,
            "pageup": pygame.K_PAGEUP,
            "pagedown": pygame.K_PAGEDOWN,
            "space": pygame.K_SPACE,
        }
        key = key.strip().lower()
        if key in key_map:
            pygame_key = key_map[key]
        else:
            assert len(key) == 1
            pygame_key = ord(key)
        cls.key_down(pygame_key, mod)

    @classmethod
    def text_input(cls, text: str):
        """Simulate text input"""
        event_data = {"text": text}
        pygame.event.post(Event(pygame.TEXTINPUT, event_data))

    @classmethod
    def quit(cls):
        """Simulate quitting the application"""
        pygame.event.post(Event(pygame.QUIT))
