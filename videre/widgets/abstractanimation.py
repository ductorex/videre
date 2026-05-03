from abc import abstractmethod

from videre.core.framing import FPS, AbstractFraming
from videre.widgets.widget import Widget


class AbstractAnimation(Widget):
    __wprops__ = {}
    __slots__ = ("_nb_frames", "_framing")

    def __init__(self, framing: AbstractFraming | None = None, **kwargs):
        super().__init__(**kwargs)
        self._nb_frames = 0
        self._framing = framing or FPS()

    def has_changed(self) -> bool:
        self._check_fps()
        return super().has_changed()

    def _check_fps(self):
        if self._framing.needs_frame(self.get_window().nb_frames):
            self._nb_frames += 1
            self._on_frame()

    @abstractmethod
    def _on_frame(self):
        raise NotImplementedError()
