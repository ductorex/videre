import dataclasses
from dataclasses import dataclass
from typing import Any, Callable, Self, TypeAlias

from videre import Alignment, Border, Colors
from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.core.pygame_utils import Color
from videre.core.sides.padding import Padding
from videre.gradient import ColoringDefinition
from videre.layouts.container import Container
from videre.layouts.control_layout import ControlLayout
from videre.widgets.widget import Widget


@dataclass(slots=True)
class Style:
    border: Border = None
    padding: Padding = None
    background_color: ColoringDefinition = None
    vertical_alignment: Alignment = None
    horizontal_alignment: Alignment = None
    width: int | None = None
    height: int | None = None
    square: bool | None = None
    color: Color | None = None

    def fill_with(self, other: "Style"):
        for key in (
            "border",
            "padding",
            "background_color",
            "vertical_alignment",
            "horizontal_alignment",
            "width",
            "height",
            "square",
            "color",
        ):
            if getattr(self, key) is None:
                setattr(self, key, getattr(other, key))

    def get_specific_from(self, other: "Style"):
        return Style(
            **{
                key: value
                for key, value in self.to_dict().items()
                if value != getattr(other, key)
            }
        )

    def to_dict(self):
        return dataclasses.asdict(self)

    def container_styles(self) -> dict:
        style = dataclasses.asdict(self)
        del style["color"]
        return style

    def copy(self, **changes) -> Self:
        return dataclasses.replace(self, **changes)


@dataclass(slots=True)
class StyleDef:
    default: Style = dataclasses.field(default_factory=Style)
    hover: Style | None = None
    click: Style | None = None

    def __post_init__(self):
        if self.hover is None:
            self.hover = dataclasses.replace(self.default)
        else:
            self.hover.fill_with(self.default)
        if self.click is None:
            self.click = dataclasses.replace(self.default)
        else:
            self.click.fill_with(self.default)

    def merged_with(self, style: "StyleType | None") -> Self:
        base_style = self
        if style is None:
            return base_style
        else:
            output = {
                "default": dataclasses.replace(base_style.default),
                "hover": base_style.hover.get_specific_from(base_style.default),
                "click": base_style.click.get_specific_from(base_style.default),
            }
            if isinstance(style, StyleDef):
                for key in ("default", "hover", "click"):
                    if getattr(style, key) is not None:
                        output_key = dataclasses.replace(getattr(style, key))
                        output_key.fill_with(output[key])
                        output[key] = output_key
            elif isinstance(style, dict):
                for key in ("default", "hover", "click"):
                    if key in style:
                        output_key = Style(**style[key])
                        output_key.fill_with(output[key])
                        output[key] = output_key
            else:
                raise TypeError(f"Invalid style type: {type(style).__name__}")
            return StyleDef(**output)


StyleType: TypeAlias = StyleDef | dict[str, dict[str, Any]]
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
        if button == MouseButton.BUTTON_LEFT and self._on_click is not None:
            self._on_click(self)

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
