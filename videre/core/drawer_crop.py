"""`crop_drawer`: prune a `Drawer` to its visible slice (rasterization
virtualization).

Pure `Drawer` → `Drawer` transformation over the command IR (see
`videre.core.drawer`) — no per-widget knowledge. `ScrollView.draw` uses it to
paint only the viewport: `materialize` then allocates a viewport-sized
surface and composes the few visible children instead of the whole (possibly
huge) content. It virtualizes *rasterization*, not *construction*.
"""

from videre.core.dpi import to_device, to_logical_ceil
from videre.core.drawer import (
    BlitArgs,
    BoxArgs,
    CopyArgs,
    Drawer,
    FillArgs,
    FilledPolygonArgs,
    ImageArgs,
    ImageFromBytesArgs,
    LineArgs,
    Position,
    RectangleArgs,
    SmoothScaleArgs,
)
from videre.core.rectangle import Rectangle

_UNCROPPABLE = (ImageArgs, ImageFromBytesArgs, SmoothScaleArgs, CopyArgs)


def _overlaps(left: int, top: int, width: int, height: int, rect: Rectangle) -> bool:
    """Half-open AABB overlap of ``[left, left+width) x [top, top+height)`` with
    `rect`. Strict: a box merely touching `rect`'s edge shares no pixel and is
    dropped. Callers pass a 1-pixel extent for inclusive-endpoint shapes (lines,
    polygons) so those are not wrongly dropped at the boundary."""
    return (
        left < rect.left + rect.width
        and left + width > rect.left
        and top < rect.top + rect.height
        and top + height > rect.top
    )


def _is_uncroppable(drawer: Drawer) -> bool:
    """A drawer that cannot be pruned to a sub-region by dropping commands:
    its pixels come from a base surface (image / scaled / copied)."""
    return any(isinstance(cmd, _UNCROPPABLE) for cmd in drawer)


def crop_drawer(drawer: Drawer, rect: Rectangle) -> Drawer:
    """A viewport drawer: the commands of `drawer` intersecting `rect`
    (logical coords), translated so `rect`'s top-left becomes (0, 0).

    The contract is the reference blit's pixels: blitting the result at
    (0, 0) shows exactly what blitting the whole `drawer` at
    ``(-rect.left, -rect.top)`` through the same `Drawing` would show. So
    the device window is derived the way that blit derives it — half-up
    anchor, flush-adjusted when `rect` reaches the drawer's logical edge —
    and its size is the output surface's own (ceil) device size: an
    edge-scaled rect can be one device pixel short of the surface it must
    fill (e.g. at 125%, to_device(5) - to_device(1) = 5 < ceil(4 × 1.25)).

    Rules, in device pixels: a command fully outside is dropped. A kept
    child keeps its identity (same `Drawer` object — it still hits the
    `materialize` cache). A straddling child larger than the view is
    recursively cropped, else its oversized surface would come back. An
    uncroppable drawer (image/scale/copy: pixels from a base surface) is
    kept whole, re-anchored at the negative offset. Anything overflowing
    the cropped bounds is clipped by the renderer."""
    scale = drawer.scale
    out = Drawer.at_scale(rect.width, rect.height, scale)
    if scale == 1.0:
        prect = rect
    else:
        # Same anchor policy as ScaledDrawing.blit for the reference blit
        # at (-rect.left, -rect.top): half-up, snapped to the device edge
        # when the drawer ends flush with the viewport's logical edge.
        ax, ay = to_device(-rect.left, scale), to_device(-rect.top, scale)
        if -rect.left + drawer.get_width() == rect.width:
            ax = min(ax, out.device_width - drawer.device_width)
        if -rect.top + drawer.get_height() == rect.height:
            ay = min(ay, out.device_height - drawer.device_height)
        prect = Rectangle(-ax, -ay, out.device_width, out.device_height)
    _crop_into(out, drawer, prect)
    return out


