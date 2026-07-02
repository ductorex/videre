from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence, TypeAlias

from PIL.Image import Image

from videre.colors import Color
from videre.core.dpi import DevicePx, LogicalPx, to_device_ceil
from videre.core.rectangle import Rectangle

PositionTuple: TypeAlias = tuple[int, int]


@dataclass(slots=True, frozen=True)
class Position:
    x: int
    y: int


###########################
# Drawer specific classes #
###########################


@dataclass(slots=True, frozen=True)
class FillArgs:
    color: Color
    rectangle: Rectangle | None = None


@dataclass(slots=True, frozen=True)
class BlitArgs:
    drawer: Drawer
    position: Position


@dataclass(slots=True, frozen=True)
class LineArgs:
    color: Color
    start: Position
    end: Position
    width: int = 1


@dataclass(slots=True, frozen=True)
class RectangleArgs:
    rectangle: Rectangle
    color: Color
    width: int = 1


@dataclass(slots=True, frozen=True)
class BoxArgs:
    rectangle: Rectangle
    color: Color


@dataclass(slots=True, frozen=True)
class FilledPolygonArgs:
    points: tuple[Position, ...]
    color: Color


@dataclass(slots=True, frozen=True)
class SmoothScaleArgs:
    drawer: Drawer  # scale to the parent drawer dimensions


@dataclass(slots=True, frozen=True)
class CopyArgs:
    drawer: Drawer  # expected to have same dimensions as parent drawer


@dataclass(slots=True, frozen=True, eq=False)
class ImageArgs:
    image: Image  # expected to have same dimensions as parent drawer

    # PIL Images are unhashable (content `__eq__`, no `__hash__`), so the
    # by-value render cache keys them by identity: the same Image object hits
    # the cache; distinct objects (even with identical pixels) just don't share.
    # The cache holds the Image alive, so the id stays valid while cached.
    def __hash__(self) -> int:
        return id(self.image)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ImageArgs) and self.image is other.image


@dataclass(slots=True, frozen=True)
class ImageFromBytesArgs:
    # Parent drawer is expected to have same width and height
    data: bytes
    width: int | float
    height: int | float


Args: TypeAlias = (
    FillArgs
    | BlitArgs
    | LineArgs
    | RectangleArgs
    | BoxArgs
    | FilledPolygonArgs
    | SmoothScaleArgs
    | CopyArgs
    | ImageArgs
    | ImageFromBytesArgs
)


