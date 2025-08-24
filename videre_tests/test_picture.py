import io
import pathlib

import pytest
from PIL import Image

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
        output = io.BytesIO()
        image = Image.open(self._string)
        image.save(output, format=image.format)
        return output.getvalue()

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
