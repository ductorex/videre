"""Unit tests for `crop_drawer` — the ScrollView visible-slice optimization.

Cropping turns a tall content drawer into a viewport-sized one holding only the
children that intersect the view, so the renderer never allocates/composes the
whole thing. These tests pin the command-level behavior (drop / keep+translate /
identity / recursion / generative wrap) and prove pixel equivalence with the old
"blit the whole content at the offset" approach.
"""

import pygame
import pytest

from tests.common import rasterize
from videre.colors import Colors
from videre.core.drawer import BlitArgs, Drawer, FillArgs, Position
from videre.core.drawer_crop import crop_drawer
from videre.core.drawing import Drawing, ScaledDrawing
from videre.core.pygame_backend.backend import PygameRenderer
from videre.core.pygame_backend.definitions import PygameRendering
from videre.core.rectangle import Rectangle


def _stack(n: int, *, w: int = 100, h: int = 50) -> tuple[Drawer, list[Drawer]]:
    """A vertical stack of `n` solid children, each `w`x`h`, at y = i*h."""
    parent = Drawer(w, n * h)
    children = []
    palette = [Colors.red, Colors.green, Colors.blue, Colors.yellow, Colors.black]
    for i in range(n):
        child = Drawer(w, h)
        child.fill(palette[i % len(palette)])
        parent.blit(child, Position(0, i * h))
        children.append(child)
    return parent, children


def test_crop_drops_fully_outside():
    parent, children = _stack(6)  # children at y = 0,50,100,150,200,250
    cropped = crop_drawer(parent, Rectangle(0, 90, 100, 60))  # view y in [90, 150)
    cmds = list(cropped)
    # Children [50,100) and [100,150) share rows with the view; [150,200) only
    # touches the edge (no shared row) and [0,50) is above -> both dropped.
    assert cropped.get_width() == 100 and cropped.get_height() == 60
    assert len(cmds) == 2
    assert all(isinstance(c, BlitArgs) for c in cmds)


def test_crop_translates_and_keeps_identity():
    parent, children = _stack(6)
    cropped = crop_drawer(parent, Rectangle(0, 100, 100, 50))  # exactly child #2
    cmds = list(cropped)
    assert len(cmds) == 1
    (blit,) = cmds
    assert isinstance(blit, BlitArgs)
    assert blit.position == Position(0, 0)  # y=100 -> 0
    assert blit.drawer is children[2]  # same object -> still hits the cache


def test_crop_fill_none_is_kept_whole():
    parent = Drawer(100, 300)
    parent.fill(Colors.red)  # FillArgs(rectangle=None) -> fills whole drawer
    cropped = crop_drawer(parent, Rectangle(0, 100, 100, 50))
    cmds = list(cropped)
    assert len(cmds) == 1
    assert isinstance(cmds[0], FillArgs) and cmds[0].rectangle is None


def test_crop_translates_fill_rect():
    parent = Drawer(100, 300)
    parent.fill(Colors.red, Rectangle(0, 100, 100, 50))
    cropped = crop_drawer(parent, Rectangle(0, 90, 100, 60))
    (fill,) = list(cropped)
    assert isinstance(fill, FillArgs)
    assert fill.rectangle == Rectangle(0, 10, 100, 50)  # shifted up by 90


def test_crop_recurses_into_oversized_child():
    # A single child taller than the view: keeping it whole would re-materialize a
    # giant surface, so it must be cropped recursively.
    inner, _ = _stack(20)  # 100 x 1000
    parent = Drawer(100, 1000)
    parent.blit(inner, Position(0, 0))
    cropped = crop_drawer(parent, Rectangle(0, 400, 100, 200))
    (blit,) = list(cropped)
    assert isinstance(blit, BlitArgs)
    assert blit.drawer is not inner  # rebuilt, not kept whole
    assert blit.drawer.get_height() == 200  # cropped to the visible band


def test_crop_small_straddling_child_is_kept_whole():
    # A child smaller than the view but crossing the edge stays whole (cache hit);
    # the renderer clips the overflow.
    parent, children = _stack(6)  # children 100x50
    cropped = crop_drawer(parent, Rectangle(0, 120, 100, 200))
    blits = [b for b in cropped if isinstance(b, BlitArgs)]
    # child #2 (100..150) straddles the top edge (120); it is kept whole, same id.
    straddler = next(b for b in blits if b.drawer is children[2])
    assert straddler.position == Position(0, -20)  # 100 - 120


def test_crop_generative_drawer_is_wrapped():
    gen = Drawer.image_from_bytes(b"", 100, 1000)  # generative: cannot be pruned
    cropped = crop_drawer(gen, Rectangle(0, 400, 100, 200))
    cmds = list(cropped)
    assert cropped.get_width() == 100 and cropped.get_height() == 200
    assert len(cmds) == 1
    (blit,) = cmds
    assert isinstance(blit, BlitArgs)
    assert blit.drawer is gen  # re-anchored whole, identity kept
    assert blit.position == Position(0, -400)


