import io

import pytest

from videre.core.pygame_backend.backend import PygameBackend
from videre.core.shaping import ShapedTextRendering


@pytest.fixture
def _image_testing(image_regression):
    """Override the root fixture so a multi-snapshot test surfaces ALL diverging
    snapshots in one run instead of stopping at the first.

    Every test collected here renders via the shaped pipeline (`_force_shaped`)
    and many take several snapshots (the mirrored `test_cursor`, the bidi
    TextInput tests). Batching the divergences — collect, re-raise together at
    teardown — means each run writes every `.obtained.png` and lists all
    mismatches, no re-run-per-snapshot dance. Only `AssertionError` (a genuine
    pixel divergence) is batched; baseline creation raises `pytest.fail`
    (`Failed`) and must not be swallowed — generate baselines in one shot with
    `uv run pytest ... --regen-all` instead.
    """
    errors: list[AssertionError] = []

    def check(image: io.BytesIO, **kwargs):
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
