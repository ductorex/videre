"""DPI opt-in: the videre.core.dpi helpers, the AbstractWindowing.scale_factor
contract, the Window text funnel and the logical-window plumbing.

The real display scale is machine-dependent, so every scaling assertion uses a
FORCED `_scale_factor` (or monkeypatched dpi helpers) — never the actual OS
value. The helpers themselves are only checked for type and graceful behavior.

Widgets and layout stay logical whatever the scale — that is the point of the
design: the scale is applied at record time by `window.drawing` (exercised in
tests/pygame_tests/test_scaled_drawing.py and the ×2 / ×1.5 snapshots of
tests/widget_tests/test_dpi_text.py) and by the text funnel (below).
"""

import PIL.Image
import pygame

import videre
import videre.core.pygame_backend.backend as pygame_backend
from videre.core.dpi import (
    declare_dpi_awareness,
    system_scale_factor,
    to_device,
    to_device_ceil,
    to_device_floor,
    to_logical,
    to_logical_ceil,
    to_logical_floor,
    to_logical_slot,
)
from videre.core.drawer import Drawer
from videre.core.drawing import Drawing, ScaledDrawing
from videre.core.events import MouseButton, MouseButtonDownEvent, MouseEvent
from videre.core.text_rendering.document import TextDocument
from videre.core.text_rendering.rendering.layout import RenderedText
from videre.fonts.font_utils import FontUtils
from videre.fonts.provider import FontProvider
from videre.testing.step_window import StepWindow
from videre.widgets.widget import Widget


def test_dpi_helpers_are_safe_to_call():
    # Windows: declares process awareness (idempotent for this test process).
    # Elsewhere: no-op returning False. Either way: no crash, right types.
    assert isinstance(declare_dpi_awareness(), bool)
    scale = system_scale_factor()
    assert isinstance(scale, float)
    assert scale >= 1.0  # 100% is the OS minimum; 1.0 wherever unreadable


def test_rounding_vocabulary():
    # Three roundings × two directions (see videre/core/dpi.py): no suffix =
    # nearest pixel (half-up), _ceil = cover, _floor = stay inside.
    assert to_device(3, 1.5) == 5  # 4.5 rounds half-up
    assert to_device(2, 1.5) == 3
    assert to_device_ceil(3, 1.5) == 5  # ceil(4.5)
    assert to_device_ceil(2, 1.5) == 3
    assert to_device_floor(3, 1.5) == 4  # floor(4.5)
    assert to_logical(5, 1.5) == 3  # 3.33 -> nearest
    assert to_logical(4, 1.5) == 3  # 2.67 -> nearest
    assert to_logical_ceil(5, 1.5) == 4  # ceil(3.33)
    assert to_logical_floor(5, 1.5) == 3  # floor(3.33)
    assert to_logical_floor(4, 1.5) == 2  # floor(2.67)
    for value in (0, 1, 7, 240):
        for helper in (
            to_device,
            to_device_ceil,
            to_device_floor,
            to_logical,
            to_logical_ceil,
            to_logical_floor,
            to_logical_slot,
        ):
            assert helper(value, 1.0) == value


def test_rounding_vocabulary_negative_values():
    # math.floor semantics, not int() truncation toward zero: a pointer
    # dragged above/left of the window and a child blitted at a negative
    # position must stay on the same grid as positive values.
    assert to_device(-3, 1.5) == -4  # -4.5 half-up (toward +inf) = -4
    assert to_device(-7, 1.3) == -9  # -9.1 nearest; int() truncation gave -8
    assert to_logical_floor(-1, 1.5) == -1  # int() truncation gave 0
    assert to_logical_floor(-5, 1.5) == -4  # exact -10/3 floors to -4
    assert to_logical_ceil(-5, 1.5) == -3
    assert to_logical_slot(-1, 1.5) == -1  # device -1 is in slot [-1, 0)


def test_rounding_vocabulary_float_guard():
    # Float representation error must never turn into a whole spurious pixel.
    assert to_logical_floor(33, 1.1) == 30  # 33/1.1 == 29.999999999999996
    assert to_device_ceil(50, 1.1) == 55  # 50*1.1 == 55.00000000000001
    assert to_device_floor(5, 1.4) == 7  # 5*1.4 == 6.999999999999999