def test_crop_pixels_match_offset_blit(fake_win):
    # The strong guarantee: cropping then blitting at (0,0) is pixel-identical to
    # blitting the whole content at the scroll offset.

    parent, _ = _stack(6, w=50, h=50)  # 50 x 300
    offset_y = -120
    width, height = 50, 100

    full = Drawer(width, height)
    full.blit(parent, Position(0, offset_y))

    crop = Drawer(width, height)
    crop.blit(
        crop_drawer(parent, Rectangle(0, -offset_y, width, height)), Position(0, 0)
    )

    s_full = rasterize(fake_win.renderer, full)
    s_crop = rasterize(fake_win.renderer, crop)
    for x in range(width):
        for y in range(height):
            assert s_full.get_at((x, y)) == s_crop.get_at((x, y)), (x, y)


# Fractional display scales for the pixel-equivalence matrix. 1.25 and 1.75
# are the common Windows scales where half-up and ceil diverge on integer
# sizes (frac .25 rounds down vs up); 1.5 and 2.0 are the scales where they
# never do (frac is 0 or .5 — the blind spot of the existing DPI snapshots);
# 170/96 is a real custom-DPI ratio (Windows quantizes to integer DPIs) that
# is inexact in binary AND decimal, stressing the float guard.
SCALED_CROP_SCALES = [1.25, 1.5, 1.75, 2.0, 170 / 96]


def _scaled_content(drawing: Drawing, w: int, h: int) -> Drawer:
    """Content sensitive to every crop defect: a global fill (kept whole by
    the crop), a full-size child blit (the ScrollView shape, where a missing
    device column shows) and a smaller child at a non-zero anchor (internal
    seams)."""
    content = drawing.new_surface(w, h)
    drawing.fill(content, Colors.yellow)
    full_child = drawing.new_surface(w, h)
    drawing.fill(full_child, Colors.red)
    drawing.blit(content, full_child, (0, 0))
    if w > 2 and h > 1:
        small = drawing.new_surface(w - 2, h - 1)
        drawing.fill(small, Colors.blue)
        drawing.blit(content, small, (1, 1))
    return content


def _crop_matches_blit(drawing, renderer, content, view_w, view_h, left, top) -> bool:
    """True when cropping at (left, top) then blitting at (0, 0) — the
    ScrollView path — gives the exact pixels of blitting the whole content
    at the offset (the reference, through the same `drawing` policy)."""
    full = drawing.new_surface(view_w, view_h)
    drawing.blit(full, content, (-left, -top))
    crop = drawing.new_surface(view_w, view_h)
    drawing.blit(
        crop, crop_drawer(content, Rectangle(left, top, view_w, view_h)), (0, 0)
    )
    s_full = rasterize(renderer, full)
    s_crop = rasterize(renderer, crop)
    assert isinstance(s_full, PygameRendering)
    assert isinstance(s_crop, PygameRendering)
    assert (s_full.get_width(), s_full.get_height()) == (
        s_crop.get_width(),
        s_crop.get_height(),
    )
    return pygame.image.tobytes(s_full.surface, "RGBA") == pygame.image.tobytes(
        s_crop.surface, "RGBA"
    )


@pytest.mark.parametrize("scale", SCALED_CROP_SCALES)
def test_crop_pixels_match_offset_blit_scaled(scale):
    # The same guarantee as test_crop_pixels_match_offset_blit, at fractional
    # display scales, over the whole domain ScrollView exercises: view sizes
    # up to the content size, offsets over the clamped scroll range
    # [0, content - view] (ScrollView never overscrolls). Small-exhaustive
    # because rounding bugs live on specific residues — e.g. at 1.25 only
    # logical widths = 1 mod 4 lose a device column.
    drawing = ScaledDrawing(scale)
    renderer = PygameRenderer()
    failures = []
    checked = 0
    for content_w in range(1, 8):
        for content_h in (1, 3):
            content = _scaled_content(drawing, content_w, content_h)
            for view_w in range(1, content_w + 1):
                for view_h in sorted({1, content_h}):
                    for left in range(0, content_w - view_w + 1):
                        for top in sorted({0, content_h - view_h}):
                            checked += 1
                            if not _crop_matches_blit(
                                drawing, renderer, content, view_w, view_h, left, top
                            ):
                                failures.append(
                                    dict(
                                        content=(content_w, content_h),
                                        view=(view_w, view_h),
                                        offset=(left, top),
                                    )
                                )
    assert not failures, (
        f"{len(failures)}/{checked} crop/blit mismatches at x{scale}: {failures[:12]}"
    )


@pytest.mark.parametrize("scale", [1.0, *SCALED_CROP_SCALES])
def test_crop_clips_global_fill_to_content_bounds(scale):
    # A view larger than the content (a ScrollView showing a small child:
    # offset clamps to 0). In the reference, the content's global fill stops
    # at the content's edge — it fills the content's own surface, and the
    # blit deposits only that. The crop must not let it flood the whole
    # (larger) output surface. Scale-independent: broken at 1.0 too.
    drawing = Drawing.create(scale)
    renderer = PygameRenderer()
    failures = []
    for content_w, content_h, view_w, view_h in (
        (1, 1, 2, 1),
        (3, 3, 5, 3),
        (3, 3, 3, 7),
        (5, 1, 9, 4),
    ):
        content = _scaled_content(drawing, content_w, content_h)
        if not _crop_matches_blit(drawing, renderer, content, view_w, view_h, 0, 0):
            failures.append(dict(content=(content_w, content_h), view=(view_w, view_h)))
    assert not failures, (
        f"global fill floods past content bounds at x{scale}: {failures}"
    )
