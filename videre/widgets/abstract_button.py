from videre import StyleDef
from videre.colors import Colors
from videre.core.sides.border import Border
from videre.layouts.div import Div, OnClickType
from videre.widgets.text import Text


class AbstractButton(Div):
    __wprops__ = {"text", "disabled"}
    __slots__ = ("_text", "_enabled_style", "_disabled_style", "_enabled_on_click")
    __disabled_style__ = StyleDef(
        default=Div.__style__.default.copy(
            border=Border.all(1, Colors.lightgray), color=Colors.lightgray
        )
    )

    def __init__(self, text: str, square=False, disabled=False, **kwargs):
        style = {"default": {"square": square}}
        self._text = Text(height_delta=0)
        super().__init__(self._text, style=style, **kwargs)
        self._disabled_style = self.__disabled_style__.merged_with(style)
        self._enabled_style = self._style
        self._enabled_on_click = None
        # Set disabled and style
        self.disabled = disabled
        # Set text, according to style
        self.text = text

    @property
    def disabled(self) -> bool:
        return self._get_wprop("disabled")

    @disabled.setter
    def disabled(self, disabled: bool):
        prev_disabled = bool(self._get_wprop("disabled"))
        disabled = bool(disabled)
        if disabled is not prev_disabled:
            self._set_wprop("disabled", disabled)
            self._style = self._disabled_style if disabled else self._enabled_style
            self._set_style()
            self._update_on_click()

    @property
    def text(self) -> str:
        return self._text.text

    @text.setter
    def text(self, text: str):
        self._text.text = text.strip()

    def _get_on_click(self) -> OnClickType | None:
        return self._on_click

    def _set_on_click(self, callback: OnClickType | None):
        if self._enabled_on_click is not callback:
            self._enabled_on_click = callback
            self._update_on_click()

    def _update_on_click(self):
        function = None if self.disabled else self._enabled_on_click
        if self._on_click is not function:
            self._on_click = function
            self.update()

    def _set_style(self):
        super()._set_style()
        self._text.color = self._get_style().color
