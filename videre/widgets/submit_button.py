from typing import Any, Callable

from videre.layouts.form import Form
from videre.widgets.abstract_button import AbstractButton

OnSubmitType = Callable[[dict[str, Any]], None]


class SubmitButton(AbstractButton):
    __wprops__ = {"on_submit"}
    __slots__ = ()

    def __init__(self, text: str, on_submit: OnSubmitType | None = None, **kwargs):
        kwargs["on_click"] = self.submit
        super().__init__(text, **kwargs)
        self.on_submit = on_submit

    @property
    def on_submit(self) -> OnSubmitType | None:
        return self._get_wprop("on_submit")

    @on_submit.setter
    def on_submit(self, value: OnSubmitType | None) -> None:
        self._set_wprop("on_submit", value)

    def submit(self, *args: Any, **kwargs: Any) -> None:
        on_submit = self.on_submit
        if on_submit:
            form: Form | None = None
            parent = self.parent
            while True:
                if parent is None:
                    break
                elif isinstance(parent, Form):
                    form = parent
                    break
                else:
                    parent = parent.parent
            if form is not None:
                on_submit(form.values())
