import io
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from PIL import Image

from videre.core.rendering_result import Rendering
from videre.widgets.text import Text
from videre.widgets.widget import Widget

if TYPE_CHECKING:
    from videre.windowing.window import Window

ImageSourceType = str | Path | bytes | bytearray | BinaryIO

logger = logging.getLogger(__name__)


class Picture(Widget):
    __wprops__ = {"alt", "src"}
    __slots__ = ()

    def __init__(self, src: ImageSourceType, alt="image", **kwargs):
        super().__init__(**kwargs)
        self.src = src
        self.alt = alt

    @property
    def src(self) -> ImageSourceType:
        return self._get_wprop("src")

    @src.setter
    def src(self, src: ImageSourceType):
        self._set_wprop("src", src)

    @property
    def alt(self) -> str:
        return self._get_wprop("alt")

    @alt.setter
    def alt(self, alt: str):
        self._set_wprop("alt", alt or "image")

    def _src_to_surface(self, window: "Window"):
        src = self.src
        try:
            if isinstance(src, (bytes, bytearray)):
                src = io.BytesIO(src)
            assert isinstance(src, (str, Path, io.BytesIO))
            image = Image.open(src).convert("RGBA")
            return window.backend.image(image)

        except Exception as exc:
            print(f"Cannot load an image: {type(exc).__name__}: {exc}", file=sys.stderr)
            return None

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Rendering:
        surface = self._src_to_surface(window)
        if surface is None:
            surface = Text(self.alt).render(window, width, height)
        return surface
