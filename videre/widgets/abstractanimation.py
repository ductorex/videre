from abc import abstractmethod

from videre.core.drawer import Drawer
from videre.core.framing import FPS, AbstractFraming
from videre.widgets.widget import Widget


class AbstractAnimation(Widget):
    __wprops__ = {}
    __slots__ = ("_nb_frames", "_framing")

    def __init__(self, framing: AbstractFraming | None = None, **kwargs):
        super().__init__(**kwargs)
        self._nb_frames = 0
        self._framing = framing or FPS()

    def render(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        # Tick the clock and re-arm the next frame before the regular render gate.
        # Done here (not in `draw`) so subclasses only implement `draw` and still
        # animate.
        self._check_fps(window.nb_frames)
        window.request_frame(self)
        return super().render(window, width, height)

    def _check_fps(self, nb_frames: int) -> bool:
        if self._framing.needs_frame(nb_frames):
            self._nb_frames += 1
            self._on_frame()
            return True
        return False

    @abstractmethod
    def _on_frame(self):
        raise NotImplementedError()
