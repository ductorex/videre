from collections.abc import Callable

from videre.core.drawer import Drawer
from videre.core.framing import FPS, AbstractFraming
from videre.layouts.abstractlayout import AbstractLayout
from videre.widgets.widget import Widget

# OnFrame(control, frame_rank), frame_rank >= 1
OnFrame = Callable[[Widget, int], None]


class Animator(AbstractLayout):
    __wprops__ = {"on_frame"}
    __slots__ = ("_nb_frames", "_framing")
    __size__ = 1

    def __init__(
        self,
        control: Widget,
        on_frame: OnFrame | None = None,
        framing: AbstractFraming | None = None,
        **kwargs,
    ):
        super().__init__([control], **kwargs)
        self._nb_frames = 0
        self._framing = framing or FPS()
        self.on_frame = on_frame

    @property
    def control(self) -> Widget:
        (control,) = self._controls()
        return control

    @control.setter
    def control(self, control: Widget):
        self._set_controls([control])

    @property
    def on_frame(self) -> OnFrame | None:
        return self._get_wprop("on_frame")

    @on_frame.setter
    def on_frame(self, callback: OnFrame | None):
        self._set_wprop("on_frame", callback)

    @property
    def frame_rank(self) -> int:
        return self._nb_frames

    def has_changed(self) -> bool:
        self._check_fps()
        return super().has_changed()

    def _check_fps(self):
        if self._framing.needs_frame(self.get_window().nb_frames):
            self._nb_frames += 1
            self.update()

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        control = self.control
        on_frame = self.on_frame
        if on_frame:
            on_frame(control, self._nb_frames)
        return control.render(window, width, height)
