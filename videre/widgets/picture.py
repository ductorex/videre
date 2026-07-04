import io
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO

from PIL import Image

from videre.core.drawer import Drawer
from videre.widgets.text import Text
from videre.widgets.widget import Widget

if TYPE_CHECKING:
    from videre.windowing.window import Window

ImageSourceType = str | Path | bytes | bytearray | BinaryIO

logger = logging.getLogger(__name__)


class Picture(Widget):
    """An image, displayed at its natural size unless `width`/`height` are
    given (then smooth-scaled; a single one keeps the aspect ratio, like an
    HTML <img>). With both given, `keep_ratio=True` fits the image *inside*
    the box instead of stretching to it (CSS object-fit: contain)."""

    __wprops__ = {"alt", "src", "width", "height", "keep_ratio"}
    __slots__ = ()

    def __init__(
        self,
        src: ImageSourceType,
        alt="image",
        width: int | None = None,
        height: int | None = None,
        keep_ratio: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.src = src
        self.alt = alt
        self.width = width
        self.height = height
        self.keep_ratio = keep_ratio

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

    @property
    def width(self) -> int | None:
        return self._get_wprop("width")

    @width.setter
    def width(self, width: int | None):
        self._set_wprop("width", width)

    @property
    def height(self) -> int | None:
        return self._get_wprop("height")

    @height.setter
    def height(self, height: int | None):
        self._set_wprop("height", height)

    @property
    def keep_ratio(self) -> bool:
        return self._get_wprop("keep_ratio")

    @keep_ratio.setter
    def keep_ratio(self, keep_ratio: bool):
        self._set_wprop("keep_ratio", bool(keep_ratio))

    def _src_to_surface(self, window: "Window") -> Drawer | None:
        src = self.src
        try:
            if isinstance(src, (bytes, bytearray)):
                src = io.BytesIO(src)
            assert isinstance(src, (str, Path, io.BytesIO))
            image = Image.open(src).convert("RGBA")
            return Drawer.image(image)

        except Exception as exc:
            print(f"Cannot load an image: {type(exc).__name__}: {exc}", file=sys.stderr)
            return None

    def draw(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        surface = self._src_to_surface(window)
        if surface is None:
            return Text(self.alt).render(window, width, height)
        view_w, view_h = self.width, self.height
        natural_w, natural_h = surface.get_width(), surface.get_height()
        if view_w is None and view_h is None:
            view_w, view_h = natural_w, natural_h
        elif view_w is None:
            assert view_h is not None
            view_w = max(1, round(natural_w * view_h / natural_h))
        elif view_h is None:
            view_h = max(1, round(natural_h * view_w / natural_w))
        elif self.keep_ratio:
            # contain: the largest ratio-preserving size fitting the box
            # (scales up small images too, like QPixmap.scaled/object-fit).
            ratio = min(view_w / natural_w, view_h / natural_h)
            view_w = max(1, round(natural_w * ratio))
            view_h = max(1, round(natural_h * ratio))
        return (
            surface
            if (surface.get_width(), surface.get_height()) == (view_w, view_h)
            else Drawer.smoothscale(surface, view_w, view_h)
        )
