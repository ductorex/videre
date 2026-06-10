"""Pixel-compare each shaped-mirror snapshot against its `widget_tests` baseline.

One parametrized case per snapshot (`<module>/<name>.png`, the union of both
trees). A case PASSES iff the two PNGs are pixel-identical, else FAILS with a
divergence metric. The count of failures is therefore the count of snapshots
where the shaped renderer diverges from the legacy pygame renderer.

Run deliberately (most text snapshots are expected to diverge — that is what we
are measuring):

    uv run pytest tests/new_text_rendering/on_videre/on_widgets/test_snapshots.py -q
"""

import importlib
import pathlib

import numpy as np
import pytest
from PIL import Image

_HERE = pathlib.Path(__file__).parent
_WIDGET_MODULE = importlib.import_module("tests.widget_tests")
assert _WIDGET_MODULE.__file__ is not None
_WIDGET = pathlib.Path(_WIDGET_MODULE.__file__).parent


def _snapshots():
    # Only mirror snapshots: those whose module is mirrored from `widget_tests`
    # (so we iterate the legacy baselines). on_widgets-only outputs — the
    # `make_diffs` `_diffs/` tree and the standalone bidi TextInput snapshots —
    # have no legacy counterpart to compare against, so they are excluded by
    # construction. A baseline present here but missing under `on_widgets/` still
    # fails (the per-test `shaped.exists()` check below).
    sources = sorted(p.relative_to(_WIDGET).as_posix() for p in _WIDGET.rglob("*.png"))
    assert sources, "Cannot find any png snapshots"
    return sources


def _load(path):
    return np.asarray(Image.open(path).convert("RGBA"))


@pytest.mark.parametrize("rel", _snapshots())
def test_shaped_matches_legacy(rel):
    legacy, shaped = _WIDGET / rel, _HERE / rel
    assert legacy.exists(), f"baseline absente de widget_tests: {rel}"
    assert shaped.exists(), f"snapshot absent de on_widgets: {rel}"

    a, b = _load(legacy), _load(shaped)
    if a.shape != b.shape:
        pytest.fail(f"taille differente: widget_tests={a.shape} vs on_videre={b.shape}")

    diff = np.any(a != b, axis=-1)
    n_diff = int(diff.sum())
    if n_diff:
        total = int(diff.size)
        max_delta = int(np.abs(a.astype(int) - b.astype(int)).max())
        pytest.fail(
            f"{n_diff}/{total} pixels differents ({100 * n_diff / total:.2f}%), "
            f"ecart max par canal={max_delta}"
        )
