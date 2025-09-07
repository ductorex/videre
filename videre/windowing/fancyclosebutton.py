from videre.widgets.button import Button


class FancyCloseButton(Button):
    """Button which closes fancy box after click."""

    __wprops__ = {}
    __slots__ = ()

    def click(self) -> None:
        if not self.disabled:
            super().click()
            self.get_window().clear_fancybox()
