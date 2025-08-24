from collections.abc import Sequence

from videre.core.constants import Alignment
from videre.core.pygame_utils import Surface
from videre.layouts.abstract_controls_layout import AbstractControlsLayout
from videre.layouts.container import Container
from videre.widgets.widget import Widget


class Column(AbstractControlsLayout):
    __wprops__ = {"horizontal_alignment", "expand_horizontal", "space"}
    __slots__ = ()

    def __init__(
        self,
        controls: Sequence[Widget],
        horizontal_alignment=Alignment.START,
        expand_horizontal=True,
        space: int = 0,
        **kwargs
    ):
        super().__init__(controls, **kwargs)
        self.expand_horizontal = expand_horizontal
        self.horizontal_alignment = horizontal_alignment
        self.space = space

    @property
    def horizontal_alignment(self) -> Alignment:
        return self._get_wprop("horizontal_alignment")

    @horizontal_alignment.setter
    def horizontal_alignment(self, horizontal_alignment: Alignment):
        self._set_wprop("horizontal_alignment", horizontal_alignment)

    @property
    def expand_horizontal(self) -> bool:
        return self._get_wprop("expand_horizontal")

    @expand_horizontal.setter
    def expand_horizontal(self, value):
        self._set_wprop("expand_horizontal", bool(value))

    @property
    def space(self) -> int:
        return self._get_wprop("space")

    @space.setter
    def space(self, space: int):
        self._set_wprop("space", space)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        w_hint = width if self.expand_horizontal else None
        max_width = 0
        total_height = 0
        controls = self.controls

        space = self.space
        if len(controls) > 1 and space > 0:
            new_controls = [controls[0]]
            for i in range(1, len(controls)):
                new_controls.append(Container(height=space))
                new_controls.append(controls[i])
            controls = new_controls

        rendered: list[tuple[Widget, Surface] | None] = [None] * len(controls)
        sizes: list[int | None] = [None] * len(controls)

        weights = [ctrl.weight for ctrl in controls]
        total_weight = sum(weights)
        if height is None or total_weight == 0:
            for i, ctrl in enumerate(controls):
                if height is not None and total_height >= height:
                    break
                surface = ctrl.render(window, w_hint)
                rendered[i] = (ctrl, surface)
                sizes[i] = surface.get_height()
                total_height += surface.get_height()
                max_width = max(max_width, surface.get_width())
        else:
            to_render = []
            for i, ctrl in enumerate(controls):
                if total_height >= height:
                    break
                if weights[i]:
                    to_render.append((i, ctrl))
                else:
                    surface = ctrl.render(window, w_hint)
                    rendered[i] = (ctrl, surface)
                    sizes[i] = surface.get_height()
                    total_height += surface.get_height()
                    max_width = max(max_width, surface.get_width())
            remaining_height = height - total_height
            if remaining_height > 0:
                for i, ctrl in to_render:
                    if total_height >= height:
                        break
                    available_height = int(
                        (remaining_height * weights[i]) // total_weight
                    )
                    surface = ctrl.render(window, w_hint, available_height)
                    rendered[i] = (ctrl, surface)
                    sizes[i] = available_height
                    total_height += available_height
                    max_width = max(max_width, surface.get_width())

        alignment = self.horizontal_alignment
        if width is None:
            width = max_width
        else:
            choice = min if alignment == Alignment.START else max
            width = choice(width, max_width)
        if height is None:
            height = total_height
        else:
            height = min(height, total_height)
        column = window.new_surface(width, height)
        y = 0
        for i, render in enumerate(rendered):
            if render:
                ctrl, surface = render
                x = self._align_dim(width, surface.get_width(), alignment)
                column.blit(surface, (x, y))
                self._set_child_position(ctrl, x, y)
                y += sizes[i]
            else:
                # todo see comment in Row
                controls[i].flush_changes()
        return column
