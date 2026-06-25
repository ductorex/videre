import numpy as np
import pytest

from videre.colors import Color, ColorDef
from videre.core.abstract_backend import AbstractBackend
from videre.core.drawer import Drawer, Drawing
from videre.core.events import KeyboardEntry
from videre.core.rendering_result import Rendering
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

    def draw(self, window, width=None, height=None) -> Drawer:
        surface = Drawer(width or 50, height or 50)
        Drawing.fill(surface, Color(200, 200, 200))
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


def rasterize(backend: AbstractBackend, drawer: Drawer) -> Rendering:
    """Replay a Drawer's command IR to a real surface for pixel inspection.

    The shaped renderer (`render_text` / `render_char` / `document.render`)
    now returns a paint-free `Drawer`; tests that read pixels (`pixels_*`) or
    serialize a snapshot (`_png`) need the rasterized `Rendering`. Mirrors what
    `Window._refresh` does in production.
    """
    return backend.render_drawer(drawer)


def _channel(rendering: Rendering, attr: str) -> np.ndarray:
    """Backend-agnostic replacement for ``pygame.surfarray.pixels_*``.

    Reads a single color channel of ``rendering`` through ``get_at`` and
    returns an ``[x][y]`` int array, matching pygame surfarray's
    (width, height) shape and indexing so callers' assertions are
    unchanged. Slow (per-pixel), but tests only.
    """
    width, height = rendering.get_width(), rendering.get_height()
    return np.array(
        [
            [getattr(rendering.get_at((x, y)), attr) for y in range(height)]
            for x in range(width)
        ],
        dtype=int,
    )


def pixels_alpha(rendering: Rendering) -> np.ndarray:
    return _channel(rendering, "a")


def pixels_red(rendering: Rendering) -> np.ndarray:
    return _channel(rendering, "r")


def pixels_green(rendering: Rendering) -> np.ndarray:
    return _channel(rendering, "g")


def pixels_blue(rendering: Rendering) -> np.ndarray:
    return _channel(rendering, "b")
