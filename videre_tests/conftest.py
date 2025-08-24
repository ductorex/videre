import io

import pytest

from videre.testing.fake_user import FakeUser
from videre.testing.step_window import StepWindow
from videre.testing.utils import LD


@pytest.fixture
def image_testing(image_regression):
    def check(image: io.BytesIO, **kwargs):
        image_regression.check(image.getvalue(), diff_threshold=0, **kwargs)

    return check


@pytest.fixture
def fake_user():
    yield FakeUser


@pytest.fixture
def fake_win(image_testing, request):
    class FakeWindow(StepWindow):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def check(self, basename: str | None = None):
            kwargs = {}
            if basename:
                kwargs["basename"] = f"{request.node.name}_{basename}"
            image_testing(self.snapshot(), **kwargs)

    win_params = request.node.get_closest_marker("win_params")
    win_params = (win_params and win_params.args[0]) or LD
    with FakeWindow(**win_params) as window:
        yield window


@pytest.fixture
def snap_win(fake_win):
    yield fake_win
    fake_win.check()
