from typing import cast

from videre.core.constants import Side


class AbstractSides[T, S]:
    __slots__ = ("top", "right", "bottom", "left")
    __default__: S | None = None

    def __init__(
        self,
        top: T | None = None,
        left: T | None = None,
        bottom: T | None = None,
        right: T | None = None,
    ):
        self.top: S = self._parse(top)
        self.left: S = self._parse(left)
        self.bottom: S = self._parse(bottom)
        self.right: S = self._parse(right)

    def _parse(self, value: T | None) -> S:
        if value is None:
            return cast(S, self.__default__)
        return self.__parser__(value)

    def __parser__(self, side: T) -> S:
        return cast(S, side)

    def __repr__(self):
        sides = []
        for side in Side:
            value = getattr(self, side.value)
            if value is not None:
                sides.append(f"{side.value}={value}")
        return f"{type(self).__name__}({', '.join(sides)})"

    def __hash__(self):
        return hash((self.top, self.right, self.bottom, self.left))

    def __eq__(self, other):
        return type(self) is type(other) and (
            self.top == other.top
            and self.right == other.right
            and self.bottom == other.bottom
            and self.left == other.left
        )

    @classmethod
    def axis(cls, vertical: T | None = None, horizontal: T | None = None):
        return cls(top=vertical, bottom=vertical, left=horizontal, right=horizontal)

    @classmethod
    def sides(cls, value: T, *axes: Side):
        return cls(**{axis.value: value for axis in set(axes)})
