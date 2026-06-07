"""Pixel-compare each shaped-mirror snapshot against its `widget_tests` baseline.

One parametrized case per snapshot (`<module>/<name>.png`, the union of both
trees). A case PASSES iff the two PNGs are pixel-identical, else FAILS with a
divergence metric. The count of failures is therefore the count of snapshots
where the shaped renderer diverges from the legacy pygame renderer.

Run deliberately (most text snapshots are expected to diverge — that is what we
are measuring):

    uv run pytest tests/new_text_rendering/on_videre/test_snapshots.py -q
"""

import pathlib

import numpy as np
import pytest
from PIL import Image

_HERE = pathlib.Path(__file__).parent  # tests/new_text_rendering/on_videre
_WIDGET = _HERE.parents[1] / "widget_tests"  # tests/widget_tests


def _snapshots():
    rels = set()
    for root in (_WIDGET, _HERE):
        for png in root.rglob("*.png"):
            rel = png.relative_to(root).as_posix()
            if rel.startswith("_diffs/"):  # make_diffs.py output, not a snapshot
                continue
            rels.add(rel)
    return sorted(rels)


def _load(path):
    return np.asarray(Image.open(path).convert("RGBA"))


@pytest.mark.parametrize("rel", _snapshots())
def test_shaped_matches_legacy(rel):
    legacy, shaped = _WIDGET / rel, _HERE / rel
    assert legacy.exists(), f"baseline absente de widget_tests: {rel}"
    assert shaped.exists(), f"snapshot absent de on_videre: {rel}"

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
