from typing import Self

from videre.colors import Color, ColorDef, Colors, parse_color
from videre.core.drawer import Drawer, Drawing


class Gradient:
    """
    Optimized gradient implementation using direct drawing.
    This approach is more efficient than using smoothscale for gradients.

    New implementation was generated with Cursor AI Assistant.
    """

    __slots__ = ("_colors", "_vertical")

    def __init__(self, *colors: Color, vertical=False):
        self._colors: tuple[Color, ...] = colors or (Colors.transparent,)
        self._vertical: bool = vertical

    def __hash__(self) -> int:
        return hash(self._colors + (self._vertical,))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Gradient):
            return NotImplemented
        return self._colors == other._colors and self._vertical is other._vertical

    @property
    def colors(self) -> tuple[Color, ...]:
        return self._colors

    @property
    def vertical(self) -> bool:
        return self._vertical

    def _interpolate_color(self, color1: Color, color2: Color, factor: float) -> Color:
        """Interpolate between two colors based on a factor (0.0 to 1.0)."""
        r = int(color1.r + (color2.r - color1.r) * factor)
        g = int(color1.g + (color2.g - color1.g) * factor)
        b = int(color1.b + (color2.b - color1.b) * factor)
        a = int(color1.a + (color2.a - color1.a) * factor)
        return Color(r, g, b, a)

    def generate(self, width: int, height: int) -> Drawer:
        if width < 0:
            raise ValueError("width cannot be negative")
        if height < 0:
            raise ValueError("height cannot be negative")

        surface = Drawer(width, height)

        if len(self._colors) == 1:
            Drawing.fill(surface, self._colors[0])
            return surface

        if self._vertical:
            # Vertical gradient
            for i in range(height):
                # Calculate relative position (0.0 to 1.0)
                pos = i / (height - 1) if height > 1 else 0

                # Find the two colors to interpolate between
                color_index = pos * (len(self._colors) - 1)
                color1_index = int(color_index)
                color2_index = min(color1_index + 1, len(self._colors) - 1)

                # Calculate interpolation factor between the two colors
                factor = color_index - color1_index

                # Interpolate color
                color = self._interpolate_color(
                    self._colors[color1_index], self._colors[color2_index], factor
                )

                # Draw a horizontal line
                Drawing.line(surface, color, (0, i), (width - 1, i))
        else:
            # Horizontal gradient
            for i in range(width):
                # Calculate relative position (0.0 to 1.0)
                pos = i / (width - 1) if width > 1 else 0

                # Find the two colors to interpolate between
                color_index = pos * (len(self._colors) - 1)
                color1_index = int(color_index)
                color2_index = min(color1_index + 1, len(self._colors) - 1)

                # Calculate interpolation factor between the two colors
                factor = color_index - color1_index

                # Interpolate color
                color = self._interpolate_color(
                    self._colors[color1_index], self._colors[color2_index], factor
                )

                # Draw a vertical line
                Drawing.line(surface, color, (i, 0), (i, height - 1))

        return surface

    @classmethod
    def parse(cls, coloring: Self | ColorDef | None) -> "Gradient":
        if isinstance(coloring, Gradient):
            return coloring
        return Gradient(parse_color(coloring))


ColoringDefinition = ColorDef | Gradient
