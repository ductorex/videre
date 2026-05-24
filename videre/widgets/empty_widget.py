from videre.core.rendering_result import Rendering
from videre.widgets.widget import Widget


class EmptyWidget(Widget):
    __wprops__ = {}
    __slots__ = ()

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Rendering:
        return window.backend.new_surface(0, 0)
