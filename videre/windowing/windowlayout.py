from videre.colors import Colors
from videre.core.pygame_utils import Color, Surface
from videre.layouts.abstract_controls_layout import AbstractControlsLayout


class WindowLayout(AbstractControlsLayout):
    __wprops__ = {"background"}
    __slots__ = ()
    _FILL = Colors.white
    __capture_mouse__ = True

    def __init__(self, background: Color | None = None):
        super().__init__()
        self.background = background

    @property
    def background(self) -> Color:
        return self._get_wprop("background")

    @background.setter
    def background(self, value: Color | None):
        self._set_wprop("background", value or self._FILL)

    def render(self, window, width: int = None, height: int = None) -> Surface:
        screen = window.get_screen()
        return super().render(window, screen.get_width(), screen.get_height())

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        screen = window.get_screen()

        screen_width, screen_height = screen.get_width(), screen.get_height()
        screen.fill(self.background)
        for control in self.controls:
            surface = control.render(window, screen_width, screen_height)
            screen.blit(surface, (control.x, control.y))

        return screen
