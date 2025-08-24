from typing import Any, Callable, Self

from videre.layouts.control_layout import ControlLayout
from videre.widgets.widget import Widget


class RadioGroup(ControlLayout):
    __wprops__ = {"value", "on_change", "can_deselect", "name"}
    __slots__ = ()

    def __init__(
        self, control: Widget, value=None, on_change=None, can_deselect=False, **kwargs
    ):
        super().__init__(control, **kwargs)
        self.on_change = on_change
        self._set_wprop("can_deselect", bool(can_deselect))
        self._set_new_value(value, react=False)

    @property
    def can_deselect(self) -> bool:
        return self._get_wprop("can_deselect")

    @property
    def control(self) -> Widget:
        (control,) = self._controls()
        return control

    @property
    def value(self) -> Any:
        return self._get_wprop("value")

    @value.setter
    def value(self, value: Any):
        self._set_new_value(value)

    @property
    def on_change(self) -> Callable[[Self], None] | None:
        return self._get_wprop("on_change")

    @on_change.setter
    def on_change(self, callback: Callable[[Self], None] | None):
        self._set_wprop("on_change", callback)

    def handle_radio_click(self, radio):
        if not radio._get_checked():
            new_value = radio.value
        elif self.can_deselect:
            new_value = None
        else:
            return
        self._set_new_value(new_value)

    def _set_new_value(self, new_value: Any, react=True):
        if new_value == self._get_wprop("value"):
            return
        self._set_wprop("value", new_value)
        for radio in self.collect_matches(is_radio):
            radio._set_checked(radio.value == new_value)
        if react:
            on_change = self.on_change
            if on_change:
                on_change(self)


def is_radio(widget) -> bool:
    from videre.widgets.radio import Radio

    return isinstance(widget, Radio)