def test_pointer_slot_inverse():
    # Rendering puts logical pixel l on the device slot
    # [to_device(l), to_device(l + 1)); to_logical_slot is its exact
    # inverse. A plain floor is NOT: at 125% it lands one pixel short on a
    # quarter of all coordinates (e.g. device 1 -> floor(0.8) = 0).
    assert to_logical_slot(1, 1.25) == 1
    assert to_logical_floor(1, 1.25) == 0  # the wrong answer floor gives
    for scale in (1.25, 1.5, 1.75, 2.0):
        for logical in range(0, 200):
            lo, hi = to_device(logical, scale), to_device(logical + 1, scale)
            for device in range(lo, hi):
                assert to_logical_slot(device, scale) == logical, (device, scale)


def test_scale_factor_defaults_to_one():
    with StepWindow() as win:
        assert win._windowing.scale_factor == 1.0
        assert win.scale_factor == 1.0
        # At 1.0 the identity Drawing is used and TextRendering hands out raw
        # documents — no scaling arithmetic or adapter anywhere on the path.
        assert type(win.drawing) is Drawing
        rendering = win.text_rendering()
        assert rendering._scale == 1.0
        assert type(rendering.document("x")) is TextDocument


def test_forced_scale_goes_through_text_funnel():
    with StepWindow() as win:
        win._windowing._scale_factor = 2.0
        # TextRendering scales every font size itself, at the source: the
        # pipeline below it is entirely device. Default and custom alike.
        rendering = win.text_rendering()
        assert rendering._scale == 2.0
        assert rendering._size == 28  # default 14 x 2
        assert win.text_rendering(size=20)._size == 40
        # Widget-facing metrics stay logical: they feed back into layout.
        assert win.symbol_size == int(round(14 * 1.625))
        assert win.font_height == FontHeightProbe.get(1.0)


class FontHeightProbe:
    """font_height for a given forced scale, on a fresh window."""

    @staticmethod
    def get(scale: float) -> int:
        with StepWindow() as win:
            win._windowing._scale_factor = scale
            return win.font_height


