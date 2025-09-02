import dataclasses
from dataclasses import dataclass
from typing import Any, Self, TypeAlias

from videre import Alignment, Border, Padding
from videre.core.pygame_utils import Color
from videre.gradient import ColoringDefinition


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
