from typing import Self

from videre.colors import ColorDef, Colors, parse_color
from videre.core.drawer import Color, Drawer, Position
from videre.core.pygame_utils import PygameUtils


class Gradient(PygameUtils):
    """
    Optimized gradient implementation using direct drawing with pygame.draw.
    This approach is more efficient than using smoothscale for gradients.

    New implementation was generated with Cursor AI Assistant.
    """

    __slots__ = ("_colors", "_vertical")

    def __init__(self, *colors: Color, vertical=False):
        super().__init__()

        self._colors = colors or [Colors.transparent]
        self._vertical: bool = vertical

    def _interpolate_color(self, color1: Color, color2: Color, factor: float) -> Color:
        """Interpolate between two colors based on a factor (0.0 to 1.0)."""
        r = int(color1.r + (color2.r - color1.r) * factor)
        g = int(color1.g + (color2.g - color1.g) * factor)
        b = int(color1.b + (color2.b - color1.b) * factor)
        a = int(color1.a + (color2.a - color1.a) * factor)
        return Color(r, g, b, a)

    def generate_drawer(self, width: int, height: int) -> Drawer:
        drawer = Drawer(width, height)

        if len(self._colors) == 1:
            drawer.fill(self._colors[0])
            return drawer

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
                drawer.line(color, Position(0, i), Position(width - 1, i))
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
                drawer.line(color, Position(i, 0), Position(i, height - 1))

        return drawer

    @classmethod
    def parse(cls, coloring: ColorDef | Self) -> "Gradient":
        if isinstance(coloring, Gradient):
            return coloring
        return Gradient(parse_color(coloring))


ColoringDefinition = ColorDef | Gradient
