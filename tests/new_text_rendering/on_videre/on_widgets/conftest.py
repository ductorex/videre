"""Re-run the whole `tests/widget_tests` suite against the SHAPED text renderer.

POC harness. `pytest_collect_file` (triggered by the empty `_mirror.py`) builds
one virtual module per `tests/widget_tests/test_*.py`, anchored under this
directory so each module's image snapshots land in `on_widgets/<module>/`, while
`_force_shaped` reroutes every `text_rendering()` to `ShapedTextRendering`. No
source test file is duplicated.
"""

import importlib
import pathlib

import pytest

_SRC_PKG = "tests.widget_tests"
_SRC_MODULE = importlib.import_module(_SRC_PKG)
assert _SRC_MODULE.__file__ is not None
_SRC_DIR = pathlib.Path(_SRC_MODULE.__file__).parent


class _MirrorModule(pytest.Module):
    """A module whose nodeid / path lives under `on_widgets/` (so snapshots land
    here) but whose code is the real source module from `tests.widget_tests`."""

    def _getobj(self):
        return importlib.import_module(f"{_SRC_PKG}.{self.path.stem}")


class _MirrorFile(pytest.File):
    def collect(self):
        here = self.path.parent
        sources = sorted(_SRC_DIR.glob("test_*.py"))
        assert sources, "Cannot find widget tests"
        for src in sources:
            yield _MirrorModule.from_parent(self, path=here / src.name)


def pytest_collect_file(file_path, parent):
    if file_path.name == "_mirror.py":
        return _MirrorFile.from_parent(parent, path=file_path)
    return None
