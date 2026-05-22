from videre.core.pygame_backend.definitions import Surface
from videre.core.pygame_backend.primitives import Pygame
from videre.widgets.widget import Widget


class EmptyWidget(Widget):
    __wprops__ = {}
    __slots__ = ()

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Surface:
        return Pygame.new_surface(0, 0)
