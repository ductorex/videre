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

    def render(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        # Tick the clock and re-arm the next frame before the regular render gate.
        # `on_frame` is fired here (not in `draw`) so it runs once per animation
        # frame. It also fires when the animator is redrawn for a real change
        # (`self._dirty`) — e.g. its callback or control was swapped — which the
        # per-frame re-arm never sets (it dirties only ancestors).
        due = self._check_fps(window.nb_frames)
        if (due or self._dirty) and self.on_frame:
            self.on_frame(self.control, self._nb_frames)
        window.request_frame(self)
        return super().render(window, width, height)

    def _check_fps(self, nb_frames: int) -> bool:
        if self._framing.needs_frame(nb_frames):
            self._nb_frames += 1
            return True
        return False

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        return self.control.render(window, width, height)
