import math
from collections.abc import Callable

import pygame

from videre import WINDOW_FPS
from videre.core.pygame_utils import Surface
from videre.layouts.abstractlayout import AbstractLayout
from videre.widgets.widget import Widget

# OnFrame(control, frame_rank), frame_rank >= 1
OnFrame = Callable[[Widget, int], None]


class Animator(AbstractLayout):
    __wprops__ = {"on_frame"}
    __slots__ = ("_clock", "_fps", "_delay_ms", "_spent_ms", "_nb_frames")
    __size__ = 1

    def __init__(
        self, control: Widget, on_frame: OnFrame | None = None, fps: int = 60, **kwargs
    ):
        super().__init__([control], **kwargs)
        self._clock = pygame.time.Clock()
        self._fps = min(max(0, int(fps)), WINDOW_FPS)
        self._delay_ms = 1000 / self._fps if self._fps > 0 else math.inf
        self._spent_ms = 0
        self._nb_frames = 0
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
        self._spent_ms += self._clock.tick()
        if self._spent_ms >= self._delay_ms:
            self._spent_ms = 0
            self._nb_frames += 1
            self.update()

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        control = self.control
        on_frame = self.on_frame
        if on_frame:
            on_frame(control, self._nb_frames)
        return control.render(window, width, height)
