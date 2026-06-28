from typing import Any

from videre.core.events import MouseButton
from videre.widgets.abstract_check_button import AbstractCheckButton
from videre.widgets.widget import Widget


class Radio(AbstractCheckButton):
    __wprops__ = {"value"}
    __slots__ = ()
    _TEXT_0 = "○"
    _TEXT_1 = "◉"

    def __init__(self, value: Any, **kwargs):
        super().__init__(**kwargs)
        self._set_wprop("value", value)

    @property
    def value(self) -> Any:
        return self._get_wprop("value")

    @classmethod
    def _get_radio_group(cls, widget: Widget | None):
        # TODO As radio/radiogroup is currently implemented, we need local imports to prevent circular imports.
        #      Can we do better ?
        from videre.layouts.radiogroup import RadioGroup  # noqa: PLC0415

        while True:
            if widget is None:
                return None
            if isinstance(widget, RadioGroup):
                return widget
            widget = widget.parent

    def handle_click(self, button: MouseButton):
        group = self._get_radio_group(self._parent)
        if group is not None:
            group.handle_radio_click(self)


def is_radio(widget) -> bool:
    return isinstance(widget, Radio)
