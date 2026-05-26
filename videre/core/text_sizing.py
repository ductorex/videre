from __future__ import annotations

from dataclasses import dataclass

from videre.colors import Color
from videre.core.constants import TextAlign
from videre.core.rendering_result import TextRenderingResult


@dataclass(slots=True, frozen=True)
class CharArgs:
    char: str
    size: int
    strong: bool
    italic: bool
    underline: bool
    color: Color

    def __post_init__(self) -> None:
        assert len(self.char) == 1


@dataclass(slots=True, frozen=True)
class TextProps:
    text: str
    size: int
    strong: bool
    italic: bool
    underline: bool
    height_delta: int
    color: Color
    width: int | None
    wrap_words: bool
    align: TextAlign


def get_char_sizing(char_args: CharArgs) -> tuple[int, int]:
    # todo will use backend-independent text measures code (e.g. new shaped text rendering?) to get width/height
    raise NotImplementedError()


def get_text_sizing(text_args: TextProps) -> TextRenderingResult:
    # todo will use backend-independent text measures code (e.g. new shaped text rendering?) to get text navigation
    raise NotImplementedError()
