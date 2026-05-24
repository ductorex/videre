from collections.abc import Sequence

from videre.core.constants import Alignment
from videre.core.pygame_backend.primitives import Pygame
from videre.core.rendering_result import Rendering
from videre.layouts.abstract_controls_layout import AbstractControlsLayout
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
        **kwargs,
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

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Rendering:
        w_hint = width if self.expand_horizontal else None
        max_width = 0
        total_height = 0
        controls = self.controls
        space = self.space
        rendered: list[tuple[Widget, Rendering] | None] = [None] * len(controls)
        sizes: list[int | None] = [None] * len(controls)

        total_space = space * max(0, len(controls) - 1)
        nb_rendered = 0

        weights = [ctrl.weight for ctrl in controls]
        total_weight = sum(weights)
        if height is None or total_weight == 0:
            for i, ctrl in enumerate(controls):
                if (
                    height is not None
                    and total_height + (nb_rendered * space) >= height
                ):
                    break
                surface = ctrl.render(window, w_hint)
                rendered[i] = (ctrl, surface)
                sizes[i] = surface.get_height()
                total_height += surface.get_height()
                max_width = max(max_width, surface.get_width())
                nb_rendered += 1
        else:
            to_render = []
            for i, ctrl in enumerate(controls):
                if total_height + (nb_rendered * space) >= height:
                    break
                if weights[i]:
                    to_render.append((i, ctrl))
                else:
                    surface = ctrl.render(window, w_hint)
                    rendered[i] = (ctrl, surface)
                    sizes[i] = surface.get_height()
                    total_height += surface.get_height()
                    max_width = max(max_width, surface.get_width())
                    nb_rendered += 1
            remaining_height = height - total_height - space * max(0, nb_rendered - 1)
            if remaining_height > 0:
                remaining_without_space = max(
                    0, remaining_height - space * (len(controls) - nb_rendered)
                )
                for i, ctrl in to_render:
                    if total_height + space * (nb_rendered - 1) >= height:
                        break
                    available_height = int(
                        (remaining_without_space * weights[i]) // total_weight
                    )
                    surface = ctrl.render(window, w_hint, available_height)
                    rendered[i] = (ctrl, surface)
                    sizes[i] = available_height
                    total_height += available_height
                    max_width = max(max_width, surface.get_width())
                    nb_rendered += 1

        alignment = self.horizontal_alignment
        if width is None:
            width = max_width
        else:
            width = (
                min(width, max_width)
                if alignment == Alignment.START
                else max(width, max_width)
            )
        if height is None:
            height = total_height + total_space
        else:
            height = min(height, total_height + space * max(0, nb_rendered - 1))
        column = Pygame.new_surface(width, height)
        y = 0
        for i, render in enumerate(rendered):
            if render:
                ctrl, surface = render
                size_i = sizes[i]
                assert size_i is not None
                x = self._align_dim(width, surface.get_width(), alignment)
                Pygame.blit(column, surface, (x, y))
                self._set_child_position(ctrl, x, y)
                y += size_i + space
            else:
                # todo see comment in Row
                controls[i].flush_changes()
                y += space
        return column
