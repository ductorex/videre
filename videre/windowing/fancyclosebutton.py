from videre.widgets.button import Button


class FancyCloseButton(Button):
    """Button which closes fancy box after click."""

    __wprops__ = {}
    __slots__ = ()

    def _click(self):
        super()._click()
        self.get_window().clear_fancybox()
