"""Display-scale (DPI) helpers: the rounding vocabulary and the platform
plumbing.

The OS distinguishes *logical* pixels (what an application lays out in) from
*device* pixels (what the screen has). At a 150% display scale, a window
meant to look 1200 px wide must cover 1800 device pixels. A process that
does not declare itself DPI-aware is rendered at logical size and
bitmap-stretched by the compositor — which blurs everything (Windows, Wayland;
X11 never stretches and macOS wants a per-window flag instead of a process
declaration).

**Naming glossary** (videre-wide, one word = one meaning):

- Pixels: **logical** (the unmarked default unit — public APIs, widget code
  and events carry no prefix; the word only appears in these helpers and in
  prose) vs **device** (the screen's real pixels — the only marked unit:
  `device_width`, `to_device*`). The multiplier is the *device-pixel ratio*
  (`scale_factor`).
- Text (Unicode vocabulary, unrelated to pixels): **logical vs visual
  *order*** (memory order vs bidi display order — always qualified: "logical
  order", "logical position") and **source** for indices into the source
  string (`source_start`, `_glyph_to_source`). A pre-wrap line is a *source
  line*.

So a bare "logical" always means pixels; text-order uses always carry
"order"/"position" next to it.

**Rounding vocabulary** (`to_device*` / `to_logical*`): the conversions the
scaling model is built on. There is no single "logical to device" rounding —
the right one depends on what the value *is* — so the vocabulary is three
roundings × two directions, with the rounding spelled out in the name:

- no suffix — **half-up, the nearest pixel**: positions, anchors, stroke and
  side widths, font sizes, the caret x. Fidelity: land as close as possible.
- ``_ceil`` — **cover**: surface sizes (never smaller than any edge-scaled
  slot), device content measured back into a logical box, bottom/right
  edges. The result always encloses the input.
- ``_floor`` — **stay inside**: sizes and top/left edges (a length inside the
  device box must stay inside the logical one), wrap widths (wrapped
  device content must fit back inside the logical box).

Plus one *inverse mapping*, not a plain rounding: ``to_logical_slot`` — the
logical pixel whose rendered slot contains a device coordinate. Pointer
coordinates need it: rendering places logical pixel ``l`` on the device
slot ``[to_device(l), to_device(l + 1))`` (half-up edge scaling), and
``floor`` is *not* the inverse of that mapping (at 125% it lands one pixel
short on a quarter of all coordinates — a click on a widget's first device
pixel would be dispatched to its neighbour).

All helpers are correct for negative values (a pointer dragged above/left of
the window, a child blitted at a negative position) — half-up and floor are
implemented with `math.floor`, never `int()` (which truncates toward zero) —
and the divisions/ceil/floor are guarded against float representation error
(e.g. ``33 / 1.1 == 29.999999999999996`` must floor to 30, and
``ceil`` must not over-allocate on a product that is exact on paper). They
are pure and importable from anywhere (`Drawing`, text rendering, windowings,
`FakeUser`).

**Platform plumbing** (`declare_dpi_awareness` / `system_scale_factor`): meant
to be called by *windowing implementations only* (e.g. ``PygameWindowing``) —
core and widget code only ever sees the backend-agnostic
``AbstractWindowing.scale_factor``. Every function degrades gracefully to "no
scaling" wherever the platform offers nothing to read, so calling them is
always safe. Today only Windows has real plumbing here. The long-term exit is
SDL3 (``SDL_GetWindowDisplayScale`` unifies all platforms) once pygame ships
it; the plumbing then shrinks to nothing for the pygame backend, and remains
available to backends built on libraries without DPI support (e.g. SFML).
"""

import ctypes
import logging
import math
import sys
from typing import TypeAlias

logger = logging.getLogger(__name__)

# Documentation-only aliases for signatures where both units meet (core /
# boundary modules). Widget-facing APIs keep plain ints: logical is the
# unmarked default unit there (see the naming glossary above).
LogicalPx: TypeAlias = int
DevicePx: TypeAlias = int

# Float guard: kill representation error (~1e-16 per multiply/divide) before
# a ceil/floor turns it into a whole spurious pixel, without touching any
# legitimate fraction (real fractions of value×scale are ≥ 1/scale ≫ 1e-9).
_GUARD_DIGITS = 9


