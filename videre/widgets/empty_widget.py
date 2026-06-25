from videre.core.drawer import Drawer
from videre.widgets.widget import Widget


class EmptyWidget(Widget):
    __wprops__ = {}
    __slots__ = ()

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        return Drawer()
