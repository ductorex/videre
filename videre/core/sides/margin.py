from videre.core.sides.abstract_sides import AbstractSides


class Margin(AbstractSides[int, int]):
    __slots__ = ()
    __default__ = 0

    def __parser__(self, value: int) -> int:
        if not isinstance(value, int):
            raise TypeError(
                f"Unsupported {type(self).__name__} value type: {type(value).__name__}"
            )
        if value < 0:
            raise ValueError(f"Unsupported {type(self).__name__} value: {value}")
        return value

    @classmethod
    def all(cls, value: int):
        return cls(value, value, value, value)

    def total(self):
        return self.top + self.right + self.bottom + self.left

    def __add__(self, other: "Margin") -> "Margin":
        assert isinstance(other, Margin)
        return Margin(
            top=self.top + other.top,
            right=self.right + other.right,
            bottom=self.bottom + other.bottom,
            left=self.left + other.left,
        )

    def get_inner_width(self, width: int) -> int:
        return max(0, width - self.left - self.right)

    def get_inner_height(self, height: int) -> int:
        return max(0, height - self.top - self.bottom)

    def get_outer_width(self, inner_width: int) -> int:
        return inner_width + self.left + self.right

    def get_outer_height(self, inner_height: int) -> int:
        return inner_height + self.top + self.bottom
