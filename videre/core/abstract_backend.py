from abc import ABC, abstractmethod
from typing import TypeAlias

from videre.colors import Color
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import Rendering

_Position: TypeAlias = tuple[int | float, int | float]


class AbstractBackend(ABC):
    @abstractmethod
    def new_surface(self, width: int | float, height: int | float) -> Rendering: ...

    @abstractmethod
    def fill(
        self, surface: Rendering, color: Color, rectangle: Rectangle | None = None
    ) -> None: ...

    @abstractmethod
    def line(
        self, surface: Rendering, color: Color, start: _Position, end: _Position
    ) -> None: ...
