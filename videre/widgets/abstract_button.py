from videre import StyleDef
from videre.colors import Colors
from videre.core.sides.border import Border
from videre.layouts.div.div import Div
from videre.widgets.text import Text


class AbstractButton(Div):
    __wprops__ = {"text", "disabled"}
    __slots__ = ("_text", "_enabled_style", "_disabled_style")
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

    @property
    def text(self) -> str:
        return self._text.text

    @text.setter
    def text(self, text: str):
        self._text.text = text.strip()

    def click(self):
        if not self.disabled:
            return super().click()

    def _set_style(self):
        super()._set_style()
        self._text.color = self._get_style().color
