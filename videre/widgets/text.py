from typing import TYPE_CHECKING, Any

from videre.colors import Color, ColorDef, parse_color
from videre.core.constants import TextAlign, TextWrap
from videre.core.drawer import Drawer
from videre.core.rendering_result import AbstractTextDocument, TextRenderingResult
from videre.widgets.widget import Widget

if TYPE_CHECKING:
    from videre.windowing.window import Window


class Text(Widget):
    """A run of text, optionally wrapped and aligned.

    `wrap` (`TextWrap`) selects char / word wrapping (None = no wrap); `align`
    (`TextAlign`) sets horizontal alignment within the available width. How
    whitespace gaps are kept or collapsed follows `TextSpacePolicy` (whose
    `AUTO` default derives from `wrap`); see that enum and
    `text_partition.wrap` for the details.
    """

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
    __slots__ = ("_rendered", "_document", "_document_scale")

    # Properties that change the shape itself (not just the layout): changing one
    # invalidates the cached `TextDocument`. Width / wrap / align only re-lay
    # out, so they keep the document — that is the resize win.
    __document_props__ = {"text", "size", "strong", "italic", "height_delta"}

    def __init__(
        self,
        text="",
        size=0,
        height_delta=2,
        wrap: TextWrap | None = None,
        align: TextAlign | None = None,
        color: ColorDef | None = None,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        selection: tuple[int, int] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._rendered: TextRenderingResult | None = None
        self._document: AbstractTextDocument | None = None
        self._document_scale: float | None = None
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
            # `_rendered` is NOT nulled here: `draw()` (run on any `has_changed()`)
            # replaces it, so it always holds the last painted frame. Nulling it
            # would leave it None between a mutation and the next draw — which
            # `TextInput` would read as a missing render (assert) rather than the
            # caret still on screen.
            if name in self.__document_props__:
                self._document = None

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
    def wrap(self) -> TextWrap | None:
        return self._get_wprop("wrap")

    @wrap.setter
    def wrap(self, wrap: TextWrap | None):
        self._set_wprop("wrap", wrap)

    @property
    def align(self) -> TextAlign | None:
        return self._get_wprop("align")

    @align.setter
    def align(self, align: TextAlign | None):
        self._set_wprop("align", align)

    @property
    def color(self) -> Color | None:
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

    def _text_rendering(self, window: "Window"):
        return window.text_rendering(
            size=self.size,
            strong=self.strong,
            italic=self.italic,
            height_delta=self.height_delta,
        )

    def get_document(self, window: "Window") -> AbstractTextDocument:
        """Cache the shaped document (text-only shape) across frames; a resize
        keeps it and only `render(width)` is replayed.

        The document bakes the display scale in (glyphs are rasterized at
        device size), so it also follows `window.scale_factor`: a widget
        re-rendered at another scale re-shapes instead of keeping the first
        window's glyph density."""
        if self._document is None or self._document_scale != window.scale_factor:
            self._document = self._text_rendering(window).document(self.text)
            self._document_scale = window.scale_factor
        return self._document

    def draw(
        self, window: "Window", width: int | None = None, height: int | None = None
    ) -> Drawer:
        wrap = self.wrap
        text_ret, surface_ret = self.get_document(window).render(
            width=(None if wrap is None else width),
            color=self.color,
            wrap_words=(wrap == TextWrap.WORD),
            align=(None if wrap is None else self.align),
            underline=self.underline,
            selection=self.selection,
        )
        self._rendered = text_ret
        return surface_ret
