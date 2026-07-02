"""The record-time scaling policy: the `Drawing` API widgets draw through.

This module is where the display scale is applied — the ONE boundary between
the framework's logical pixels and the `Drawer`'s device commands (see
`videre.core.drawer` for the command IR itself, which is policy-free).
`Window` builds the right `Drawing` for its scale (`Drawing.create`); widget
`draw()` code records logical coordinates through it and never sees the
scale. At 1.0 the base class is the strict identity (the historic code
path); `ScaledDrawing` converts every coordinate at record time.
"""

from typing import Sequence

from PIL.Image import Image

from videre.colors import Color
from videre.core.dpi import DevicePx, LogicalPx, to_device, to_logical_ceil
from videre.core.drawer import Drawer, Position, PositionTuple, SmoothScaleArgs
from videre.core.rectangle import Rectangle
from videre.core.sides.border import Border


def _scale_rect(r: Rectangle, scale: float) -> Rectangle:
    """A logical rectangle in device pixels, scaled edge-wise: both edges
    round half-up and the size is their difference, so two rectangles sharing
    a logical edge share the device one too (no seam at any scale)."""
    left, top = to_device(r.left, scale), to_device(r.top, scale)
    return Rectangle(
        left,
        top,
        to_device(r.left + r.width, scale) - left,
        to_device(r.top + r.height, scale) - top,
    )


def logical_view(drawer: Drawer, scale: float) -> Drawer:
    """Give a device-built drawer (e.g. text rasterized at native glyph size)
    its logical view size — the inverse boundary of `new_surface`: sizes are
    derived from the device size (ceil: the logical box covers the content),
    never mutated, so re-applying on a cached drawer recomputes the same
    values and `set_logical_size` no-ops."""
    drawer.set_logical_size(
        to_logical_ceil(drawer.device_width, scale),
        to_logical_ceil(drawer.device_height, scale),
        scale,
    )
    return drawer


class Drawing:
    """The drawing API widgets record through — `window.drawing`.

    This base class is the identity (display scale 1.0): coordinates are
    recorded unchanged. On a scaled display `Window` provides a
    `ScaledDrawing` instead. Discipline: widget `draw()` code must create
    surfaces via `new_surface`, never a bare ``Drawer(...)`` — a bare
    drawer records unscaled commands, correct at 1.0 and silently wrong on
    a scaled display.
    """

    __slots__ = ()

    @staticmethod
    def create(scale: float) -> "Drawing":
        """The `Drawing` for a display scale: the identity at 1.0 (no scaling
        arithmetic anywhere on the path), a `ScaledDrawing` otherwise."""
        return Drawing() if scale == 1.0 else ScaledDrawing(scale)

    @property
    def scale(self) -> float:
        return 1.0

    def new_surface(self, width: LogicalPx, height: LogicalPx) -> Drawer:
        return Drawer(width, height)

    def screen_surface(
        self,
        width: LogicalPx,
        height: LogicalPx,
        device_width: DevicePx,
        device_height: DevicePx,
    ) -> Drawer:
        """The root drawer for the OS screen: the buffer's real device size
        with the window's logical size. The one surface whose device size is
        not derived from its logical size — an OS-resized buffer can differ
        by one pixel from ceil(logical × scale) (see
        `AbstractWindowing.device_width`). At scale 1.0 both are equal."""
        return Drawer(width, height)

    def fill(
        self, surface: Drawer, color: Color, rectangle: Rectangle | None = None
    ) -> None:
        surface.fill(color, rectangle)

    def blit(self, surface: Drawer, drawer: Drawer, position: PositionTuple) -> None:
        surface.blit(drawer, Position(*position))

    def line(
        self, surface: Drawer, color: Color, start: PositionTuple, end: PositionTuple
    ) -> None:
        surface.line(color, Position(*start), Position(*end))

    def rectangle(self, surface: Drawer, rectangle: Rectangle, color: Color) -> None:
        surface.rectangle(rectangle, color)

    def box(self, surface: Drawer, rectangle: Rectangle, color: Color) -> None:
        surface.box(rectangle, color)

    def filled_polygon(
        self, surface: Drawer, points: Sequence[PositionTuple], color: Color
    ) -> None:
        surface.filled_polygon([Position(*point) for point in points], color)

    def border(self, surface: Drawer, border: Border) -> None:
        """Record `border` along `surface`'s edges, as ordinary line/polygon
        commands computed at the surface's device size (border geometry
        derives from the surface size, so it must be built at record time —
        scaling pre-baked shapes would give position-dependent widths)."""
        _record_border(surface, border)

    def copy(self, drawer: Drawer) -> Drawer:
        return drawer.copy()

    def smoothscale(self, drawer: Drawer, width: int, height: int) -> Drawer:
        """A new `width` × `height` (logical) surface showing `drawer`
        resampled. The backend resamples `drawer`'s pixels straight to the
        device target — one resampling whatever the scale, and a no-op when
        the sizes already match (e.g. a density-matched bitmap)."""
        return Drawer.smoothscale(drawer, width, height)

    def image(self, image: Image) -> Drawer:
        """A drawer holding `image` at its native pixel size, scale-neutral
        (raw pixels — same at any display scale). To *display* a bitmap at a
        logical size, resample it via `smoothscale` (what `Picture` does)."""
        return Drawer.image(image)

    def image_from_bytes(self, data: bytes, dimensions: PositionTuple) -> Drawer:
        """Like `image`, from a raw RGBA buffer."""
        return Drawer.image_from_bytes(data, *dimensions)


