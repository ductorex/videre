"""The record-time scaling seam: `ScaledDrawing` + the scale-free
renderer (see videre/core/drawing.py for the model)."""

from videre.colors import Colors
from videre.core.drawer import Drawer
from videre.core.drawing import Drawing, ScaledDrawing
from videre.core.pygame_backend.backend import PygameRenderer
from videre.core.rectangle import Rectangle
from videre.core.sides.border import Border


def test_scale_one_is_identity():
    drawing = Drawing.create(1.0)
    assert type(drawing) is Drawing
    d = drawing.new_surface(10, 10)
    assert (d.get_width(), d.get_height()) == (10, 10)
    assert (d.device_width, d.device_height) == (10, 10)
    drawing.box(d, Rectangle(1, 1, 3, 3), Colors.red)
    surface = PygameRenderer().materialize(d)
    assert (surface.get_width(), surface.get_height()) == (10, 10)
    assert surface.get_at((1, 1)).r == 255
    assert surface.get_at((4, 4)).a == 0


def test_box_scales_edgewise():
    drawing = ScaledDrawing(1.5)
    d = drawing.new_surface(10, 10)
    assert (d.get_width(), d.get_height()) == (10, 10)  # logical, for layouts
    drawing.box(d, Rectangle(1, 1, 3, 3), Colors.red)
    surface = PygameRenderer().materialize(d)
    # Surface: ceil(10 × 1.5) = 15; box edges: rx(1)=2 … rx(4)=6 → pixels 2..5.
    assert (surface.get_width(), surface.get_height()) == (15, 15)
    assert surface.get_at((2, 2)).r == 255
    assert surface.get_at((5, 5)).r == 255
    assert surface.get_at((1, 1)).a == 0
    assert surface.get_at((6, 6)).a == 0


def test_adjacent_boxes_stay_seamless():
    # Edge-wise scaling: two boxes sharing an edge share it after scaling too
    # (no gap, no overlap), whatever the fractional scale.
    drawing = ScaledDrawing(1.5)
    d = drawing.new_surface(10, 4)
    drawing.box(d, Rectangle(0, 0, 3, 4), Colors.red)
    drawing.box(d, Rectangle(3, 0, 3, 4), Colors.blue)
    surface = PygameRenderer().materialize(d)
    boundary = int(3 * 1.5 + 0.5)  # shared edge, scaled once
    for x in range(boundary):
        assert surface.get_at((x, 2)).r == 255
    for x in range(boundary, int(6 * 1.5 + 0.5)):
        assert surface.get_at((x, 2)).b == 255


def test_blit_scales_anchor_and_child():
    drawing = ScaledDrawing(1.5)
    child = drawing.new_surface(3, 3)
    drawing.fill(child, Colors.blue)
    parent = drawing.new_surface(10, 10)
    drawing.blit(parent, child, (3, 3))
    surface = PygameRenderer().materialize(parent)
    # Child allocates at ceil(3 × 1.5) = 5, anchored at rx(3) = 5.
    assert surface.get_at((5, 5)).b == 255
    assert surface.get_at((9, 9)).b == 255
    assert surface.get_at((4, 4)).a == 0


def test_border_scales_uniformly():
    # A 1-logical border at 1.5 must be 2 device pixels on all four sides.
    # Odd logical sizes on purpose: the parity that once gave
    # position-dependent thickness (1px here, 2px there).
    drawing = ScaledDrawing(1.5)
    d = drawing.new_surface(21, 11)
    drawing.border(d, Border.all(1))
    surface = PygameRenderer().materialize(d)
    w, h = surface.get_width(), surface.get_height()
    assert (w, h) == (32, 17)  # ceil(21 x 1.5), ceil(11 x 1.5)
    # stroke = round(1 x 1.5) = 2: the two outer rows/columns on every side.
    for x in range(w):
        for y in (0, 1, h - 2, h - 1):
            assert surface.get_at((x, y)).a == 255, (x, y)
    for y in range(h):
        for x in (0, 1, w - 2, w - 1):
            assert surface.get_at((x, y)).a == 255, (x, y)
    assert surface.get_at((5, 2)).a == 0  # just inside: transparent


def test_flush_child_keeps_its_last_row():
    # A child ending at the parent's logical edge anchors to the device
    # edge, else its ceil surface overshoots and its last row is clipped.
    # Here: child 10x3 at y=7 in a 10x10 parent at 1.5 -> parent 15 rows,
    # child 5; half-up anchor 11 would clip row 15, edge anchor 10 keeps
    # border rows 13+14.
    drawing = ScaledDrawing(1.5)
    child = drawing.new_surface(10, 3)
    drawing.border(child, Border.all(1))
    parent = drawing.new_surface(10, 10)
    drawing.blit(parent, child, (0, 7))
    surface = PygameRenderer().materialize(parent)
    assert surface.get_at((7, 13)).a == 255
    assert surface.get_at((7, 14)).a == 255  # the row half-up anchoring lost
    assert surface.get_at((7, 12)).a == 0  # inside the child: transparent


def test_screen_surface_takes_real_buffer_size():
    # After an OS resize the buffer can be any size (484 != ceil(322 x 1.5)
    # = 483). The root takes the real size; a full-width child keeps its
    # origin and the spare device column is the background's job.
    drawing = ScaledDrawing(1.5)
    root = drawing.screen_surface(322, 242, 484, 363)
    assert (root.get_width(), root.get_height()) == (322, 242)
    assert (root.device_width, root.device_height) == (484, 363)
    child = drawing.new_surface(322, 242)  # ceil -> 483 x 363
    drawing.fill(child, Colors.red)
    drawing.blit(root, child, (0, 0))
    surface = PygameRenderer().materialize(root)
    assert surface.get_at((0, 100)).r == 255  # origin kept (not shifted to 1)
    assert surface.get_at((482, 100)).r == 255
    assert surface.get_at((483, 100)).a == 0  # spare column: background's job
    assert surface.get_at((200, 362)).r == 255  # exact height: fully covered


def test_screen_surface_is_identity_at_scale_one():
    root = Drawing.create(1.0).screen_surface(320, 240, 320, 240)
    assert (root.get_width(), root.get_height()) == (320, 240)
    assert (root.device_width, root.device_height) == (320, 240)
    assert root.scale == 1.0


def test_device_content_replays_one_to_one():
    # Device-built content (e.g. rasterized glyphs) must not be scaled
    # again — only its anchor is.
    drawing = ScaledDrawing(1.5)
    content = Drawer(9, 9)
    content.fill(Colors.red)
    content.set_logical_size(6, 6, 1.5)  # ceil(9 / 1.5)
    assert (content.get_width(), content.get_height()) == (6, 6)
    assert (content.device_width, content.device_height) == (9, 9)
    parent = drawing.new_surface(20, 20)
    drawing.blit(parent, content, (2, 2))
    surface = PygameRenderer().materialize(parent)
    # Anchor rx(2) = 3; content stays 9×9 → red pixels exactly [3, 12).
    assert surface.get_at((3, 3)).r == 255
    assert surface.get_at((11, 11)).r == 255
    assert surface.get_at((12, 12)).a == 0
