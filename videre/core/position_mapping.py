from typing import Any


class Position:
    __slots__ = ("_x", "_y")

    def __init__(self, x=0, y=0):
        self._x, self._y = x, y

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y


DEFAULT_POSITION = Position()


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
