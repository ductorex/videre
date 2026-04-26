from videre.core.pygame_utils import Surface
from videre.widgets.widget import Widget


class EmptyWidget(Widget):
    __wprops__ = {}
    __slots__ = ()

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Surface:
        return window.new_surface(0, 0)
