"""`TextDocument` parity: `document.render(width)` must equal the one-shot
`render_text(text, width)`. The document only caches the text-only shape and
replays the width-dependent half, so the painted surface and the caret contract
must be identical. Also checks the document exposes `text` / `edit_units`.
"""

import numpy as np
import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha, rasterize
from videre.colors import Color
from videre.core.constants import TextAlign
from videre.core.text_editing import segment_edit_units
from videre.core.text_rendering.document import TextDocument
from videre.core.text_rendering.rasterizer import GlyphRasterizer
from videre.core.text_rendering.render import render_text
from videre.core.text_rendering.shaper import Shaper

BLACK = Color(0, 0, 0)
ARAB = "أبج"


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


@pytest.fixture
def shaper() -> Shaper:
    return Shaper()


@pytest.fixture
def rasterizer() -> GlyphRasterizer:
    return GlyphRasterizer()


@pytest.mark.parametrize(
    "text, width, wrap_words, align",
    [
        ("hello world", None, False, None),
        ("hello world foo bar baz", 80, True, None),
        ("hello world foo bar baz", 80, False, None),
        (ARAB + " hello", None, False, None),
        ("a  b   c", 60, True, None),
        ("right", 120, False, TextAlign.RIGHT),
        ("line1\nline2\nline3", None, False, None),
        ("", None, False, None),
    ],
)
def test_document_render_matches_render_text(
    fake_win, shaper, rasterizer, text, width, wrap_words, align
):
    rt_result, rt_surface = render_text(
        text,
        rasterizer=rasterizer,
        shaper=shaper,
        size=16,
        color=BLACK,
        width=width,
        wrap_words=wrap_words,
        align=align,
    )
    doc = TextDocument(text, shaper=shaper, rasterizer=rasterizer, size=16)
    doc_result, doc_surface = doc.render(
        width, color=BLACK, wrap_words=wrap_words, align=align
    )

    assert (doc_result.get_width(), doc_result.get_height()) == (
        rt_result.get_width(),
        rt_result.get_height(),
    )
    assert doc_result.total_visual_count() == rt_result.total_visual_count()
    assert np.array_equal(
        pixels_alpha(rasterize(fake_win.renderer, doc_surface)),
        pixels_alpha(rasterize(fake_win.renderer, rt_surface)),
    )


@pytest.mark.parametrize(
    "text, width, wrap_words, align",
    [
        ("hello world", None, False, None),
        ("hello world foo bar baz", 80, True, None),
        ("hello world foo bar baz", 80, False, None),
        (ARAB + " hello", None, False, None),
        ("a  b   c", 60, True, None),
        ("right", 120, False, TextAlign.RIGHT),
        ("line1\nline2\nline3", None, False, None),
        ("", None, False, None),
    ],
)
def test_document_layout_matches_render(
    fake_win, shaper, rasterizer, text, width, wrap_words, align
):
    """`layout()` returns the SAME caret/hit-test contract as `render()[0]` —
    and from the shared per-width cache, so it is the very same object (no second
    wrap/reorder), without painting a surface."""
    doc = TextDocument(text, shaper=shaper, rasterizer=rasterizer, size=16)
    laid = doc.layout(width, wrap_words=wrap_words, align=align)
    rendered, _surface = doc.render(
        width, color=BLACK, wrap_words=wrap_words, align=align
    )
    assert laid is rendered  # shared memo: same key → same RenderedText object
    assert (laid.get_width(), laid.get_height()) == (
        rendered.get_width(),
        rendered.get_height(),
    )
    assert laid.total_visual_count() == rendered.total_visual_count()


def test_document_layout_cache_keyed_on_layout_params(fake_win, shaper, rasterizer):
    """The shared layout cache keys on (width, wrap, policy, align): the same key
    reuses the instance, a different width recomputes, and `render` at the cached
    key paints from `layout`'s instance (a single wrap per width)."""
    doc = TextDocument(
        "hello world foo bar baz", shaper=shaper, rasterizer=rasterizer, size=16
    )
    wide = doc.layout(200, wrap_words=True)
    assert doc.layout(200, wrap_words=True) is wide  # same key → cached
    narrow = doc.layout(60, wrap_words=True)
    assert narrow is not wide  # different width → recomputed
    rendered, _ = doc.render(60, wrap_words=True)
    assert rendered is narrow  # render reuses the cached layout


def test_document_exposes_text_and_edit_units(fake_win, shaper, rasterizer):
    text = "café " + ARAB
    doc = TextDocument(text, shaper=shaper, rasterizer=rasterizer, size=16)
    assert doc.text == text
    assert doc.edit_units == segment_edit_units(text)


def test_caret_items_are_edit_units_not_codepoints(fake_win, shaper, rasterizer):
    """C3 lock: a multi-codepoint grapheme (base + combining mark) is ONE caret
    item. Total = graphemes (not codepoints); selecting that item covers BOTH
    its codepoints; a source position inside it maps to a boundary."""
    text = (
        "ae" + chr(0x301) + "b"
    )  # a | e + combining acute | b: 4 codepoints, 3 graphemes
    doc = TextDocument(text, shaper=shaper, rasterizer=rasterizer, size=16)
    rendered, _ = doc.render()
    assert len(doc.edit_units) == 3  # the document agrees: 3 graphemes
    assert rendered.total_visual_count() == 3  # caret too: not 4 codepoints
    # The middle visual item (the é) covers BOTH its codepoints.
    assert rendered.visual_range_to_source_set(1, 2) == frozenset({1, 2})
    # A source position between e and its accent maps to an edit-unit boundary.
    assert rendered.visual_state(2).pos in (1, 3)