def _crop_device(drawer: Drawer, rect: Rectangle) -> Drawer:
    """Recursive form of `crop_drawer`: `rect` is already in `drawer`'s own
    (device) command coordinates."""
    scale = drawer.scale
    out = Drawer(rect.width, rect.height)
    if scale != 1.0:
        out.set_logical_size(
            to_logical_ceil(rect.width, scale),
            to_logical_ceil(rect.height, scale),
            scale,
        )
    _crop_into(out, drawer, rect)
    return out


def _crop_into(out: Drawer, drawer: Drawer, rect: Rectangle) -> None:
    # Device coordinates throughout: `rect`, command geometry, child sizes.
    if _is_uncroppable(drawer):
        out.blit(drawer, Position(int(-rect.left), int(-rect.top)))
        return
    dx, dy = int(-rect.left), int(-rect.top)
    rl, rt, rw, rh = rect.left, rect.top, rect.width, rect.height
    for cmd in drawer:
        match cmd:
            case FillArgs(color=color, rectangle=None):
                # A global fill stops at the drawer's own surface in the
                # reference (materialize clips it, the blit deposits only
                # that), so emit its footprint ∩ rect — global again when
                # that covers the whole output (a view inside the content).
                il, it = max(0, rl), max(0, rt)
                ir = min(drawer.device_width, rl + rw)
                ib = min(drawer.device_height, rt + rh)
                if il < ir and it < ib:
                    clipped = Rectangle(il + dx, it + dy, ir - il, ib - it)
                    if clipped == Rectangle(0, 0, out.device_width, out.device_height):
                        out.fill(color)
                    else:
                        out.fill(color, clipped)
            case FillArgs(color=color, rectangle=r):
                if _overlaps(r.left, r.top, r.width, r.height, rect):
                    out.fill(
                        color, Rectangle(r.left + dx, r.top + dy, r.width, r.height)
                    )
            case BlitArgs(drawer=child, position=pos):
                cw, ch = child.device_width, child.device_height
                if not _overlaps(pos.x, pos.y, cw, ch, rect):
                    continue
                inside = (
                    pos.x >= rl
                    and pos.y >= rt
                    and pos.x + cw <= rl + rw
                    and pos.y + ch <= rt + rh
                )
                if not inside and (cw > rw or ch > rh) and not _is_uncroppable(child):
                    ix0, iy0 = max(pos.x, rl), max(pos.y, rt)
                    ix1, iy1 = min(pos.x + cw, rl + rw), min(pos.y + ch, rt + rh)
                    child_rect = Rectangle(
                        ix0 - pos.x, iy0 - pos.y, ix1 - ix0, iy1 - iy0
                    )
                    out.blit(
                        _crop_device(child, child_rect),
                        Position(int(ix0 + dx), int(iy0 + dy)),
                    )
                else:
                    out.blit(child, Position(int(pos.x + dx), int(pos.y + dy)))
            case LineArgs(color=color, start=s, end=e, width=w):
                pad = w // 2  # a thick stroke bleeds around its segment
                bx, by = min(s.x, e.x) - pad, min(s.y, e.y) - pad
                if _overlaps(
                    bx,
                    by,
                    abs(e.x - s.x) + 1 + 2 * pad,
                    abs(e.y - s.y) + 1 + 2 * pad,
                    rect,
                ):
                    out.line(
                        color,
                        Position(s.x + dx, s.y + dy),
                        Position(e.x + dx, e.y + dy),
                        width=w,
                    )
            case RectangleArgs(rectangle=r, color=color, width=w):
                if _overlaps(r.left, r.top, r.width, r.height, rect):
                    out.rectangle(
                        Rectangle(r.left + dx, r.top + dy, r.width, r.height),
                        color,
                        width=w,
                    )
            case BoxArgs(rectangle=r, color=color):
                if _overlaps(r.left, r.top, r.width, r.height, rect):
                    out.box(
                        Rectangle(r.left + dx, r.top + dy, r.width, r.height), color
                    )
            case FilledPolygonArgs(points=pts, color=color):
                xs = [p.x for p in pts]
                ys = [p.y for p in pts]
                if pts and _overlaps(
                    min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1, rect
                ):
                    out.filled_polygon(
                        [Position(p.x + dx, p.y + dy) for p in pts], color
                    )
            case _:
                raise NotImplementedError(type(cmd).__name__, cmd)
