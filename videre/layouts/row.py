from collections.abc import Sequence

from videre.core.constants import Alignment
from videre.core.pygame_utils import Surface
from videre.layouts.abstract_controls_layout import AbstractControlsLayout
from videre.layouts.container import Container
from videre.widgets.widget import Widget


class Row(AbstractControlsLayout):
    __wprops__ = {"vertical_alignment", "expand_vertical", "space"}
    __slots__ = ()

    def __init__(
        self,
        controls: Sequence[Widget],
        vertical_alignment=Alignment.START,
        expand_vertical=True,
        space: int = 0,
        **kwargs
    ):
        super().__init__(controls, **kwargs)
        self.vertical_alignment = vertical_alignment
        self.expand_vertical = expand_vertical
        self.space = space

    @property
    def vertical_alignment(self) -> Alignment:
        return self._get_wprop("vertical_alignment")

    @vertical_alignment.setter
    def vertical_alignment(self, vertical_alignment: Alignment):
        self._set_wprop("vertical_alignment", vertical_alignment)

    @property
    def expand_vertical(self) -> bool:
        return self._get_wprop("expand_vertical")

    @expand_vertical.setter
    def expand_vertical(self, value):
        self._set_wprop("expand_vertical", bool(value))

    @property
    def space(self) -> int:
        return self._get_wprop("space")

    @space.setter
    def space(self, space: int):
        self._set_wprop("space", space)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        h_hint = height if self.expand_vertical else None
        max_height = 0
        total_width = 0
        controls = self.controls

        space = self.space
        if len(controls) > 1 and space > 0:
            new_controls = [controls[0]]
            for i in range(1, len(controls)):
                new_controls.append(Container(width=space))
                new_controls.append(controls[i])
            controls = new_controls

        rendered: list[tuple[Widget, Surface] | None] = [None] * len(controls)
        sizes: list[int | None] = [None] * len(controls)

        weights = [ctrl.weight for ctrl in controls]
        total_weight = sum(weights)
        if width is None or total_weight == 0:
            for i, ctrl in enumerate(controls):
                if width is not None and total_width >= width:
                    break
                surface = ctrl.render(window, None, h_hint)
                rendered[i] = (ctrl, surface)
                sizes[i] = surface.get_width()
                total_width += surface.get_width()
                max_height = max(max_height, surface.get_height())
        else:
            to_render = []
            for i, ctrl in enumerate(controls):
                if total_width >= width:
                    break
                if weights[i]:
                    to_render.append((i, ctrl))
                else:
                    surface = ctrl.render(window, None, h_hint)
                    rendered[i] = (ctrl, surface)
                    sizes[i] = surface.get_width()
                    total_width += surface.get_width()
                    max_height = max(max_height, surface.get_height())
            remaining_width = width - total_width
            if remaining_width > 0:
                for i, ctrl in to_render:
                    if total_width >= width:
                        break
                    available_width = int(
                        (remaining_width * weights[i]) // total_weight
                    )
                    surface = ctrl.render(window, available_width, h_hint)
                    rendered[i] = (ctrl, surface)
                    sizes[i] = available_width
                    total_width += available_width
                    max_height = max(max_height, surface.get_height())

        alignment = self.vertical_alignment
        if width is None:
            width = total_width
        else:
            width = min(width, total_width)
        if height is None:
            height = max_height
        else:
            choice = min if alignment == Alignment.START else max
            height = choice(height, max_height)
        row = window.new_surface(width, height)
        x = 0
        for i, render in enumerate(rendered):
            if render:
                ctrl, surface = render
                y = self._align_dim(height, surface.get_height(), alignment)
                row.blit(surface, (x, y))
                self._set_child_position(ctrl, x, y)
                x += sizes[i]
            else:
                # TODO should we instead fully render control but not display it ?
                # Because, sometimes control rendering may also imply
                # further control state changes, so it may better
                # better to fully render control, even if it
                # must not be displayed in the layout.
                controls[i].flush_changes()
        return row
