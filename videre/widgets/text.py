from typing import Any

from videre.colors import ColorDef, parse_color
from videre.core.constants import TextAlign, TextWrap
from videre.core.fontfactory.pygame_text_rendering import RenderedText
from videre.core.pygame_utils import Color, Surface
from videre.widgets.widget import Widget


class Text(Widget):
    __wprops__ = {
        "text",
        "size",
        "height_delta",
        "wrap",
        "align",
        "color",
        "strong",
        "italic",
        "underline",
        "selection",
    }
    __slots__ = ("_rendered",)

    # Properties that do not affect characters layout or size
    # in the rendered, then can be set without re-rendering the text.
    __neutral_props__ = {"color", "underline", "selection"}

    def __init__(
        self,
        text="",
        size=0,
        height_delta=2,
        wrap=TextWrap.NONE,
        align=TextAlign.NONE,
        color: ColorDef = None,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        selection: tuple[int, int] | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._rendered: RenderedText | None = None
        self._set_wprops(size=size, height_delta=height_delta)
        self.text = text
        self.wrap = wrap
        self.align = align
        self.color = color
        self.strong = strong
        self.italic = italic
        self.underline = underline
        self.selection = selection

    def _set_wprop(self, name: str, value: Any):
        if value != self._get_wprop(name):
            super()._set_wprop(name, value)
            if name not in self.__neutral_props__:
                self._rendered = None

    @property
    def text(self) -> str:
        return self._get_wprop("text")

    @text.setter
    def text(self, text: str):
        self._set_wprop("text", text)

    @property
    def size(self) -> int:
        return self._get_wprop("size")

    @property
    def height_delta(self) -> int:
        return self._get_wprop("height_delta")

    @property
    def wrap(self) -> TextWrap:
        return self._get_wprop("wrap")

    @wrap.setter
    def wrap(self, wrap: TextWrap):
        self._set_wprop("wrap", wrap)

    @property
    def align(self) -> TextAlign:
        return self._get_wprop("align")

    @align.setter
    def align(self, align: TextAlign):
        self._set_wprop("align", align)

    @property
    def color(self) -> Color | None:
        return self._get_wprop("color")

    @color.setter
    def color(self, color: ColorDef):
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

    @property
    def selection(self) -> tuple[int, int] | None:
        return self._get_wprop("selection")

    @selection.setter
    def selection(self, selection: tuple[int, int] | None):
        if isinstance(selection, tuple):
            if len(selection) != 2 or not all(isinstance(i, int) for i in selection):
                raise ValueError("Selection must be a tuple of two integers.")
            start, end = selection
            if start > end:
                start, end = end, start
            start = max(0, start)
            end = max(start, end)
            selection = (start, end)
        elif selection is not None:
            raise TypeError("Selection must be a tuple of two integers or None.")
        self._set_wprop("selection", selection)

    def _text_rendering(self, window):
        return window.text_rendering(
            size=self.size,
            strong=self.strong,
            italic=self.italic,
            underline=self.underline,
            height_delta=self.height_delta,
        )

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        wrap = self.wrap
        self._rendered = self._text_rendering(window).render_text(
            text=self.text,
            color=self.color,
            wrap_words=(wrap == TextWrap.WORD),
            width=(None if wrap == TextWrap.NONE else width),
            align=(TextAlign.NONE if wrap == TextWrap.NONE else self.align),
            selection=self.selection,
        )
        return self._rendered.surface