def _record_border(surface: Drawer, border: Border) -> None:
    # A 1-px side degenerates to a line, a thicker one to a trapezoid —
    # the shapes Container historically drew, at the surface's device size
    # (a ScaledDrawing passes a border with device side widths).
    width, height = surface.device_width, surface.device_height
    for color, points in border.describe_borders(width, height):
        if points:
            if points[0] == points[-1]:
                # Degenerate trapezoid (1px side): a plain line.
                surface.line(color, Position(*points[0]), Position(*points[1]))
            else:
                surface.filled_polygon([Position(*p) for p in points], color)


class ScaledDrawing(Drawing):
    """`Drawing` for a display scale ≠ 1.0: every logical coordinate becomes
    device at record time.

    Rectangles scale edge-wise (`_scale_rect`), positions round half-up,
    1-px strokes thicken to round(scale), borders are rebuilt with device
    side widths, `new_surface` allocates ceil(logical × scale). A child
    drawer is already device, so a blit only converts the anchor.
    """

    __slots__ = ("_scale", "_stroke")

    def __init__(self, scale: float):
        assert scale != 1.0
        self._scale = float(scale)
        self._stroke = max(1, to_device(1, self._scale))

    @property
    def scale(self) -> float:
        return self._scale

    def new_surface(self, width: LogicalPx, height: LogicalPx) -> Drawer:
        return Drawer.at_scale(width, height, self._scale)

    def screen_surface(
        self,
        width: LogicalPx,
        height: LogicalPx,
        device_width: DevicePx,
        device_height: DevicePx,
    ) -> Drawer:
        out = Drawer(device_width, device_height)
        out.set_logical_size(width, height, self._scale)
        return out

    def fill(
        self, surface: Drawer, color: Color, rectangle: Rectangle | None = None
    ) -> None:
        surface.fill(
            color, None if rectangle is None else _scale_rect(rectangle, self._scale)
        )

    def blit(self, surface: Drawer, drawer: Drawer, position: PositionTuple) -> None:
        scale = self._scale
        x, y = to_device(position[0], scale), to_device(position[1], scale)
        # A child ending exactly at the parent's logical edge anchors to
        # the device edge: its ceil-sized surface can overshoot the half-up
        # anchor by one pixel, and the parent would clip its last row (e.g.
        # the bottom border of a final button). min(): never shift the
        # child off its half-up position either — in a root sized on a
        # larger real OS buffer, the spare device column stays background
        # rather than displacing a full-width child.
        if position[0] + drawer.get_width() == surface.get_width():
            x = min(x, surface.device_width - drawer.device_width)
        if position[1] + drawer.get_height() == surface.get_height():
            y = min(y, surface.device_height - drawer.device_height)
        surface.blit(drawer, Position(x, y))

    def line(
        self, surface: Drawer, color: Color, start: PositionTuple, end: PositionTuple
    ) -> None:
        scale = self._scale
        surface.line(
            color,
            Position(to_device(start[0], scale), to_device(start[1], scale)),
            Position(to_device(end[0], scale), to_device(end[1], scale)),
            width=self._stroke,
        )

    def rectangle(self, surface: Drawer, rectangle: Rectangle, color: Color) -> None:
        surface.rectangle(
            _scale_rect(rectangle, self._scale), color, width=self._stroke
        )

    def box(self, surface: Drawer, rectangle: Rectangle, color: Color) -> None:
        surface.box(_scale_rect(rectangle, self._scale), color)

    def filled_polygon(
        self, surface: Drawer, points: Sequence[PositionTuple], color: Color
    ) -> None:
        scale = self._scale
        surface.filled_polygon(
            [Position(to_device(x, scale), to_device(y, scale)) for x, y in points],
            color,
        )

    def border(self, surface: Drawer, border: Border) -> None:
        _record_border(surface, border.scaled(self._scale))

    def smoothscale(self, drawer: Drawer, width: int, height: int) -> Drawer:
        out = Drawer.at_scale(width, height, self._scale)
        out._cmd(SmoothScaleArgs(drawer))
        return out

    # `copy`, `image` and `image_from_bytes` are inherited unchanged: a copy
    # keeps the source's shape, and an image drawer is native-size raw pixels
    # (scale-neutral — display it through `smoothscale`).
