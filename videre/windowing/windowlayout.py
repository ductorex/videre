from typing import TYPE_CHECKING

from videre.colors import Color, Colors
from videre.core.pygame_backend.definitions import Surface
from videre.core.pygame_backend.primitives import Pygame
from videre.layouts.abstract_controls_layout import AbstractControlsLayout

if TYPE_CHECKING:
    from videre.windowing.window import Window


class WindowLayout(AbstractControlsLayout):
    __wprops__ = {"background"}
    __slots__ = ("_screen",)
    _FILL = Colors.white
    __capture_mouse__ = True

    def __init__(self, background: Color | None = None):
        super().__init__()
        self.background = background
        self._screen: Surface | None = None

    @property
    def background(self) -> Color:
        return self._get_wprop("background")

    @background.setter
    def background(self, value: Color | None):
        self._set_wprop("background", value or self._FILL)

    @property
    def screen(self) -> Surface:
        if self._screen is None:
            raise RuntimeError(f"{self} requires a screen")
        return self._screen

    @screen.setter
    def screen(self, screen: Surface):
        self._screen = screen

    def render(
        self, window: "Window", width: int | None = None, height: int | None = None
    ) -> Surface:
        screen = self.screen
        return super().render(window, screen.get_width(), screen.get_height())

    def draw(
        self, window: "Window", width: int | None = None, height: int | None = None
    ) -> Surface:
        screen = self.screen

        screen_width, screen_height = screen.get_width(), screen.get_height()
        screen.fill(Pygame.new_color(self.background))
        for control in self.controls:
            surface = control.render(window, screen_width, screen_height)
            Pygame.blit(screen, surface, (control.x, control.y))

        return screen
