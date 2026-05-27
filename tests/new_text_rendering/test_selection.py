"""Tests for the `selection` parameter of `ShapedTextRendering.render_text`.

The selection is expressed in logical source positions (matching the
printable-source convention) and produces a translucent blue rectangle
behind glyphs whose source positions fall in the half-open range
``[start, end)``. Pixel inspection compares the selection-on render
against the selection-off render to identify the highlighted band.
"""

import numpy as np
import pygame
import pygame.freetype
import pytest

from tests.common import pixels_alpha, pixels_blue, pixels_green, pixels_red
from videre.colors import Color
from videre.core.rendering_result import Rendering
from videre.core.shaping import ShapedTextRendering


@pytest.fixture(scope="module", autouse=True)
def _init_pygame() -> None:
    pygame.freetype.init()


def _highlight_x_range(s_sel: Rendering, s_no: Rendering) -> tuple[int, int]:
    """Difference in blue channel (selection introduces blue pixels;
    text is black). Returns ``(min_col, max_col)`` of the highlighted
    band, or ``(-1, -1)`` if no highlight is present.

    `gfxdraw.box` stores premultiplied blue values around 99 on a
    SRCALPHA surface for the legacy `(100, 100, 255, 100)` color, so
    we can't simply look at `blue > 200`; instead we check the delta
    against the no-selection render where blue is 0 everywhere except
    where the highlight injects it.
    """
    arr_diff = pixels_blue(s_sel).astype(int) - pixels_blue(s_no).astype(int)
    cols = (arr_diff > 20).any(axis=1)
    nz = np.flatnonzero(cols)
    if nz.size == 0:
        return -1, -1
    return int(nz.min()), int(nz.max())


# -- Basic contract ----------------------------------------------------------


def test_selection_none_is_unchanged(fake_win) -> None:
    """Without selection, the surface must be identical to the
    no-selection render (no phantom blue tint anywhere)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello world"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_none = r.render_text(text, color=Color(0, 0, 0), selection=None)[1]
    assert pixels_alpha(s_no).shape == pixels_alpha(s_none).shape
    assert (pixels_alpha(s_no) == pixels_alpha(s_none)).all()
    assert (pixels_blue(s_no) == pixels_blue(s_none)).all()


def test_selection_empty_range_is_noop(fake_win) -> None:
    """A degenerate range `[k, k)` selects nothing."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello world"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_empty = r.render_text(text, color=Color(0, 0, 0), selection=(3, 3))[1]
    assert (pixels_blue(s_no) == pixels_blue(s_empty)).all()


def test_selection_introduces_blue_band(fake_win) -> None:
    """A non-empty selection must paint a translucent blue band."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello world"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_sel = r.render_text(text, color=Color(0, 0, 0), selection=(1, 5))[1]
    lo, hi = _highlight_x_range(s_sel, s_no)
    assert lo > 0 and hi > lo


def test_selection_keeps_glyph_color(fake_win) -> None:
    """Selection paints BEHIND glyphs: glyph pixels keep their black
    color (red and green stay 0). Alpha at antialiased edges may
    blend up slightly because the translucent selection sits below,
    but the dominant black ink must remain visible."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_sel = r.render_text(text, color=Color(0, 0, 0), selection=(0, 5))[1]
    a_no = pixels_alpha(s_no)
    # On fully-opaque glyph pixels (alpha=255), the post-selection
    # render must still have alpha=255 (no transparency injected).
    fully_opaque_no = a_no == 255
    a_sel = pixels_alpha(s_sel)
    if fully_opaque_no.any():
        assert (a_sel[fully_opaque_no] == 255).all()
    # On those same pixels, RGB must remain (~0, ~0, ~0): the glyph
    # color was black, and a translucent selection underneath should
    # not bleed through an opaque foreground.
    r_sel = pixels_red(s_sel)
    g_sel = pixels_green(s_sel)
    if fully_opaque_no.any():
        assert r_sel[fully_opaque_no].max() <= 5
        assert g_sel[fully_opaque_no].max() <= 5


# -- Position correctness ----------------------------------------------------


