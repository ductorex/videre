import pytest

from videre.colors import Color, ColorDef
from videre.core.events import KeyboardEntry
from videre.core.pygame_backend.primitives import Pygame
from videre.testing.utils import HD, SD
from videre.widgets.widget import Widget


def win_parameters(
    *,
    width: int | None = None,
    height: int | None = None,
    background: ColorDef | None = None,
):
    parameters = {}
    if width is not None:
        parameters["width"] = width
    if height is not None:
        parameters["height"] = height
    if background is not None:
        parameters["background"] = background
    return pytest.mark.win_params(parameters)


def win_hd_parameters(*, background: ColorDef | None = None):
    return win_parameters(**HD, background=background)


def win_sd_parameters(*, background: ColorDef | None = None):
    return win_parameters(**SD, background=background)


class TrackerWidget(Widget):
    """Widget that tracks received events for testing."""

    __slots__ = ("events",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = []

    def draw(self, window, width=None, height=None):
        surface = Pygame.new_surface(width or 50, height or 50)
        Pygame.fill(surface, Color(200, 200, 200))
        return surface

    def handle_mouse_wheel(self, x, y, shift):
        self.events.append(("mouse_wheel", x, y, shift))
        return True

    def handle_text_input(self, text):
        self.events.append(("text_input", text))
        return True

    def handle_keydown(self, key: KeyboardEntry):
        self.events.append(("keydown", key))
        return self

    def handle_focus_in(self):
        self.events.append(("focus_in",))
        return self

    def handle_focus_out(self):
        self.events.append(("focus_out",))

    def handle_click(self, button):
        self.events.append(("click", button))
        return self

    def handle_mouse_enter(self, event):
        self.events.append(("mouse_enter",))
        return self

    def handle_mouse_over(self, event):
        self.events.append(("mouse_over",))
        return self

    def handle_mouse_exit(self):
        self.events.append(("mouse_exit",))
        return self

    def handle_mouse_down(self, event):
        self.events.append(("mouse_down",))
        return self

    def handle_mouse_up(self, event):
        self.events.append(("mouse_up",))
        return self

    def handle_mouse_down_move(self, event):
        self.events.append(("mouse_down_move",))
        return self

    def handle_mouse_down_canceled(self, button):
        self.events.append(("mouse_down_canceled", button))
        return self
