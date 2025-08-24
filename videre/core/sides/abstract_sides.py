from videre.core.constants import Side


class AbstractSides[T, S]:
    __slots__ = ("top", "right", "bottom", "left")
    __default__ = None

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
        return self.__default__ if value is None else self.__parser__(value)

    def __parser__(self, value: T) -> S:
        return value

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
            and self.bottom == self.bottom
            and self.left == other.left
        )

    @classmethod
    def axis(cls, vertical: T | None = None, horizontal: T | None = None):
        return cls(top=vertical, bottom=vertical, left=horizontal, right=horizontal)

    @classmethod
    def sides(cls, value: T, *axes: Side):
        return cls(**{axis.value: value for axis in set(axes)})
