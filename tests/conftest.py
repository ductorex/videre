import io
from typing import Callable, Iterator

import pytest

from videre.testing.step_window import StepWindow
from videre.testing.utils import LD

ImageCheck = Callable[..., None]


class FakeWindow(StepWindow):
    __slots__ = ("_image_check", "_node_name")

    def __init__(self, image_check: ImageCheck, node_name: str, **kwargs):
        super().__init__(**kwargs)
        self._image_check = image_check
        self._node_name = node_name

    def check(self, basename: str | None = None):
        kwargs = {}
        if basename:
            kwargs["basename"] = f"{self._node_name}_{basename}"
        self.render()
        self._image_check(self.screenshot(), **kwargs)


@pytest.fixture
def _image_testing(image_regression) -> ImageCheck:
    def check(image: io.BytesIO, **kwargs):
        image_regression.check(image.getvalue(), diff_threshold=0, **kwargs)

    return check


@pytest.fixture
def fake_win(_image_testing, request) -> Iterator[FakeWindow]:
    win_params_marker = request.node.get_closest_marker("win_params")
    user_params = win_params_marker.args[0] if win_params_marker else {}
    win_params = {**LD, **user_params}
    with FakeWindow(
        image_check=_image_testing, node_name=request.node.name, **win_params
    ) as window:
        yield window


@pytest.fixture
def snap_win(fake_win):
    yield fake_win
    fake_win.check()
