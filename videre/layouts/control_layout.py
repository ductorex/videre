from videre.core.pygame_utils import Surface
from videre.layouts.abstractlayout import AbstractLayout
from videre.widgets.widget import Widget


class ControlLayout(AbstractLayout):
    __slots__ = ()
    __wprops__ = {}
    __size__ = 1

    def __init__(self, control: Widget, **kwargs):
        super().__init__([control], **kwargs)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        (control,) = self._controls()
        return control.render(window, width, height)
