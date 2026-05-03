import io

import pytest

from videre.testing.fake_user import FakeUser
from videre.testing.step_window import StepWindow
from videre.testing.utils import HD, LD, SD


@pytest.fixture
def _image_testing(image_regression):
    """Per-call image-regression check.

    In normal mode, each `check()` raises immediately on a mismatch
    (the test stops at the first failing snapshot — standard
    pytest-regressions behavior).

    In `VIDERE_USE_SHAPED_RENDERING` mode, failures are collected silently and re-raised
    at teardown. This lets a single test that calls `check()` several
    times — for example `test_cursor` taking snapshots after each
    keypress — produce one `*.obtained.png` per snapshot, instead of
    stopping at the first one and leaving later snapshots unrendered.
    """

    errors: list[AssertionError] = []

    def check(image: io.BytesIO, **kwargs):
        from videre.core.shaping.legacy_adapter import use_shaped_rendering

        if not use_shaped_rendering():
            image_regression.check(image.getvalue(), diff_threshold=0, **kwargs)
            return
        try:
            image_regression.check(image.getvalue(), diff_threshold=0, **kwargs)
        except AssertionError as e:
            errors.append(e)

    yield check
    if errors:
        raise AssertionError(
            f"{len(errors)} snapshot(s) diverged in this test:\n"
            + "\n".join(str(e) for e in errors)
        )


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
