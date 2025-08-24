from typing import Any, Self

from videre.core.constants import Alignment
from videre.core.events import MouseEvent
from videre.core.pygame_utils import Surface
from videre.core.sides.border import Border
from videre.layouts.column import Column
from videre.layouts.container import Container
from videre.layouts.div import Div, Style, StyleDef
from videre.layouts.row import Row
from videre.widgets.text import Text


class _Text(Text):
    __slots__ = ()
    __wprops__ = {}

    def __init__(self, data=""):
        super().__init__(str(data), height_delta=0)


class _PlainColumn(Column):
    __slots__ = ()
    __wprops__ = {}
    __capture_mouse__ = True


class _OptionWidget(Div):
    __slots__ = ("_dropdown", "_index")
    __wprops__ = {}

    def __init__(self, dropdown: "Dropdown", index: int, width: int):
        self._dropdown = dropdown
        self._index = index
        super().__init__(
            _Text(dropdown.options[index]),
            style=StyleDef(
                default=Style(
                    width=width, border=Border(), horizontal_alignment=Alignment.START
                )
            ),
        )
        self._on_click = self._select

    def _select(self, *args, **kwargs):
        self._dropdown.index = self._index


class Dropdown(Div):
    __slots__ = ("_context", "_text", "_arrow")
    __wprops__ = {"options", "index", "name"}
    ARROW_DOWN = "▼"

    def __init__(self, options=(), **kwargs):
        self._text = _Text()
        self._arrow = _Text(self.ARROW_DOWN)
        self._context: Column | None = None
        super().__init__(Row([Container(self._text, weight=1), self._arrow]), **kwargs)
        self.options = options
        self.index = 0

        if self.options:
            self._text.text = str(self.selected)

    @property
    def options(self) -> tuple:
        return self._get_wprop("options")

    @options.setter
    def options(self, options: list | tuple):
        options = tuple(options)
        assert options
        self._set_wprop("options", options)
        self.index = 0

    @property
    def index(self) -> int:
        return self._get_wprop("index")

    @index.setter
    def index(self, index: int):
        self._set_wprop("index", min(max(0, index), len(self.options) - 1))
        self._text.text = str(self.selected)
        self._close_context()

    @property
    def selected(self) -> Any:
        return self.options[self.index]

    def handle_mouse_down(self, event: MouseEvent):
        if event.button_left:
            super().handle_mouse_down(event)
            if self._context:
                self._close_context()
            else:
                self._open_context()

    def handle_focus_in(self) -> Self:
        return self

    def handle_focus_out(self):
        self._close_context()

    def _open_context(self):
        window = self.get_window()
        width = self._compute_width(window, include_border=False)
        self._context = _PlainColumn(
            [_OptionWidget(self, i, width) for i, option in enumerate(self.options)]
        )
        window.set_context(self, self._context, y=-1)

    def _close_context(self):
        if self._context:
            self.get_window().clear_context()
            self._context = None

    def _compute_width(self, window, include_border=True) -> int:
        text_width = (
            max(
                (
                    _Text(str(option)).render(window, None, None).get_width()
                    for option in self.options
                ),
                default=0,
            )
            + self._arrow.render(window, None, None).get_width()
        )

        container = self._container()
        margin = container.padding
        if include_border:
            margin = margin + container.border.margin()
        return margin.left + text_width + margin.right

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        self._container().width = self._compute_width(window)
        return super().draw(window, width, None)
