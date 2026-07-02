from videre.colors import Color, ColorDef, parse_color, stringify_color
from videre.core.dpi import to_device
from videre.core.sides.abstract_sides import AbstractSides
from videre.core.sides.margin import Margin


class BorderSide:
    __slots__ = ("width", "color")

    def __init__(self, width: int, color: ColorDef | None = None):
        self.width = width
        self.color = parse_color(color or "black")

    def __repr__(self):
        return f"{self.width}:{stringify_color(self.color)}"

    def __hash__(self):
        return hash(
            (self.width, self.color.r, self.color.g, self.color.b, self.color.a)
        )

    def __eq__(self, other):
        return (
            type(self) is type(other)
            and self.width == other.width
            and self.color == other.color
        )


BorderType = BorderSide | tuple[int, ColorDef] | int


class _DimensionsLimit:
    __slots__ = ("_w", "_h")

    def __init__(self, width: int, height: int):
        self._w = width
        self._h = height

    def __call__(self, x: int, y: int) -> tuple[int, int]:
        return min(max(x, 0), self._w - 1), min(max(y, 0), self._h - 1)


class Border(AbstractSides[BorderType, BorderSide]):
    """
    0,0                      w-1,0
          l-1,t-1    w-r,t-1
          l-1,h-b    w-r,h-b
    0,h-1                    w-1,h-1
    """

    __slots__ = ()
    __default__ = BorderSide(0)

    def __parser__(self, side: BorderType) -> BorderSide:
        if isinstance(side, BorderSide):
            return side
        elif isinstance(side, tuple):
            assert isinstance(side, tuple)
            width, color = side
            return BorderSide(width, color)
        elif isinstance(side, int):
            return BorderSide(side)
        else:
            raise ValueError(f"Unsupported border side value: {side!r}")

    @classmethod
    def all(cls, width: int, color: ColorDef | None = None):
        side = BorderSide(width, color)
        return cls(side, side, side, side)

    def __bool__(self) -> bool:
        """True if any side has a visible (non-zero) width."""
        return bool(
            self.top.width or self.right.width or self.bottom.width or self.left.width
        )

    def margin(self):
        return Margin(
            top=self.top.width,
            right=self.right.width,
            bottom=self.bottom.width,
            left=self.left.width,
        )

    def scaled(self, factor: float) -> "Border":
        """This border with each side width in device pixels (half-up; a 0
        side stays 0)."""
        if factor == 1.0:
            return self
        return Border(
            top=BorderSide(to_device(self.top.width, factor), self.top.color),
            right=BorderSide(to_device(self.right.width, factor), self.right.color),
            bottom=BorderSide(to_device(self.bottom.width, factor), self.bottom.color),
            left=BorderSide(to_device(self.left.width, factor), self.left.color),
        )

    def get_top_points(self, width: int, height: int) -> list[tuple[int, int]]:
        if not width or not height or not self.top.width:
            return []
        limit = _DimensionsLimit(width, height)
        return [
            (0, 0),
            (width - 1, 0),
            limit(width - self.right.width, self.top.width - 1),
            limit(self.left.width - 1, self.top.width - 1),
        ]

    def get_right_points(self, width: int, height: int) -> list[tuple[int, int]]:
        if not width or not height or not self.right.width:
            return []
        limit = _DimensionsLimit(width, height)
        return [
            (width - 1, 0),
            (width - 1, height - 1),
            limit(width - self.right.width, height - self.bottom.width),
            limit(width - self.right.width, self.top.width - 1),
        ]

    def get_bottom_points(self, width: int, height: int) -> list[tuple[int, int]]:
        if not width or not height or not self.bottom.width:
            return []
        limit = _DimensionsLimit(width, height)
        return [
            (0, height - 1),
            (width - 1, height - 1),
            limit(width - self.right.width, height - self.bottom.width),
            limit(self.left.width - 1, height - self.bottom.width),
        ]

    def get_left_points(self, width: int, height: int) -> list[tuple[int, int]]:
        if not width or not height or not self.left.width:
            return []
        limit = _DimensionsLimit(width, height)
        return [
            (0, 0),
            (0, height - 1),
            limit(self.left.width - 1, height - self.bottom.width),
            limit(self.left.width - 1, self.top.width - 1),
        ]

    def describe_borders(
        self, width: int, height: int
    ) -> list[tuple[Color, list[tuple[int, int]]]]:
        return [
            (self.top.color, self.get_top_points(width, height)),
            (self.right.color, self.get_right_points(width, height)),
            (self.bottom.color, self.get_bottom_points(width, height)),
            (self.left.color, self.get_left_points(width, height)),
        ]
