"""Re-run the whole `tests/widget_tests` suite against the SHAPED text renderer.

POC harness. `pytest_collect_file` (triggered by the empty `_mirror.py`) builds
one virtual module per `tests/widget_tests/test_*.py`, anchored under this
directory so each module's image snapshots land in `on_videre/<module>/`, while
`_force_shaped` reroutes every `text_rendering()` to `ShapedTextRendering`. No
source test file is duplicated.
"""

import importlib

import pytest

from videre.core.pygame_backend.backend import PygameBackend
from videre.core.shaping import ShapedTextRendering

_SRC_PKG = "tests.widget_tests"


@pytest.fixture(autouse=True)
def _force_shaped(monkeypatch):
    """Make the pygame backend hand out a `ShapedTextRendering` instead of the
    legacy `PygameTextRendering`, for every Window created during these tests."""

    def shaped(
        self, size, strong=False, italic=False, underline=False, height_delta=None
    ):
        return ShapedTextRendering(
            self,
            size=size,
            bold=strong,
            italic=italic,
            underline=underline,
            height_delta=2 if height_delta is None else height_delta,
        )

    monkeypatch.setattr(PygameBackend, "text_rendering", shaped)


class _MirrorModule(pytest.Module):
    """A module whose nodeid / path lives under `on_videre/` (so snapshots land
    here) but whose code is the real source module from `tests.widget_tests`."""

    def _getobj(self):
        return importlib.import_module(f"{_SRC_PKG}.{self.path.stem}")


class _MirrorFile(pytest.File):
    def collect(self):
        here = self.path.parent  # tests/new_text_rendering/on_videre
        src_dir = self.path.parents[2] / "widget_tests"  # tests/widget_tests
        for src in sorted(src_dir.glob("test_*.py")):
            yield _MirrorModule.from_parent(self, path=here / src.name)


def pytest_collect_file(file_path, parent):
    if file_path.name == "_mirror.py":
        return _MirrorFile.from_parent(parent, path=file_path)
    return None
