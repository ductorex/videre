"""Adapter exposing the legacy `PygameTextRendering` call shape on top
of `ShapedTextRendering`.

Lets us substitute the shaped pipeline for the legacy one in
`Window.text_rendering()` (gated by an environment variable) without
changing every widget call site. `render_text()` returns the same
two-part contract as the legacy renderer: a text-layout result for
caret / hit-testing helpers, and a pygame-rendered result carrying the
bitmap surface.
"""

import os

import pygame

from videre.core.constants import TextAlign
from videre.core.pygame_utils import PygameRendered
from videre.core.shaping.layout import ShapedRenderedText
from videre.core.shaping.text_rendering import ShapedTextRendering


def _color_to_rgb(color) -> tuple[int, ...]:
    """Map the legacy `Color | None` into the 3- or 4-tuple shape the
    shaped pipeline expects. `None` -> black, single ints -> grey."""
    if color is None:
        return (0, 0, 0)
    if isinstance(color, (tuple, list)):
        return tuple(int(c) for c in color)
    if isinstance(color, int):
        return (color, color, color)
    # Last resort: rely on pygame's `Color` having `.r/.g/.b/.a`.
    return (
        int(color.r),
        int(color.g),
        int(color.b),
        int(color.a) if hasattr(color, "a") else 255,
    )


class ShapedTextRenderingLegacyAdapter:
    """Mirrors the constructor / `render_text` / `render_char`
    signatures of `PygameTextRendering`, but routes through
    `ShapedTextRendering` internally."""

    __slots__ = ("_inner",)

    def __init__(
        self,
        fonts,
        size: int | float = 0,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int | None = None,
        subpixel: bool = False,
    ) -> None:
        # Mirror legacy default-resolution: `size=0` falls back to the
        # FontProvider's default; `height_delta=None` resolves to 2
        # (matches what `PygameTextRendering` does in its `__init__`).
        if not size:
            size = fonts.size
        if height_delta is None:
            height_delta = 2
        self._inner = ShapedTextRendering(
            size=int(size),
            bold=bool(strong),
            italic=bool(italic),
            underline=bool(underline),
            height_delta=int(height_delta),
            subpixel=subpixel,
        )

    def render_char(self, c: str, color=None) -> pygame.Surface:
        return self._inner.render_char(c, _color_to_rgb(color))

    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        compact: bool = True,
        color=None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[ShapedRenderedText, PygameRendered]:
        # `compact` in legacy was per-call; in the shaped pipeline
        # it lives on the constructor (default True). The widgets
        # never pass `compact=False`, so we silently use the
        # constructor's value. If a future caller relies on a
        # per-call override, the adapter will need to rebuild
        # `_inner` here.
        del compact
        return self._inner.render_text(
            text,
            _color_to_rgb(color),
            width=width,
            wrap_words=wrap_words,
            align=align,
            selection=selection,
        )


def use_shaped_rendering() -> bool:
    """True when `Window.text_rendering()` should swap in the shaped
    pipeline. Driven by the `VIDERE_USE_SHAPED_RENDERING` env var so
    a single test run can toggle between legacy and shaped without
    touching the codebase."""
    return bool(os.environ.get("VIDERE_USE_SHAPED_RENDERING"))


def use_shaped_subpixel() -> bool:
    return bool(os.environ.get("VIDERE_USE_SHAPED_SUBPIXEL"))
