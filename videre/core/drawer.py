from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence, TypeAlias

from PIL.Image import Image

from videre.colors import Color
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


@dataclass(slots=True, frozen=True)
class RectangleArgs:
    rectangle: Rectangle
    color: Color


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
    """
    Drawer offers a per-widget API (each widget builds its own Drawer in local coordinates)
    and is rendered by an external visitor. The visitor either flattens the tree of nested
    drawers into a single sequence of primitives, executed directly on the screen,
    or goes through drawers recursively.
    — if possible, no intermediate surface is allocated.
    """

    __slots__ = ("_width", "_height", "_commands", "_hash")

    def __init__(self, width: int | float = 0, height: int | float = 0):
        self._width = int(width)
        self._height = int(height)
        self._commands: list[Args] = []
        self._hash: int | None = None

    def __hash__(self) -> int:
        # Memoized: `__hash__` walks the whole command tree (sub-drawers
        # recurse), so the render cache that keys on it would be O(tree) per
        # lookup otherwise. A Drawer is built once then frozen (used as a cache
        # key); `_cmd` resets this. Mutating a Drawer after it has been hashed
        # and cached is unsupported.
        if self._hash is None:
            self._hash = hash((self._width, self._height, tuple(self._commands)))
        return self._hash

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Drawer)
            and self._width == other._width
            and self._height == other._height
            and self._commands == other._commands
        )

    def __iter__(self) -> Iterator[Args]:
        return iter(self._commands)

    def _cmd(self, args: Args) -> None:
        self._commands.append(args)
        self._hash = None

    def get_width(self) -> int:
        return self._width

    def get_height(self) -> int:
        return self._height

    def fill(self, color: Color, rectangle: Rectangle | None = None) -> None:
        self._cmd(FillArgs(color, rectangle))

    def blit(self, drawer: Drawer, position: Position) -> None:
        self._cmd(BlitArgs(drawer, position))

    def line(self, color: Color, start: Position, end: Position) -> None:
        self._cmd(LineArgs(color, start, end))

    def rectangle(self, rectangle: Rectangle, color: Color) -> None:
        self._cmd(RectangleArgs(rectangle, color))

    def box(self, rectangle: Rectangle, color: Color) -> None:
        self._cmd(BoxArgs(rectangle, color))

    def filled_polygon(self, points: Sequence[Position], color: Color) -> None:
        self._cmd(FilledPolygonArgs(tuple(points), color))

    def copy(self) -> Drawer:
        out = Drawer(self._width, self._height)
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


_GENERATIVE = (ImageArgs, ImageFromBytesArgs, SmoothScaleArgs, CopyArgs)


def _overlaps(left: int, top: int, width: int, height: int, rect: Rectangle) -> bool:
    """Half-open AABB overlap of ``[left, left+width) x [top, top+height)`` with
    `rect`. Strict: a box merely touching `rect`'s edge shares no pixel and is
    dropped. Callers pass a 1-pixel extent for inclusive-endpoint shapes (lines,
    polygons) so those are not wrongly dropped at the boundary."""
    return (
        left < rect.left + rect.width
        and left + width > rect.left
        and top < rect.top + rect.height
        and top + height > rect.top
    )


def _is_generative(drawer: Drawer) -> bool:
    """A drawer whose pixels come from a base surface (image / scaled / copied):
    it cannot be pruned to a sub-region by dropping commands."""
    return any(isinstance(cmd, _GENERATIVE) for cmd in drawer)


