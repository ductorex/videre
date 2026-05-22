from videre.colors import Colors
from videre.core.pygame_backend.definitions import Surface
from videre.core.pygame_backend.primitives import Pygame
from videre.core.sides.border import Border
from videre.layouts.abstractlayout import AbstractLayout
from videre.layouts.container import Container
from videre.widgets.widget import Widget


class Context(AbstractLayout):
    __slots__ = ("_relative", "_x", "_y")
    __wprops__ = {}
    __size__ = 1

    def __init__(self, relative: Widget, control: Widget, x=0, y=0, **kwargs):
        container = Container(
            control, border=Border.all(1), background_color=Colors.white
        )
        self._relative = relative
        self._x = x
        self._y = y
        super().__init__([container], **kwargs)

    @property
    def relative(self) -> Widget:
        return self._relative

    def handle_focus_in(self) -> Widget | None:
        return self._relative.handle_focus_in()

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Surface:
        self._relative._assert_rendered()
        (container,) = self._controls()
        x = self._relative.global_x + self._x
        y = self._relative.global_y + self._relative.rendered_height + self._y

        control_surface = container.render(window, None, None)
        surface = Pygame.new_surface(width or 0, height or 0)
        Pygame.blit(surface, control_surface, (x, y))
        self._set_child_position(container, x, y)
        return surface
