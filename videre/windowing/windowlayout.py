from typing import TYPE_CHECKING, Sequence

from videre.colors import Color, Colors
from videre.core.events import KeyboardEntry
from videre.core.pygame_backend.definitions import Surface
from videre.core.pygame_backend.primitives import Pygame
from videre.layouts.abstract_controls_layout import AbstractControlsLayout
from videre.widgets.widget import Widget
from videre.windowing.context import Context
from videre.windowing.fancybox import Fancybox

if TYPE_CHECKING:
    from videre.windowing.window import Window


class WindowLayout(AbstractControlsLayout):
    __wprops__ = {"background"}
    __slots__ = ("_screen", "_fancybox", "_context", "_user_controls")
    _FILL = Colors.white
    __capture_mouse__ = True

    def __init__(self, background: Color | None = None):
        super().__init__()
        self.background = background
        self._user_controls: list[Widget] = []
        self._fancybox: Fancybox | None = None
        self._context: Context | None = None
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

    def has_fancybox(self) -> bool:
        return self._fancybox is not None

    def set_fancybox(self, fancybox: Fancybox | None):
        if fancybox is not None:
            assert self._fancybox is None
        self._fancybox = fancybox
        self._rebuild()

    def has_context(self, relative: Widget | None = None) -> bool:
        """
        Return True if a context is currently active.
        :param relative: optional relative.
            If given, return True only if
            current context is attached to this relative.
        """
        return self._context is not None and (
            relative is None or self._context.relative is relative
        )

    def set_context(self, context: Context | None):
        self._context = context
        self._rebuild()

    @property
    def controls(self) -> tuple[Widget, ...]:
        """Return layout controls, excluding fancybox and context."""
        return tuple(self._user_controls)

    @controls.setter
    def controls(self, controls: Sequence[Widget]):
        """Set layout controls, excluding fancybox and context."""
        self._user_controls = list(controls)
        self._rebuild()

    def _rebuild(self):
        children = list(self._user_controls)
        if self._fancybox is not None:
            children.append(self._fancybox)
        if self._context is not None:
            children.append(self._context)
        self._set_controls(children)

    def handle_keydown(self, key: KeyboardEntry):
        if key.escape:
            if self.has_context():
                self.set_context(None)
            elif self.has_fancybox():
                self.set_fancybox(None)

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
        for control in self._controls():
            surface = control.render(window, screen_width, screen_height)
            Pygame.blit(screen, surface, (control.x, control.y))

        return screen
