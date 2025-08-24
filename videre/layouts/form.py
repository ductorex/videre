from collections import Counter
from typing import Any

from videre.layouts.control_layout import ControlLayout
from videre.layouts.radiogroup import RadioGroup
from videre.widgets.checkbox import Checkbox
from videre.widgets.dropdown import Dropdown
from videre.widgets.textinput.textinput import TextInput
from videre.widgets.widget import Widget

# Dictionary of input widgets.
# Dict key is a widget that can be used as an input.
# Each input widget must have a "name" field.
# Dict value is the name of "value" field in widget class.
_FORM_TYPES_: dict[type, str] = {
    RadioGroup: "value",
    Checkbox: "checked",
    Dropdown: "selected",
    TextInput: "value",
}


def _is_input(widget: Widget) -> bool:
    return type(widget) in _FORM_TYPES_


class Form(ControlLayout):
    __slots__ = ()
    __wprops__ = {}

    def __init__(self, control: Widget, **kwargs):
        super().__init__(control, **kwargs)

    def values(self) -> dict[str, Any]:
        inputs = self.collect_matches(_is_input)
        output = {}
        type_counter = Counter()
        for widget in inputs:
            cls = type(widget)
            name = getattr(widget, "name", None)
            if not name:
                while True:
                    count = type_counter.get(cls, 0)
                    type_counter.update((cls,))
                    name = f"{cls.__name__}{count or ''}"
                    if name not in output:
                        break
            value = getattr(widget, _FORM_TYPES_[cls])
            output[name] = value
        return output
