import dataclasses
from dataclasses import dataclass
from typing import Any, Iterator, Self, TypeAlias

from videre import Alignment, Border, Padding
from videre.colors import Color
from videre.gradient import ColoringDefinition


@dataclass(slots=True)
class Style:
    border: Border | None = None
    padding: Padding | None = None
    background_color: ColoringDefinition | None = None
    vertical_alignment: Alignment | None = None
    horizontal_alignment: Alignment | None = None
    width: int | None = None
    height: int | None = None
    square: bool | None = None
    color: Color | None = None

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        for field in dataclasses.fields(self):
            yield field.name, getattr(self, field.name)

    def fill_with(self, other: "Style"):
        for field in dataclasses.fields(self):
            key = field.name
            if getattr(self, key) is None:
                setattr(self, key, getattr(other, key))

    def get_specific_from(self, other: "Style"):
        return Style(
            **{key: value for key, value in self if value != getattr(other, key)}
        )

    def copy(self, **changes) -> Self:
        return dataclasses.replace(self, **changes)


@dataclass(slots=True)
class StyleDef:
    default: Style = dataclasses.field(default_factory=Style)
    hover: Style = dataclasses.field(default_factory=Style)
    click: Style = dataclasses.field(default_factory=Style)

    def __post_init__(self):
        self.hover.fill_with(self.default)
        self.click.fill_with(self.default)

    def merged_with(self, style: "StyleType | None") -> "StyleDef":
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
