from typing import TYPE_CHECKING

from videre.colors import Color, ColorDef, parse_color
from videre.core.drawer import Drawer
from videre.widgets.widget import Widget

if TYPE_CHECKING:
    from videre.windowing.window import Window


class Character(Widget):
    __wprops__ = {"text", "size", "color", "strong", "italic", "underline"}
    __slots__ = ()

    def __init__(
        self,
        text="",
        size=None,
        color: ColorDef | None = None,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.size = size
        self.text = text
        self.color = color
        self.strong = strong
        self.italic = italic
        self.underline = underline

    @property
    def text(self) -> str:
        return self._get_wprop("text")

    @text.setter
    def text(self, text: str):
        assert len(text) == 1, "Character must be a single character"
        self._set_wprop("text", text)

    @property
    def size(self) -> int | None:
        return self._get_wprop("size")

    @size.setter
    def size(self, size: int | None):
        self._set_wprop("size", size)

    @property
    def color(self) -> Color:
        return self._get_wprop("color")

    @color.setter
    def color(self, color: ColorDef | None):
        self._set_wprop("color", None if color is None else parse_color(color))

    @property
    def strong(self) -> bool:
        return self._get_wprop("strong")

    @strong.setter
    def strong(self, strong: bool):
        self._set_wprop("strong", bool(strong))

    @property
    def italic(self) -> bool:
        return self._get_wprop("italic")

    @italic.setter
    def italic(self, italic: bool):
        self._set_wprop("italic", bool(italic))

    @property
    def underline(self) -> bool:
        return self._get_wprop("underline")

    @underline.setter
    def underline(self, underline: bool):
        self._set_wprop("underline", bool(underline))

    def _text_rendering(self, window: "Window"):
        size = self.size
        if size is None:
            size = window.symbol_size

        rendering = window.text_rendering(
            size=size, strong=self.strong, italic=self.italic
        )
        return rendering

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        return self._text_rendering(window).render_char(self.text, color=self.color)