def crop_drawer(drawer: Drawer, rect: Rectangle) -> Drawer:
    """Return a new ``Drawer(rect.width, rect.height)`` showing only the part of
    `drawer` inside `rect` (in `drawer`'s local coords), with `rect`'s top-left
    mapped to ``(0, 0)``.

    The point is to avoid rasterizing what a ScrollView never shows: a tall
    content drawer (e.g. a 90-row column) becomes a viewport-sized drawer holding
    only the handful of children that intersect the view, so ``materialize``
    allocates a small surface and composes a few children instead of a giant one.

    Rules: a command fully outside `rect` is dropped; otherwise it is kept,
    translated by ``(-rect.left, -rect.top)`` — anything still overflowing the
    cropped drawer is clipped by the renderer (surface bounds), so nothing needs
    trimming. A kept child keeps its **identity** (same ``Drawer`` object) so it
    still hits the ``materialize`` cache. A straddling child *larger than `rect`*
    would re-introduce an oversized surface if kept whole, so it is recursively
    cropped instead — unless it is generative (image/scale/copy), which cannot be
    pruned and is kept whole. A generative `drawer` itself can't be pruned at
    all: it is re-anchored whole at the negative offset (same as a plain offset
    blit — correct, cache-friendly, just not size-reduced)."""
    out = Drawer(rect.width, rect.height)
    if _is_generative(drawer):
        out.blit(drawer, Position(int(-rect.left), int(-rect.top)))
        return out
    dx, dy = int(-rect.left), int(-rect.top)
    rl, rt, rw, rh = rect.left, rect.top, rect.width, rect.height
    for cmd in drawer:
        match cmd:
            case FillArgs(color=color, rectangle=None):
                out.fill(color)
            case FillArgs(color=color, rectangle=r):
                if _overlaps(r.left, r.top, r.width, r.height, rect):
                    out.fill(
                        color, Rectangle(r.left + dx, r.top + dy, r.width, r.height)
                    )
            case BlitArgs(drawer=child, position=pos):
                cw, ch = child.get_width(), child.get_height()
                if not _overlaps(pos.x, pos.y, cw, ch, rect):
                    continue
                inside = (
                    pos.x >= rl
                    and pos.y >= rt
                    and pos.x + cw <= rl + rw
                    and pos.y + ch <= rt + rh
                )
                if not inside and (cw > rw or ch > rh) and not _is_generative(child):
                    ix0, iy0 = max(pos.x, rl), max(pos.y, rt)
                    ix1, iy1 = min(pos.x + cw, rl + rw), min(pos.y + ch, rt + rh)
                    child_rect = Rectangle(
                        ix0 - pos.x, iy0 - pos.y, ix1 - ix0, iy1 - iy0
                    )
                    out.blit(
                        crop_drawer(child, child_rect),
                        Position(int(ix0 + dx), int(iy0 + dy)),
                    )
                else:
                    out.blit(child, Position(int(pos.x + dx), int(pos.y + dy)))
            case LineArgs(color=color, start=s, end=e):
                bx, by = min(s.x, e.x), min(s.y, e.y)
                if _overlaps(bx, by, abs(e.x - s.x) + 1, abs(e.y - s.y) + 1, rect):
                    out.line(
                        color,
                        Position(s.x + dx, s.y + dy),
                        Position(e.x + dx, e.y + dy),
                    )
            case RectangleArgs(rectangle=r, color=color):
                if _overlaps(r.left, r.top, r.width, r.height, rect):
                    out.rectangle(
                        Rectangle(r.left + dx, r.top + dy, r.width, r.height), color
                    )
            case BoxArgs(rectangle=r, color=color):
                if _overlaps(r.left, r.top, r.width, r.height, rect):
                    out.box(
                        Rectangle(r.left + dx, r.top + dy, r.width, r.height), color
                    )
            case FilledPolygonArgs(points=pts, color=color):
                xs = [p.x for p in pts]
                ys = [p.y for p in pts]
                if pts and _overlaps(
                    min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, rect
                ):
                    out.filled_polygon(
                        [Position(p.x + dx, p.y + dy) for p in pts], color
                    )
            case _:
                raise NotImplementedError(type(cmd).__name__, cmd)
    return out


class Drawing:
    """Helper class for drawing using functions (class methods) instead of (object) methods."""

    @classmethod
    def new_surface(cls, width: int, height: int) -> Drawer:
        return Drawer(width, height)

    @classmethod
    def fill(
        cls, self: Drawer, color: Color, rectangle: Rectangle | None = None
    ) -> None:
        self.fill(color, rectangle)

    @classmethod
    def blit(cls, self: Drawer, drawer: Drawer, position: PositionTuple) -> None:
        self.blit(drawer, Position(*position))

    @classmethod
    def line(
        cls, self: Drawer, color: Color, start: PositionTuple, end: PositionTuple
    ) -> None:
        self.line(color, Position(*start), Position(*end))

    @classmethod
    def rectangle(cls, self: Drawer, rectangle: Rectangle, color: Color) -> None:
        self.rectangle(rectangle, color)

    @classmethod
    def box(cls, self: Drawer, rectangle: Rectangle, color: Color) -> None:
        self.box(rectangle, color)

    @classmethod
    def filled_polygon(
        cls, self: Drawer, points: Sequence[PositionTuple], color: Color
    ) -> None:
        self.filled_polygon([Position(*point) for point in points], color)

    @classmethod
    def copy(cls, self: Drawer) -> Drawer:
        return self.copy()

    @classmethod
    def smoothscale(cls, drawer: Drawer, width: int, height: int) -> Drawer:
        return Drawer.smoothscale(drawer, width, height)

    @classmethod
    def image(cls, image: Image) -> Drawer:
        return Drawer.image(image)

    @classmethod
    def image_from_bytes(cls, data: bytes, dimensions: PositionTuple) -> Drawer:
        return Drawer.image_from_bytes(data, *dimensions)
