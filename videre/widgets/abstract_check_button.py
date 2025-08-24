from videre.core.constants import Alignment
from videre.core.events import MouseButton
from videre.layouts.div import Div, Style, StyleDef
from videre.widgets.character import Character


class AbstractCheckButton(Div):
    __wprops__ = {"_checked"}
    __slots__ = ("_text",)
    _TEXT_0 = "☐"
    _TEXT_1 = "☑"
    __style__ = StyleDef(
        default=Style(
            vertical_alignment=Alignment.CENTER,
            horizontal_alignment=Alignment.CENTER,
            # set width and height to -1 to render with natural size
            width=-1,
            height=-1,
        )
    )

    def __init__(self, **kwargs):
        self._text = Character(self._TEXT_0)
        super().__init__(self._text, **kwargs)
        self._set_wprop("_checked", False)

    def _get_checked(self) -> bool:
        return self._get_wprop("_checked")

    def _set_checked(self, checked: bool):
        self._set_wprop("_checked", bool(checked))
        self._text.text = self._compute_checked_text()

    def handle_click(self, button: MouseButton):
        ret = super().handle_click(button)
        if button == MouseButton.BUTTON_LEFT:
            self._set_checked(not self._get_checked())
        return ret

    def _compute_checked_text(self) -> str:
        return self._TEXT_1 if self._get_checked() else self._TEXT_0

    def _set_style(self):
        self._text.strong = bool(self._hover)
        return super()._set_style()
