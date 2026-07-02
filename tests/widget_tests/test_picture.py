import io
import pathlib

import PIL.Image
import pytest

from videre import Picture
from videre.testing.utils import IMAGE_EXAMPLE


class SrcProvider:
    _string = IMAGE_EXAMPLE
    _path = pathlib.Path(_string)

    def string(self):
        return self._string

    def path(self):
        return self._path

    def bytes(self) -> bytes:
        with open(self._string, mode="rb") as f:
            return f.read()

    def bytearray(self):
        return bytearray(self.bytes())

    def file_like(self):
        return io.BytesIO(self.bytes())


@pytest.mark.parametrize("src", ["string", "path", "bytes", "bytearray", "file_like"])
def test_image(src, fake_win):
    src_provider = SrcProvider()
    fake_win.controls = [Picture(src=getattr(src_provider, src)())]
    fake_win.check()


@pytest.mark.parametrize("alt", [None, "Bad image!"])
def test_bad_image(alt, fake_win):
    fake_win.controls = [Picture("", alt=alt)]
    fake_win.check()


def test_image_resized(fake_win):
    fake_win.controls = [Picture(IMAGE_EXAMPLE, width=100, height=60)]
    fake_win.check()


def test_image_resized_keeps_ratio(fake_win):
    # A single dimension scales the other one like an HTML <img>.
    picture = Picture(IMAGE_EXAMPLE, width=100)
    fake_win.controls = [picture]
    fake_win.render()
    assert picture.rendered_width == 100
    with PIL.Image.open(IMAGE_EXAMPLE) as image:
        expected = round(image.height * 100 / image.width)
    assert picture.rendered_height == expected
    fake_win.check()


def test_image_contained_in_box(fake_win):
    # keep_ratio + both dimensions: fit inside the box (object-fit: contain).
    picture = Picture(IMAGE_EXAMPLE, width=100, height=100, keep_ratio=True)
    fake_win.controls = [picture]
    fake_win.render()
    with PIL.Image.open(IMAGE_EXAMPLE) as image:
        ratio = min(100 / image.width, 100 / image.height)
        expected = (round(image.width * ratio), round(image.height * ratio))
    assert (picture.rendered_width, picture.rendered_height) == expected
    assert picture.rendered_width == 100 or picture.rendered_height == 100
    fake_win.check()
