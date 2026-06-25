from typing import Any

from videre.core.drawer import Position

DEFAULT_POSITION = Position(0, 0)


class PositionMapping:
    __slots__ = ["_el_to_pos"]

    def __init__(self):
        self._el_to_pos: dict[Any, Position] = {}

    def set(self, element, x: int, y: int):
        self._el_to_pos[element] = Position(x, y)

    def update_x(self, element, x: int):
        self.set(element, x, self.get(element).y)

    def update_y(self, element, y: int):
        self.set(element, self.get(element).x, y)

    def get(self, element) -> Position:
        return self._el_to_pos.get(element, DEFAULT_POSITION)

    def remove(self, element):
        self._el_to_pos.pop(element, None)
