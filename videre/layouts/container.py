import pygame
import pygame.gfxdraw

from videre.core.constants import Alignment
from videre.core.pygame_utils import Surface
from videre.core.sides.border import Border
from videre.core.sides.padding import Padding
from videre.gradient import ColoringDefinition, Gradient
from videre.layouts.abstractlayout import AbstractLayout
from videre.widgets.empty_widget import EmptyWidget
from videre.widgets.widget import Widget


class Container(AbstractLayout):
    __wprops__ = {
        "border",
        "padding",
        "background_color",
        "vertical_alignment",
        "horizontal_alignment",
        "width",
        "height",
        "square",
    }
    __slots__ = ()
    __size__ = 1

    def __init__(
        self,
        control: Widget | None = None,
        *,
        border: Border | None = None,
        padding: Padding | None = None,
        background_color: ColoringDefinition = None,
        vertical_alignment: Alignment = Alignment.START,
        horizontal_alignment: Alignment = Alignment.START,
        width: int = None,
        height: int = None,
        square: bool = False,
        **kwargs
    ):
        super().__init__([control or EmptyWidget()], **kwargs)
        self.border = border
        self.padding = padding
        self.background_color = background_color
        self.vertical_alignment = vertical_alignment
        self.horizontal_alignment = horizontal_alignment
        self.width = width
        self.height = height
        self.square = square

    @property
    def control(self) -> Widget:
        (control,) = self._controls()
        return control

    @control.setter
    def control(self, control: Widget | None):
        self._set_controls([control or EmptyWidget()])

    @property
    def border(self) -> Border:
        return self._get_wprop("border")

    @border.setter
    def border(self, border: Border | None):
        self._set_wprop("border", border or Border())

    @property
    def padding(self) -> Padding:
        return self._get_wprop("padding")

    @padding.setter
    def padding(self, padding: Padding | None):
        self._set_wprop("padding", padding or Padding())

    @property
    def background_color(self) -> Gradient:
        return self._get_wprop("background_color")

    @background_color.setter
    def background_color(self, coloring: ColoringDefinition):
        self._set_wprop("background_color", Gradient.parse(coloring))

    @property
    def horizontal_alignment(self) -> Alignment:
        return self._get_wprop("horizontal_alignment")

    @horizontal_alignment.setter
    def horizontal_alignment(self, alignment: Alignment | None):
        self._set_wprop("horizontal_alignment", alignment or Alignment.START)

    @property
    def vertical_alignment(self) -> Alignment:
        return self._get_wprop("vertical_alignment")

    @vertical_alignment.setter
    def vertical_alignment(self, alignment: Alignment | None):
        self._set_wprop("vertical_alignment", alignment or Alignment.START)

    @property
    def width(self) -> int | None:
        return self._get_wprop("width")

    @width.setter
    def width(self, width: int | None):
        self._set_wprop("width", width)

    @property
    def height(self) -> int | None:
        return self._get_wprop("height")

    @height.setter
    def height(self, height: int | None):
        self._set_wprop("height", height)

    @property
    def square(self) -> bool:
        return self._get_wprop("square")

    @square.setter
    def square(self, square: bool):
        self._set_wprop("square", bool(square))

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        square = self.square
        width = _resolve_size(self.width, width)
        height = _resolve_size(self.height, height)
        border = self.border
        margin = self.padding + border.margin()

        min_width = border.left.width + border.right.width
        min_height = border.top.width + border.bottom.width

        control = self.control

        if width is None and height is None:
            # no size available
            inner_surface = control.render(window, width, height)
            inner_width = inner_surface.get_width()
            inner_height = inner_surface.get_height()
            outer_width = margin.get_outer_width(inner_width)
            outer_height = margin.get_outer_height(inner_height)
            if square:
                dim = max(outer_width, outer_height)
                outer_width = outer_height = dim
                inner_width = margin.get_inner_width(outer_width)
                inner_height = margin.get_inner_height(outer_height)
        elif width is None:
            # height available
            outer_height = max(height, min_height)
            inner_height = margin.get_inner_height(outer_height)
            if square:
                outer_width = outer_height
                inner_width = margin.get_inner_width(outer_width)
                inner_surface = control.render(window, inner_width, inner_height)
            else:
                inner_surface = control.render(window, None, inner_height)
                inner_width = inner_surface.get_width()
                outer_width = margin.get_outer_width(inner_width)
        elif height is None:
            # width available
            outer_width = max(width, min_width)
            inner_width = margin.get_inner_width(outer_width)
            if square:
                outer_height = outer_width
                inner_height = margin.get_inner_height(outer_height)
                inner_surface = control.render(window, inner_width, inner_height)
            else:
                inner_surface = control.render(window, inner_width, None)
                inner_height = inner_surface.get_height()
                outer_height = margin.get_outer_height(inner_height)
        else:
            # width and height available
            outer_width = max(width, min_width)
            outer_height = max(height, min_height)
            if square:
                dim = min(outer_width, outer_height)
                outer_width = outer_height = dim
            inner_width = margin.get_inner_width(outer_width)
            inner_height = margin.get_inner_height(outer_height)
            inner_surface = control.render(window, inner_width, inner_height)

        x = self._align_dim(
            inner_width, inner_surface.get_width(), self.horizontal_alignment
        )
        y = self._align_dim(
            inner_height, inner_surface.get_height(), self.vertical_alignment
        )
        # inner_box = pygame.Rect(0, 0, inner_width - x, inner_height - y)
        surface = self.background_color.generate(outer_width, outer_height)
        for border_color, border_points in border.describe_borders(
            outer_width, outer_height
        ):
            if border_points:
                if border_points[0] == border_points[-1]:
                    # Certainly a line
                    pygame.gfxdraw.line(
                        surface, *border_points[0], *border_points[1], border_color
                    )
                else:
                    pygame.gfxdraw.filled_polygon(surface, border_points, border_color)
        inner_x, inner_y = margin.left + x, margin.top + y
        surface.blit(inner_surface, (inner_x, inner_y), area=None)
        self._set_child_position(control, inner_x, inner_y)
        return surface


def _resolve_size(view_size: int | None, parent_size: int | None) -> int | None:
    """
    Compute a size based on view size and parent size.
    Allow view size to have negative value (typically -1) to force no size,
    which means to render the container with its natural size.
    """
    if view_size is None and parent_size is None:
        size = None
    elif view_size is None:
        size = parent_size
    elif parent_size is None:
        size = view_size
    else:
        size = min(view_size, parent_size)
    return size if size is not None and size >= 0 else None
