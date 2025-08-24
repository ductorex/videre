import math
from abc import ABC, abstractmethod

import pygame

from videre import WINDOW_FPS
from videre.widgets.widget import Widget


class AbstractFraming(ABC):
    """
    Abstract class to compute rhythm of animation rendering.

    NB: With current implementation of Window class,
    there will always be at least 1 frame rendered
    (the first one, to generate first surfaces)
    before any widget state is checked.
    """

    __slots__ = ()

    @abstractmethod
    def needs_frame(self, nb_window_frames: int) -> bool:
        """
        Abstract method to check if we need a rendering.

        :param nb_window_frames: number of window frames
            rendered until now.
        :return: True if rendering is required for next frame.
        """
        raise NotImplementedError()


class FPS(AbstractFraming):
    """Frames Per Second rhythm."""

    __slots__ = ("_clock", "_fps", "_delay_ms", "_spent_ms")

    def __init__(self, fps: int = 60):
        self._clock = pygame.time.Clock()
        self._fps = min(max(0, int(fps)), WINDOW_FPS)
        self._delay_ms = 1000 / self._fps if self._fps > 0 else math.inf
        self._spent_ms = 0

    def needs_frame(self, nb_window_frames: int) -> bool:
        self._spent_ms += self._clock.tick()
        if self._spent_ms >= self._delay_ms:
            self._spent_ms = 0
            return True
        return False


class FPR(AbstractFraming):
    """
    Frames per rendering rhythm.

    Render 1 animation frame
    for each `nb_frames` window frames.

    Example: if `nb_frames == 4`,
    then for each 4 rendered window frames,
    the 4th rendering will include a new
    animation frame.

    Ass `needs_frame()` may be called many times
    between 2 window frames (when widgets states are checked),
    we must make sure it returns True only once
    between 2 window renderings. To do that,
    we cache given `nb_window_frames`, and
    we check rendering only if a new value
    of `nb_window_frames` is given to the method.
    """

    __slots__ = ("_nb_frames", "_nb_curr_win_frames")

    def __init__(self, nb_frames: int):
        self._nb_frames = max(1, nb_frames)
        self._nb_curr_win_frames = 0

    def needs_frame(self, nb_window_frames: int) -> bool:
        if self._nb_curr_win_frames == nb_window_frames:
            return False
        else:
            self._nb_curr_win_frames = nb_window_frames
            return ((nb_window_frames + 1) % self._nb_frames) == 0


class AbstractAnimation(Widget):
    __wprops__ = {}
    __slots__ = ("_nb_frames", "_framing")

    def __init__(self, framing: AbstractFraming = None, **kwargs):
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