class Drawer:
    """A recorded list of draw commands in device pixels, plus the logical
    size the rest of the framework sees.

    Layouts read `get_width`/`get_height` (logical); the backend allocates
    `device_width` × `device_height` and replays the commands 1:1, knowing
    nothing about scaling. At scale 1.0 both sizes are equal. The recording
    methods here are the raw device layer: widgets never call them directly
    — they record through `window.drawing`, which converts logical
    coordinates at record time (see videre/core/drawing.py); only code that
    already works in device pixels (the text pipeline) records raw.
    """

    __slots__ = (
        "_width",
        "_height",
        "_device_width",
        "_device_height",
        "_scale",
        "_commands",
        "_hash",
    )

    def __init__(self, width: int | float = 0, height: int | float = 0):
        # Identity construction: logical == device, scale 1.0. Scaled
        # drawers come from `Drawing`; device-built content (text) gets its
        # logical size afterwards via `set_logical_size`.
        self._width = int(width)
        self._height = int(height)
        self._device_width = self._width
        self._device_height = self._height
        self._scale = 1.0
        self._commands: list[Args] = []
        self._hash: int | None = None

    @classmethod
    def at_scale(cls, width: int | float, height: int | float, scale: float) -> Drawer:
        """A logical-size drawer whose device surface is ceil(size × scale).

        Ceil, because the device slot a parent gives a child depends on the
        child's position and can reach ceil — any smaller surface could
        leave a visible gap. The cost: when the slot is smaller than ceil,
        the surface overlaps the next sibling's slot by one pixel, hidden
        by paint order unless that sibling is transparent. The trade-off is
        intrinsic: a drawer is recorded without knowing where it will be
        blitted."""
        out = cls(width, height)
        if scale != 1.0:
            out._device_width = to_device_ceil(out._width, scale)
            out._device_height = to_device_ceil(out._height, scale)
            out._scale = float(scale)
        return out

    def __hash__(self) -> int:
        # Memoized: `__hash__` walks the whole command tree (sub-drawers
        # recurse), so the render cache that keys on it would be O(tree) per
        # lookup otherwise. A Drawer is built once then frozen (used as a cache
        # key); `_cmd` resets this. Mutating a Drawer after it has been hashed
        # and cached is unsupported.
        if self._hash is None:
            self._hash = hash(
                (
                    self._width,
                    self._height,
                    self._device_width,
                    self._device_height,
                    self._scale,
                    tuple(self._commands),
                )
            )
        return self._hash

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Drawer)
            and self._width == other._width
            and self._height == other._height
            and self._device_width == other._device_width
            and self._device_height == other._device_height
            and self._scale == other._scale
            and self._commands == other._commands
        )

    def __iter__(self) -> Iterator[Args]:
        return iter(self._commands)

    def _cmd(self, args: Args) -> None:
        self._commands.append(args)
        self._hash = None

    def get_width(self) -> LogicalPx:
        """Logical width — what layouts measure and stack with."""
        return self._width

    def get_height(self) -> LogicalPx:
        """Logical height — what layouts measure and stack with."""
        return self._height

    @property
    def device_width(self) -> DevicePx:
        """Surface width in device pixels — what the backend allocates."""
        return self._device_width

    @property
    def device_height(self) -> DevicePx:
        """Surface height in device pixels — what the backend allocates."""
        return self._device_height

    @property
    def scale(self) -> float:
        """Device pixels per logical pixel of this drawer's coordinates."""
        return self._scale

    def set_logical_size(
        self, width: LogicalPx, height: LogicalPx, scale: float
    ) -> None:
        """Give a device-built drawer (e.g. rasterized text) the logical
        size layouts should see. Arguments are derived from the device size
        (which never changes), so re-applying is a no-op."""
        width, height, scale = int(width), int(height), float(scale)
        if (self._width, self._height, self._scale) == (width, height, scale):
            return
        self._width = width
        self._height = height
        self._scale = scale
        self._hash = None

    def fill(self, color: Color, rectangle: Rectangle | None = None) -> None:
        self._cmd(FillArgs(color, rectangle))

    def blit(self, drawer: Drawer, position: Position) -> None:
        self._cmd(BlitArgs(drawer, position))

    def line(
        self, color: Color, start: Position, end: Position, width: int = 1
    ) -> None:
        self._cmd(LineArgs(color, start, end, width))

    def rectangle(self, rectangle: Rectangle, color: Color, width: int = 1) -> None:
        self._cmd(RectangleArgs(rectangle, color, width))

    def box(self, rectangle: Rectangle, color: Color) -> None:
        self._cmd(BoxArgs(rectangle, color))

    def filled_polygon(self, points: Sequence[Position], color: Color) -> None:
        self._cmd(FilledPolygonArgs(tuple(points), color))

    def copy(self) -> Drawer:
        out = Drawer(self._width, self._height)
        out._device_width = self._device_width
        out._device_height = self._device_height
        out._scale = self._scale
        out._cmd(CopyArgs(self))
        return out

    @classmethod
    def smoothscale(cls, drawer: Drawer, width: int, height: int) -> Drawer:
        """Class method, since this command should produce a new surface."""
        out = Drawer(width, height)
        out._cmd(SmoothScaleArgs(drawer))
        return out

    @classmethod
    def image(cls, image: Image) -> Drawer:
        """Class method, since this command should produce a new surface."""
        width, height = image.size
        out = Drawer(width, height)
        out._cmd(ImageArgs(image))
        return out

    @classmethod
    def image_from_bytes(
        cls, data: bytes, width: int | float, height: int | float
    ) -> Drawer:
        out = Drawer(width, height)
        out._cmd(ImageFromBytesArgs(data, width, height))
        return out
