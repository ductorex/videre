from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.widgets.empty_widget import EmptyWidget
from videre.widgets.text import Text
from videre.widgets.widget import Widget


class Label(Text):
    __wprops__ = {}
    __slots__ = ["_for_button", "_for_key"]

    def __init__(self, for_button: str | Widget, **kwargs):
        super().__init__(**kwargs)
        if isinstance(for_button, Widget):
            self._for_button = for_button
            self._for_key = for_button.key
        else:
            assert isinstance(for_button, str)
            self._for_button = None
            self._for_key = for_button

    def _get_button(self) -> Widget:
        if self._for_button is None:
            candidates = self.get_root().collect_matches(
                lambda w: w.key == self._for_key
            )
            if len(candidates) == 1:
                (self._for_button,) = candidates
            else:
                # TODO Warning here ?
                self._for_button = EmptyWidget()
        return self._for_button

    def handle_mouse_enter(self, event: MouseEvent):
        button = self._get_button()
        return button.handle_mouse_enter(event.with_coordinates(x=button.x, y=button.y))

    def handle_mouse_exit(self):
        return self._get_button().handle_mouse_exit()

    def handle_mouse_down(self, event: MouseEvent):
        bw = self._get_button()
        return bw.handle_mouse_down(event)

    def handle_mouse_up(self, event: MouseEvent):
        bw = self._get_button()
        return bw.handle_mouse_up(event)

    def handle_mouse_down_canceled(self, button: MouseButton):
        return self._get_button().handle_mouse_down_canceled(button)

    def handle_click(self, button: MouseButton):
        return self._get_button().handle_click(button)
