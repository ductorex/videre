from typing import Sequence

import pygame

from videre.colors import Colors
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_utils import Color, Surface
from videre.layouts.abstractlayout import AbstractLayout
from videre.layouts.column import Column
from videre.layouts.container import Container
from videre.layouts.row import Row
from videre.widgets.button import Button
from videre.widgets.text import Text
from videre.widgets.widget import Widget


class Fancybox(AbstractLayout):
    __slots__ = ()
    __size__ = 1

    def __init__(
        self,
        content: Widget,
        title: str | Text = "Fancybox",
        buttons: Sequence[Button] = (),
        expand_buttons=True,
    ):
        button_close = Button("✕", on_click=self._on_close, square=True)

        if not isinstance(title, Text):
            title = Text(title)
        title.weight = 1

        formatted_buttons = []
        for button in buttons:
            if expand_buttons:
                button.weight = 1
            formatted_buttons.append(button)

        dialog = Column(
            [
                Row([title, button_close]),
                Container(content, weight=1),
                *([Row(formatted_buttons)] if formatted_buttons else ()),
            ],
            expand_horizontal=True,
        )
        super().__init__([dialog])

    def _on_close(self, widget):
        self.get_window().clear_fancybox()

    def get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        owner = super().get_mouse_owner(x_in_parent, y_in_parent)
        return owner or MouseOwnership(self, x_in_parent, y_in_parent)

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        assert width is not None
        assert height is not None
        dialog_part = 0.8
        dialog_width = int(dialog_part * width)
        dialog_height = int(dialog_part * height)
        (dialog,) = self._controls()
        dialog_surface = dialog.render(window, dialog_width, dialog_height)
        dialog_x = (width - dialog_width) // 2
        dialog_y = (height - dialog_height) // 2
        surface = window.new_surface(width, height)
        surface.fill(Color(0, 0, 0, 64))
        surface.fill(
            Colors.white, pygame.Rect(dialog_x, dialog_y, dialog_width, dialog_height)
        )
        surface.blit(dialog_surface, (dialog_x, dialog_y))
        self._set_child_position(dialog, dialog_x, dialog_y)
        return surface
