class WidgetByKeyGetter:
    __slots__ = ("key",)

    def __init__(self, key: str):
        self.key = key

    def __call__(self, widget) -> bool:
        return widget.key == self.key