def test_scaled_text_keeps_widget_metrics_logical():
    with StepWindow() as win:
        win._windowing._scale_factor = 2.0
        result, drawer = win.text_rendering().render_text("Hello, world")
        # The drawer holds device-resolution glyphs but presents a logical box.
        device_w, device_h = drawer.device_width, drawer.device_height
        assert device_w > 0 and device_h > 0
        assert drawer.scale == 2.0
        assert drawer.get_width() == -(-device_w // 2)  # ceil(device / scale)
        assert drawer.get_height() == -(-device_h // 2)
        # The result carries both units itself, like a Drawer: stored fields
        # are device, the widget-facing contract is logical.
        assert isinstance(result, RenderedText)
        assert result.scale == 2.0
        assert result.get_width() == -(-result.width // 2)
        assert result.get_height() == -(-result.height // 2)


def test_mouse_events_round_trip_at_forced_scale():
    # FakeUser posts device pixels (like the OS); the windowing converts back
    # to logical on dispatch. Forcing the scale after layout keeps widget
    # positions logical, so a hit landing home proves the round-trip.
    clicked = []
    with StepWindow() as win:
        button = videre.Button("Hi", on_click=lambda b: clicked.append(b))
        win.controls = [button]
        win.render()
        win._windowing._scale_factor = 2.0
        win.user.click(button)
        win.render()
    assert clicked == [button]


def test_dpi_aware_keeps_logical_size_and_opens_device_screen(monkeypatch):
    # The platform plumbing is monkeypatched so the test is deterministic on
    # any machine: declaration "succeeds", the system reports 150%.
    monkeypatch.setattr(pygame_backend, "declare_dpi_awareness", lambda: True)
    monkeypatch.setattr(pygame_backend, "system_scale_factor", lambda: 1.5)
    with StepWindow(width=320, height=240, dpi_aware=True) as win:
        assert win.scale_factor == 1.5
        assert isinstance(win.drawing, ScaledDrawing)
        # Layout, wprops and events stay logical; only the OS buffer (and the
        # commands recorded through `window.drawing`) are device-sized.
        assert win.width == 320 and win.height == 240
        win.render()
        with PIL.Image.open(win.screenshot()) as screen:
            assert screen.size == (480, 360)


def test_dpi_aware_without_platform_scale_changes_nothing(monkeypatch):
    # Declaration fails (e.g. non-Windows): no scaling, current behavior.
    monkeypatch.setattr(pygame_backend, "declare_dpi_awareness", lambda: False)
    with StepWindow(width=320, height=240, dpi_aware=True) as win:
        assert win.scale_factor == 1.0
        assert win.width == 320 and win.height == 240


class _ClickProbe(Widget):
    """Full-window widget recording the logical mouse-down coordinates."""

    __slots__ = ("received",)

    def __init__(self):
        super().__init__()
        self.received: list[tuple[int, int]] = []

    def draw(self, window, width=None, height=None) -> Drawer:
        return window.drawing.new_surface(width or 0, height or 0)

    def handle_mouse_down(self, event: MouseEvent) -> Widget:
        self.received.append((event.x, event.y))
        return self


def test_pointer_maps_to_rendered_slot_at_125_percent():
    # End to end: a device pixel must be dispatched to the logical pixel the
    # renderer painted there. At 125%, logical x=41 owns device slot [51, 53)
    # — a plain floor would send device 51 to x=40 (one pixel short), i.e. a
    # click on a widget's first device pixel would reach its neighbour.
    probe = _ClickProbe()
    with StepWindow() as win:
        win.controls = [probe]
        win.render()
        win._windowing._scale_factor = 1.25
        assert to_device(41, 1.25) == 51  # first device pixel of slot 41
        win._windowing.post_event(
            MouseButtonDownEvent(x=51, y=51, buttons=(MouseButton.BUTTON_LEFT,))
        )
        win.render()
    assert probe.received == [(41, 41)]


def test_os_resize_covers_arbitrary_device_size(monkeypatch):
    # An OS resize grants ANY device size — including one that is not
    # ceil(logical x scale): 484 at 150% gives logical floor(322.67) = 322,
    # and ceil(322 x 1.5) = 483 < 484. The root drawer must be sized on the
    # real buffer (Drawing.screen_surface) and a full-width child must keep
    # its origin (not be shifted right by edge anchoring); the spare device
    # column is window background, like any DPI-aware toolkit.
    monkeypatch.setattr(pygame_backend, "declare_dpi_awareness", lambda: True)
    monkeypatch.setattr(pygame_backend, "system_scale_factor", lambda: 1.5)
    with StepWindow(width=320, height=240, dpi_aware=True) as win:
        win.controls = [
            videre.Container(videre.Text("x"), background_color=videre.Colors.red)
        ]
        win.render()
        windowing = win._windowing
        flags = pygame.RESIZABLE | pygame.HIDDEN
        windowing._screen = pygame.display.set_mode((484, 363), flags=flags)
        windowing._screen_rendering = pygame_backend.PygameRendering(windowing._screen)
        windowing._resize_window(pygame.event.Event(pygame.WINDOWRESIZED, x=484, y=363))
        win.render()
        assert (win.width, win.height) == (322, 242)
        assert (windowing.device_width, windowing.device_height) == (484, 363)
        with PIL.Image.open(win.screenshot()) as screen:
            assert screen.size == (484, 363)
            rgb = screen.convert("RGB")
            assert rgb.getpixel((0, 100)) == (255, 0, 0)  # origin kept
            assert rgb.getpixel((482, 100)) == (255, 0, 0)  # content covers ceil
            assert rgb.getpixel((483, 100)) == (255, 255, 255)  # background
            assert rgb.getpixel((200, 362)) == (255, 0, 0)  # height is exact


def test_font_height_covers_scaled_text():
    # font metrics are not linear in size: at 150% the rasterized line is
    # taller than font_height x 1.5 would suggest (e.g. 29 device for a
    # 21px font vs sized_height(14) = 19 logical). font_height must be
    # measured on the device font size and ceil'd back, so a reservation
    # always covers the real text.
    with StepWindow() as win:
        win._windowing._scale_factor = 1.5
        _, path = FontProvider().get_font_info(" ")
        device = FontUtils(path, to_device(14, 1.5)).sized_height
        assert device is not None
        assert win.font_height == to_logical_ceil(device, 1.5)
