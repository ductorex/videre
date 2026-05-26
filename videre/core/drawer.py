from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence, TypeAlias

from PIL.Image import Image

from videre.colors import Color
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import TextRenderingResult
from videre.core.text_sizing import (
    CharArgs,
    TextProps,
    get_char_sizing,
    get_text_sizing,
)


@dataclass(slots=True, frozen=True)
class Position:
    x: int | float
    y: int | float


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
class ImageArgs:
    image: Image  # expected to have same dimensions as parent drawer


@dataclass(slots=True, frozen=True)
class TextArgs:
    props: TextProps
    navigation: TextRenderingResult


Args: TypeAlias = (
    FillArgs
    | BlitArgs
    | LineArgs
    | RectangleArgs
    | BoxArgs
    | FilledPolygonArgs
    | SmoothScaleArgs
    | ImageArgs
    | CharArgs
    | TextArgs
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
    def character(cls, char, **kwargs) -> Drawer:
        char_args = CharArgs(char=char, **kwargs)
        width, height = get_char_sizing(char_args)
        out = Drawer(width, height)
        out._cmd(char_args)
        return out

    @classmethod
    def text(cls, text: str, **kwargs) -> Drawer:
        text_props = TextProps(text=text, **kwargs)
        text_nav = get_text_sizing(text_props)
        out = Drawer(text_nav.get_width(), text_nav.get_height())
        out._cmd(TextArgs(props=text_props, navigation=text_nav))
        return out
