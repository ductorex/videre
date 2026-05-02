from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique, auto
from typing import Iterator, Sequence, Self, TypeAlias

from PIL.Image import Image


@unique
class MouseButton(Enum):
    BUTTON_LEFT = auto()
    BUTTON_MIDDLE = auto()
    BUTTON_RIGHT = auto()
    BUTTON_WHEELDOWN = auto()
    BUTTON_WHEELUP = auto()
    BUTTON_X1 = auto()  # what is button x1 ?
    BUTTON_X2 = auto()  # what is button x2 ?


@unique
class KeyMod(Enum):
    LSHIFT = auto()
    RSHIFT = auto()
    LCTRL = auto()
    RCTRL = auto()
    RALT = auto()
    LALT = auto()
    CAPS = auto()


@unique
class Key(Enum):
    BACKSPACE = auto()
    TAB = auto()
    RETURN = auto()
    ESCAPE = auto()
    DELETE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    HOME = auto()
    END = auto()
    PAGEUP = auto()
    PAGEDOWN = auto()
    PRINTSCREEN = auto()
    SPACE = auto()
    a = auto()
    c = auto()
    v = auto()


@dataclass(slots=True, frozen=True)
class KeyboardEntry:
    modifiers: frozenset[KeyMod] = field(default_factory=frozenset)
    key: Key | None = None
    unicode: str | None = None

    lshift = property(lambda self: KeyMod.LSHIFT in self.modifiers)
    rshift = property(lambda self: KeyMod.RSHIFT in self.modifiers)
    lctrl = property(lambda self: KeyMod.LCTRL in self.modifiers)
    rctrl = property(lambda self: KeyMod.RCTRL in self.modifiers)
    ralt = property(lambda self: KeyMod.RALT in self.modifiers)
    lalt = property(lambda self: KeyMod.LALT in self.modifiers)

    backspace = property(lambda self: self.key == Key.BACKSPACE)
    tab = property(lambda self: self.key == Key.TAB)
    enter = property(lambda self: self.key == Key.RETURN)
    escape = property(lambda self: self.key == Key.ESCAPE)
    delete = property(lambda self: self.key == Key.DELETE)
    up = property(lambda self: self.key == Key.UP)
    down = property(lambda self: self.key == Key.DOWN)
    left = property(lambda self: self.key == Key.LEFT)
    right = property(lambda self: self.key == Key.RIGHT)
    home = property(lambda self: self.key == Key.HOME)
    end = property(lambda self: self.key == Key.END)
    pageup = property(lambda self: self.key == Key.PAGEUP)
    pagedown = property(lambda self: self.key == Key.PAGEDOWN)
    printscreen = property(lambda self: self.key == Key.PRINTSCREEN)

    a = property(lambda self: self.key == Key.a)
    c = property(lambda self: self.key == Key.c)
    v = property(lambda self: self.key == Key.v)

    @property
    def caps(self) -> int:
        return KeyMod.CAPS in self.modifiers

    @property
    def ctrl(self) -> int:
        return KeyMod.LCTRL in self.modifiers or KeyMod.RCTRL in self.modifiers

    @property
    def alt(self) -> int:
        return KeyMod.RALT in self.modifiers or KeyMod.LALT in self.modifiers

    @property
    def shift(self) -> int:
        return KeyMod.LSHIFT in self.modifiers or KeyMod.RSHIFT in self.modifiers

    def __repr__(self):
        return " + ".join(
            key for key in ("caps", "ctrl", "alt", "shift") if getattr(self, key)
        )


@dataclass(slots=True, frozen=True)
class Color:
    r: int
    g: int
    b: int
    a: int = 255  # 0: transparent, 255: opaque


@dataclass(slots=True, frozen=True)
class Position:
    x: int | float
    y: int | float


@dataclass(slots=True, frozen=True)
class Rectangle:
    x: int | float
    y: int | float
    width: int | float
    height: int | float


@dataclass(slots=True, frozen=True)
class DrawerFont:
    path: str
    strong: bool = False
    italic: bool = False


###########################
# Drawer specific classes #
###########################


@dataclass(slots=True, frozen=True)
class FillArgs:
    color: Color


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
class TextArgs:
    font: DrawerFont
    destination: Position
    text: str
    size: int | None
    fgcolor: Color | None


@dataclass(slots=True, frozen=True)
class SmoothScaleArgs:
    drawer: Drawer  # scale to the parent drawer dimensions


@dataclass(slots=True, frozen=True)
class ImageArgs:
    image: Image  # expected to have same dimensions as parent drawer


Args: TypeAlias = (
    FillArgs
    | BlitArgs
    | LineArgs
    | RectangleArgs
    | BoxArgs
    | FilledPolygonArgs
    | TextArgs
    | SmoothScaleArgs
    | ImageArgs
)


class Drawer:
    """
    Drawer offers a per-widget API (each widget builds its own Drawer in local coordinates)
    and is rendered by an external visitor. The visitor either flattens the tree of nested
    drawers into a single sequence of primitives, executed directly on the screen,
    or goes through drawers recursively.
    — if possible, no intermediate surface is allocated.
    """

    __slots__ = ("_width", "_height", "_commands")

    def __init__(self, width: int | float, height: int | float):
        self._width = width
        self._height = height
        self._commands: list[Args] = []

    def _cmd(self, args: Args) -> None:
        self._commands.append(args)

    def __iter__(self) -> Iterator[Args]:
        return iter(self._commands)

    def get_width(self) -> int | float:
        return self._width

    def get_height(self) -> int | float:
        return self._height

    def fill(self, color: Color) -> None:
        self._cmd(FillArgs(color))

    def blit(self, drawer: Self, position: Position) -> None:
        self._cmd(BlitArgs(drawer, position))

    def line(self, color: Color, start: Position, end: Position) -> None:
        self._cmd(LineArgs(color, start, end))

    def rectangle(self, rectangle: Rectangle, color: Color) -> None:
        self._cmd(RectangleArgs(rectangle, color))

    def box(self, rectangle: Rectangle, color: Color) -> None:
        self._cmd(BoxArgs(rectangle, color))

    def filled_polygon(self, points: Sequence[Position], color: Color) -> None:
        self._cmd(FilledPolygonArgs(tuple(points), color))

    def text(
        self,
        font: DrawerFont,
        destination: Position,
        text: str,
        size: int | None = None,
        fgcolor: Color | None = None,
    ) -> None:
        """Draw `text` at `destination`.

        NB: `destination` is expressed in surface coordinates (top-left
        origin), but it does **not** point to the top-left of the painted
        text. It is the **text origin**: `x` is the pen position before the
        first glyph (the leftmost painted pixel sits at `x + CharMetrics.x`
        of that glyph), `y` is the baseline (glyphs with descenders extend
        below `y`, ascenders extend above).
        """
        self._cmd(TextArgs(font, destination, text, size, fgcolor))

    @classmethod
    def smoothscale(cls, drawer: Self, width: int, height: int) -> "Drawer":
        """Class method, since this command should produce a new surface."""
        out = Drawer(width, height)
        out._cmd(SmoothScaleArgs(drawer))
        return out

    @classmethod
    def image(cls, image: Image) -> "Drawer":
        """Class method, since this command should produce a new surface."""
        width, height = image.size
        out = Drawer(width, height)
        out._cmd(ImageArgs(image))
        return out
