from typing import Callable, TypeAlias

from videre.colors import Colors
from videre.core.constants import Alignment, MouseButton
from videre.core.events import MouseEvent
from videre.core.sides.border import Border
from videre.core.sides.padding import Padding
from videre.layouts.container import Container
from videre.layouts.control_layout import ControlLayout
from videre.layouts.divutils.styling import Style, StyleDef, StyleType
from videre.widgets.widget import Widget

OnClickType: TypeAlias = Callable[[Widget], None]


class Div(ControlLayout):
    __slots__ = ("_hover", "_down", "_style", "_on_click")
    __wprops__ = {}
    __capture_mouse__ = True
    __style__: StyleDef = StyleDef(
        default=Style(
            padding=Padding.axis(horizontal=6, vertical=4),
            border=Border.all(1),
            vertical_alignment=Alignment.CENTER,
            horizontal_alignment=Alignment.CENTER,
        ),
        hover=Style(background_color=Colors.lightgray),
        click=Style(background_color=Colors.gray),
    )

    def __init__(
        self,
        control: Widget | None = None,
        style: StyleType | None = None,
        on_click: OnClickType | None = None,
        **kwargs,
    ):
        self._style = self.__style__.merged_with(style)
        super().__init__(Container(control), **kwargs)
        self._hover = False
        self._down = False
        self._on_click = on_click
        self._set_style()

    def _container(self) -> Container:
        (container,) = self._controls()
        return container

    def handle_mouse_enter(self, event: MouseEvent):
        self._hover = True
        self._set_style()

    def handle_mouse_exit(self):
        self._hover = False
        self._set_style()

    def handle_mouse_down(self, event: MouseEvent):
        self._down = True
        self._set_style()

    def handle_mouse_up(self, event: MouseEvent):
        return self.handle_mouse_down_canceled(event.button)

    def handle_mouse_down_canceled(self, button: MouseButton):
        self._down = False
        self._set_style()

    def handle_click(self, button: MouseButton):
        if button == MouseButton.BUTTON_LEFT:
            self.click()

    def click(self):
        if self._on_click is not None:
            self.get_window().call_now(self._on_click, self)

    def _get_style(self) -> Style:
        if self._down:
            style = self._style.click
        elif self._hover:
            style = self._style.hover
        else:
            style = self._style.default
        return style

    def _set_style(self):
        (container,) = self._controls()
        for key, value in self._get_style().container_styles().items():
            setattr(container, key, value)