def test_selection_starts_after_first_char(fake_win) -> None:
    """Selecting `[1, 5)` of `Hello` highlights `ello` only — the band
    must start at `H`'s right edge, not at column 0."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_sel = r.render_text(text, color=Color(0, 0, 0), selection=(1, 5))[1]
    lo, _ = _highlight_x_range(s_sel, s_no)
    # Width of 'H' at size 16 is around 9-12 px; lo must be at least 4
    # so we're definitely past the leftmost stroke of H.
    assert lo >= 4


def test_selection_full_text_covers_everything(fake_win) -> None:
    """Selecting the whole string highlights from the first glyph to
    the last."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    n = len(text)
    s_sel = r.render_text(text, color=Color(0, 0, 0), selection=(0, n))[1]
    lo, hi = _highlight_x_range(s_sel, s_no)
    # Should reach close to the right edge.
    natural_w = s_no.get_width()
    assert lo <= 2
    assert hi >= natural_w - 4


def test_selection_spans_inter_word_space(fake_win) -> None:
    """Selecting across a word boundary fills the inter-word gap (the
    source whitespace) so the highlight is contiguous."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "Hello world"
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_sel = r.render_text(text, color=Color(0, 0, 0), selection=(0, len(text)))[1]
    diff = pixels_blue(s_sel).astype(int) - pixels_blue(s_no).astype(int)
    cols = (diff > 20).any(axis=1)
    # No "hole": the highlighted column run must be contiguous (no col
    # without highlight inside the highlighted range).
    nz = np.flatnonzero(cols)
    if nz.size:
        run_length = nz.max() - nz.min() + 1
        assert nz.size >= run_length - 2  # tolerate a couple of antialiasing slits


# -- Multi-line / wrap -------------------------------------------------------


def test_selection_across_wrapped_lines(fake_win) -> None:
    """Selection spanning a wrap break must highlight on both lines."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "alpha beta gamma delta"
    width = 80
    s_no = r.render_text(text, color=Color(0, 0, 0), width=width, wrap_words=True)[1]
    s_sel = r.render_text(
        text,
        color=Color(0, 0, 0),
        width=width,
        wrap_words=True,
        selection=(0, len(text)),
    )[1]
    diff = pixels_blue(s_sel).astype(int) - pixels_blue(s_no).astype(int)
    rows = (diff > 20).any(axis=0)
    nz_rows = np.flatnonzero(rows)
    # Selection must span more than one line vertically; a single-line
    # highlight can't exceed `line_spacing` rows, so anything taller
    # proves at least two lines are highlighted. We don't probe for a
    # gap between the two lines' bands — the bands are contiguous when
    # `ascender + descender == line_spacing` (the Noto Sans case), and
    # demanding a gap would entangle this test with font metrics.
    assert nz_rows.size > r.font_metrics.line_spacing, (
        f"selection span too short ({nz_rows.size} rows) to cover two "
        f"lines (line_spacing={r.font_metrics.line_spacing})"
    )


def test_selection_across_paragraph_break(fake_win) -> None:
    """Selecting through an explicit `\\n` highlights both paragraphs.
    The newline character itself occupies one source position; on the
    rendered surface no glyph is drawn for it (between-line space)."""
    r = ShapedTextRendering(fake_win.backend, size=16)
    text = "alpha\nbeta"
    n = len(text)
    s_no = r.render_text(text, color=Color(0, 0, 0))[1]
    s_sel = r.render_text(text, color=Color(0, 0, 0), selection=(0, n))[1]
    diff = pixels_blue(s_sel).astype(int) - pixels_blue(s_no).astype(int)
    rows = (diff > 20).any(axis=0)
    nz_rows = np.flatnonzero(rows)
    # Same intent as test_selection_across_wrapped_lines: span exceeds
    # one line's worth of rows ⇒ two lines are highlighted.
    assert nz_rows.size > r.font_metrics.line_spacing, (
        f"selection span too short ({nz_rows.size} rows) to cover two "
        f"lines (line_spacing={r.font_metrics.line_spacing})"
    )
