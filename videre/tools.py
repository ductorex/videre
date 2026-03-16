from pathlib import Path

from .layouts.scroll.scrollview import ScrollView
from .widgets.picture import ImageSourceType, Picture
from .windowing.window import Window


def _build_image_window(src: ImageSourceType) -> Window:
    if isinstance(src, (str, Path)):
        title = str(src)
    else:
        title = "image"

    window = Window(title=title)
    window.controls = [ScrollView(Picture(src))]
    return window


def printimg(src: ImageSourceType):
    _build_image_window(src).run()
