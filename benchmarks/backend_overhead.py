"""Overhead of the AbstractBackend abstraction relative to raw pygame.

Unlike render_perf.py (which measures whole-frame render time per scenario),
this answers a narrower question: how much do the indirections introduced by
decoupling pygame behind AbstractBackend cost, versus calling pygame directly?

Run with:
    uv run python -m benchmarks.backend_overhead

Two parts
---------
- Part A: per-call micro-overhead for each hot drawing primitive. Each op is
  timed twice: raw pygame (with pre-built pygame objects, the theoretical
  floor) vs through the backend (with videre Color/Rectangle, which forces the
  per-call conversion). The decomposition isolates _deref / new_color /
  new_rect. Small surfaces are used on purpose: that maximizes the wrapper's
  visible share, so the ratios are an upper bound.
- Part B: a realistic frame (a Column of buttons = border + background + text)
  profiled with cProfile, both in steady state (cached surfaces) and forced
  full redraw, attributing CPU to the abstraction glue vs pygame/freetype C.
"""

from __future__ import annotations

import cProfile
import pstats
import time
import timeit

import pygame
import pygame.gfxdraw

import videre
from videre.colors import Color
from videre.core.pygame_backend.backend import PygameBackend, _deref
from videre.core.pygame_backend.definitions import PygameColor, Rect, Surface
from videre.core.rectangle import Rectangle
from videre.core.tasks import TaskManager
from videre.testing.step_window import StepWindow


def ns_per_call(stmt: str, glb: dict) -> float:
    timer = timeit.Timer(stmt, globals=glb)
    number, _ = timer.autorange()
    return min(timer.repeat(repeat=7, number=number)) / number * 1e9


def part_a() -> None:
    task_manager = TaskManager(lambda task: None)
    backend = PygameBackend(
        200, 100, "bench", lambda e: None, lambda r: None, task_manager, hide=True
    )
    backend.start()

    surf = backend.new_surface(200, 100)
    src = backend.new_surface(60, 40)
    glb = dict(
        pygame=pygame,
        gfxdraw=pygame.gfxdraw,
        backend=backend,
        _deref=_deref,
        Surface=Surface,
        surf=surf,
        src=src,
        raw=_deref(surf),
        rawsrc=_deref(src),
        vcolor=Color(10, 20, 30, 200),
        vrect=Rectangle(2, 3, 80, 50),
        pcolor=PygameColor(10, 20, 30, 200),
        prect=Rect(2, 3, 80, 50),
    )

    cases = [
        ("fill (rect)", "raw.fill(pcolor, prect)", "backend.fill(surf, vcolor, vrect)"),
        ("fill (full)", "raw.fill(pcolor)", "backend.fill(surf, vcolor)"),
        ("blit", "raw.blit(rawsrc, (5, 5))", "backend.blit(surf, src, (5, 5))"),
        (
            "line",
            "pygame.draw.line(raw, pcolor, (0, 0), (50, 50))",
            "backend.line(surf, vcolor, (0, 0), (50, 50))",
        ),
        (
            "rectangle",
            "gfxdraw.rectangle(raw, prect, pcolor)",
            "backend.rectangle(surf, vrect, vcolor)",
        ),
        ("box", "gfxdraw.box(raw, prect, pcolor)", "backend.box(surf, vrect, vcolor)"),
        (
            "new_surface",
            "Surface((50, 50), flags=pygame.SRCALPHA)",
            "backend.new_surface(50, 50)",
        ),
        ("copy", "raw.copy()", "backend.copy(surf)"),
    ]

    print("=" * 72)
    print("PART A - per-call micro-overhead (ns/call, best of 7)")
    print("=" * 72)
    print(f"{'op':<14}{'raw pygame':>12}{'via backend':>14}{'delta':>10}{'ratio':>8}")
    for name, raw_stmt, backend_stmt in cases:
        raw_ns = ns_per_call(raw_stmt, glb)
        backend_ns = ns_per_call(backend_stmt, glb)
        print(
            f"{name:<14}{raw_ns:>11.0f}n{backend_ns:>13.0f}n"
            f"{backend_ns - raw_ns:>9.0f}n{backend_ns / raw_ns:>7.2f}x"
        )

    print("\n  decomposition of the conversion tax:")
    for name, stmt in [
        ("_deref(surf)", "_deref(surf)"),
        ("new_color(v)", "backend.new_color(vcolor)"),
        ("new_rect(v)", "backend.new_rect(vrect)"),
    ]:
        print(f"    {name:<16}{ns_per_call(stmt, glb):>7.0f} ns")


def part_b(n_buttons: int = 40, reps: int = 200) -> None:
    controls = [videre.Column([videre.Button(f"Button {i}") for i in range(n_buttons)])]
    win = StepWindow(width=420, height=1000)
    win.controls = controls

    print("\n" + "=" * 72)
    print(f"PART B - realistic frame: Column of {n_buttons} Buttons (border+bg+text)")
    print("=" * 72)

    with win:
        win.render()  # warm: load fonts, first full draw
        widgets = win._layout.collect_matches(lambda w: True)
        print(f"widgets in tree: {len(widgets)}")

        start = time.perf_counter()
        for _ in range(reps):
            win.render()
        steady_ms = (time.perf_counter() - start) / reps * 1e3

        def forced() -> None:
            for _ in range(reps):
                for widget in widgets:
                    widget.update()
                win.render()

        start = time.perf_counter()
        forced()
        forced_ms = (time.perf_counter() - start) / reps * 1e3

        print(f"steady-state (cached) : {steady_ms:8.3f} ms/frame")
        print(f"forced full redraw    : {forced_ms:8.3f} ms/frame")

        profiler = cProfile.Profile()
        profiler.enable()
        forced()
        profiler.disable()

    stats = pstats.Stats(profiler)
    total = stats.total_tt

    def tottime_of(names: set[str]) -> float:
        return sum(v[2] for k, v in stats.stats.items() if k[2] in names)

    conversions = tottime_of({"new_color", "new_rect", "_deref"})
    wrappers = tottime_of(
        {
            "fill",
            "blit",
            "line",
            "rectangle",
            "box",
            "filled_polygon",
            "copy",
            "new_surface",
            "smoothscale",
            "step",
            "_step",
        }
    )
    print(f"\ntotal profiled tottime: {total * 1e3:.1f} ms over {reps} frames")
    print(
        f"  conversions (_deref/new_color/new_rect): "
        f"{conversions * 1e3:7.1f} ms  ({conversions / total * 100:4.1f}%)"
    )
    print(
        f"  backend method wrappers                : "
        f"{wrappers * 1e3:7.1f} ms  ({wrappers / total * 100:4.1f}%)"
    )

    print("\ntop 25 by tottime:")
    stats.sort_stats("tottime").print_stats(25)


def main() -> None:
    part_a()
    part_b()


if __name__ == "__main__":
    main()
