import io
import pathlib

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


def test_testing_image(image_testing):
    """Just check if testing image is correctly saved."""
    image_testing(SrcProvider().file_like())


@pytest.mark.parametrize("src", ["string", "path", "bytes", "bytearray", "file_like"])
def test_image(src, fake_win):
    src_provider = SrcProvider()
    fake_win.controls = [Picture(src=getattr(src_provider, src)())]
    fake_win.check()


@pytest.mark.parametrize("alt", [None, "Bad image!"])
def test_bad_image(alt, fake_win):
    fake_win.controls = [Picture("", alt=alt)]
    fake_win.check()
