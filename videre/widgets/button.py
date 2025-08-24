from videre.layouts.div import OnClickType
from videre.widgets.abstract_button import AbstractButton


class Button(AbstractButton):
    __wprops__ = {}
    __slots__ = ()

    def __init__(self, text: str, on_click: OnClickType | None = None, **kwargs):
        super().__init__(text, **kwargs)
        # Set on click, according to disabled
        self._set_on_click(on_click)

    @property
    def on_click(self) -> OnClickType | None:
        return self._get_on_click()

    @on_click.setter
    def on_click(self, callback: OnClickType | None):
        self._set_on_click(callback)
