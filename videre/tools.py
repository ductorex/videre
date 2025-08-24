from pathlib import Path

from .layouts.scroll.scrollview import ScrollView
from .widgets.picture import ImageSourceType, Picture
from .windowing.window import Window


def printimg(src: ImageSourceType):
    if isinstance(src, (str, Path)):
        title = str(src)
    else:
        title = "image"

    window = Window(title=title)
    window.controls = [ScrollView(Picture(src))]
    window.run()
