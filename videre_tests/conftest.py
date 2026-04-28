import io

import pytest

from videre.testing.fake_user import FakeUser
from videre.testing.step_window import StepWindow
from videre.testing.utils import LD, HD, SD


@pytest.fixture
def _image_testing(image_regression):
    def check(image: io.BytesIO, **kwargs):
        image_regression.check(image.getvalue(), diff_threshold=0, **kwargs)

    return check


@pytest.fixture
def fake_user():
    yield FakeUser


@pytest.fixture
def win_HD():
    return HD


@pytest.fixture
def win_SD():
    return SD


RESOLUTION_FIXTURES = ("win_HD", "win_SD")


@pytest.fixture
def fake_win(_image_testing, request):
    params = next(
        (
            request.getfixturevalue(f)
            for f in RESOLUTION_FIXTURES
            if f in request.fixturenames
        ),
        LD,
    )

    class FakeWindow(StepWindow):
        __slots__ = ()

        def check(self, basename: str | None = None):
            kwargs = {}
            if basename:
                kwargs["basename"] = f"{request.node.name}_{basename}"
            _image_testing(self.snapshot(), **kwargs)

    win_params = request.node.get_closest_marker("win_params")
    win_params = {**params, **(win_params.args[0] if win_params else {})}
    print(win_params)
    with FakeWindow(**win_params) as window:
        yield window


@pytest.fixture
def snap_win(fake_win):
    yield fake_win
    fake_win.check()