def to_device(value: LogicalPx | float, scale: float) -> DevicePx:
    """A logical value on the nearest device pixel (half-up).

    Positions, anchors, stroke/side widths, font sizes, hit-test inputs."""
    return math.floor(value * scale + 0.5)


def to_device_ceil(value: LogicalPx | float, scale: float) -> DevicePx:
    """A logical size in device pixels, covering (ceil).

    Surface allocations: never smaller than any edge-scaled slot a parent
    computes (a gap would show; the ≤1-px excess stays inside the surface)."""
    return math.ceil(round(value * scale, _GUARD_DIGITS))


def to_device_floor(value: LogicalPx | float, scale: float) -> DevicePx:
    """A logical length in device pixels, staying inside (floor).

    Wrap widths: content wrapped to this device width always fits back
    inside the logical box it was measured against."""
    return math.floor(round(value * scale, _GUARD_DIGITS))


def to_logical(value: DevicePx | float, scale: float) -> LogicalPx:
    """A device value on the nearest logical pixel (half-up).

    Outgoing display coordinates where fidelity matters — e.g. the caret x
    (the closest logical column to the device glyph edge)."""
    return math.floor(value / scale + 0.5)


def to_logical_ceil(value: DevicePx | float, scale: float) -> LogicalPx:
    """A device size — or a bottom/right edge — in logical pixels (ceil).

    The logical box always covers the device content."""
    return math.ceil(round(value / scale, _GUARD_DIGITS))


def to_logical_floor(value: DevicePx | float, scale: float) -> LogicalPx:
    """A device size — or a top/left edge — in logical pixels (floor).

    A length inside the device box stays inside the logical one (e.g. the
    logical window size derived from an OS-resized device buffer)."""
    return math.floor(round(value / scale, _GUARD_DIGITS))


def to_logical_slot(value: DevicePx | float, scale: float) -> LogicalPx:
    """The logical pixel whose rendered slot contains this device
    coordinate — the exact inverse of the half-up edge mapping: the unique
    ``l`` with ``to_device(l) <= value < to_device(l + 1)``.

    Pointer coordinates: what the renderer put under the cursor is what the
    hit-test must find. A plain floor is *not* this inverse (at 125% it is
    off by one on a quarter of all coordinates)."""
    return math.ceil(round((value + 0.5) / scale, _GUARD_DIGITS)) - 1


# DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2, winuser.h (Windows 10 1703+).
_PER_MONITOR_AWARE_V2 = -4


def declare_dpi_awareness() -> bool:
    """Declare this process DPI-aware. Returns True if a declaration call
    succeeded (or False where the concept does not exist).

    Must run **before the first OS window is created** — afterwards Windows
    ignores it. Windows-only by nature: macOS uses a per-window flag (the
    windowing library's job), Wayland scales through the compositor protocol,
    X11 does not scale windows at all. On those platforms this is a no-op.
    """
    if sys.platform != "win32":
        return False
    try:
        # Windows 10 1703+ — per-monitor v2 (the scale can differ per screen).
        if ctypes.windll.user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(_PER_MONITOR_AWARE_V2)
        ):
            return True
    except (OSError, AttributeError):
        pass
    try:
        # Windows 8.1+ — 2 = PROCESS_PER_MONITOR_DPI_AWARE (0 == S_OK).
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return True
    except (OSError, AttributeError):
        pass
    try:
        # Windows Vista+ — system-wide awareness.
        return bool(ctypes.windll.user32.SetProcessDPIAware())
    except (OSError, AttributeError):
        return False


def system_scale_factor() -> float:
    """The system display scale as a ratio (1.0 = 100%, 1.5 = 150%).

    Only meaningful on Windows *after* :func:`declare_dpi_awareness` — an
    unaware process is deliberately lied to and reads 96 dpi. Returns 1.0
    wherever the platform offers nothing to read (macOS/X11/Wayland: the
    windowing library is the right source there).
    """
    if sys.platform != "win32":
        return 1.0
    try:
        # Windows 10 1607+. 96 dpi is the 100% baseline.
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except (OSError, AttributeError):
        return 1.0
