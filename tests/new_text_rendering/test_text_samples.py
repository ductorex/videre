"""Image-regression snapshots of the shaped renderer over the
`videre.testing` sample corpus.

These exercise `ShapedTextRendering` **standalone** — instantiated directly
on the backend, not through the `Text` widget (which still routes to the
legacy `PygameTextRendering`). The point is to pin the *new* shaping stack
end to end (segmentation -> HarfBuzz shaping -> wrap -> bidi reorder ->
rasterization) against the hard cases the corpus collects: mixed
French/Arabic bidi, CJK without spaces, Hebrew with nikkud, Devanagari
reordering, Thai line-breaking, emoji (ZWJ / flags / skin tones), Latin
ligatures, and the `\\r` / `\\n` / `\\r\\n` line variants.

NB: the baselines freeze the renderer's **current** output. The first run
generates the `.png` files and fails; a second run passes. Before trusting
a freshly-generated baseline, look at the image — a regression test only
guarantees "no change since this snapshot", so a wrong-but-frozen render
would silently lock in a bug. Render is pixel-exact (`diff_threshold=0`),
so baselines are platform / FreeType-version specific.
"""

import io

import pygame
import pygame.freetype
import pytest

from videre.colors import Color
from videre.core.pygame_backend.definitions import PygameRendering
from videre.core.rendering_result import Rendering
from videre.core.shaping import ShapedTextRendering
from videre.testing.utils import LOREM_IPSUM, TEXT_SAMPLES

# Rendering config shared by every snapshot. A fixed width forces wrapping
# so the long samples produce a readable block instead of one enormous
# single line; `wrap_words=True` breaks on word boundaries for spaced
# scripts and falls back to cluster breaks for the space-less ones
# (CJK / Thai). Kept as module constants so the whole corpus is easy to
# re-render at a different size / width.
_SIZE = 20
_WIDTH = 600

# `lorem_ipsum` is exported separately from the `TEXT_SAMPLES` dict; fold it
# in so the corpus is covered by one parametrized test.
_SAMPLES: dict[str, str] = {"lorem_ipsum": LOREM_IPSUM, **TEXT_SAMPLES}

# Turn the shaper's swallowed callback exceptions into hard failures.
# HarfBuzz calls our font-funcs from C, so a Python exception there becomes
# an "unraisable" warning instead of propagating — a bug like the
# script/font mismatch that probed hundreds of absent Arabic glyphs would
# otherwise render subtly wrong yet pass silently.
pytestmark = pytest.mark.filterwarnings(
    "error::pytest.PytestUnraisableExceptionWarning"
)


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


def _png(rendering: Rendering) -> bytes:
    """Serialize a rendered surface to PNG bytes for `image_regression`.

    These tests are already pygame-coupled (they init `pygame.freetype`),
    so unwrapping the backend's `PygameRendering` to its `pygame.Surface`
    is acceptable here; `pygame.image.save` mirrors what the backend's
    `screenshot()` does for the display.
    """
    assert isinstance(rendering, PygameRendering)
    buffer = io.BytesIO()
    pygame.image.save(rendering.surface, buffer, "out.png")
    return buffer.getvalue()


@pytest.mark.parametrize("name", sorted(_SAMPLES))
def test_text_sample_renders_to_snapshot(fake_win, image_regression, name: str) -> None:
    _, surface = ShapedTextRendering(fake_win.backend, size=_SIZE).render_text(
        _SAMPLES[name], color=Color(0, 0, 0), width=_WIDTH, wrap_words=True
    )
    image_regression.check(_png(surface), diff_threshold=0)


def test_line_endings_render_identically(fake_win) -> None:
    """`\\n`, `\\r`, `\\r\\n` and a malformed mix all collapse to the same
    line breaks, so the four `lines_*` samples must render **byte-for-byte
    identically**. A stronger, platform-independent invariant than the
    per-sample snapshots (which only assert "unchanged since baseline").
    """
    keys = ["lines_linux", "lines_mac", "lines_windows", "lines_malformed"]
    renders = {
        k: _png(
            ShapedTextRendering(fake_win.backend, size=_SIZE).render_text(
                TEXT_SAMPLES[k], color=Color(0, 0, 0), width=_WIDTH, wrap_words=True
            )[1]
        )
        for k in keys
    }
    reference = renders["lines_linux"]
    for k, data in renders.items():
        assert data == reference, f"{k} renders differently from lines_linux"
