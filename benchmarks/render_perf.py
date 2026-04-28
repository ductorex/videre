"""Render performance benchmark for Videre.

Measures per-frame render time on representative UI scenarios. Designed to
be run before and after architectural changes (e.g. a Drawer-based widget
refactor) to quantify performance impact.

Run with:
    uv run python -m benchmarks.render_perf

Or, with custom parameters:
    uv run python -m benchmarks.render_perf --frames 500 --runs 7

Scenarios
---------
- static_simple   : trivial UI, nothing changes (sanity baseline).
- static_complex  : grid + progress bars, nothing changes
                    (pure composition cost; dominated by blits).
- dirty_one       : same as static_complex but one ProgressBar is mutated
                    each frame (typical hover/animation pattern).
- dirty_many      : 24 ProgressBars all mutated each frame
                    (stress: many widgets dirty simultaneously).
- deep_nesting    : Containers nested many levels deep
                    (cumulative blits across the tree).
- text_heavy      : long wrapped paragraph
                    (freetype rasterization + text layout cost).

The static_* scenarios are near zero on the current architecture thanks to
dirty tracking (cached surfaces are reused). They still serve as baselines:
if a refactor inflates them, that is a regression. The dirty_* scenarios
are where the bulk of useful signal lives.

Notes
-----
- Each scenario runs `--frames` frames per run, `--runs` times. The reported
  number is the median per-frame time across runs (robust to outliers).
- Uses StepWindow(hide=True) so rendering is software-only and not coupled
  to the OS compositor or vsync.
- A single warmup frame is rendered before the timed loop so first-frame
  costs (font loading, surface allocation) do not pollute the measurement.
"""

from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass
from typing import Callable

import videre
from videre import Border, Column, Container, Padding, ProgressBar, Row, Text, TextWrap
from videre.testing.step_window import StepWindow

# -----------------------------------------------------------------------------
# Scenario builders
# -----------------------------------------------------------------------------

# A scenario builder returns (root_widget, optional per-frame mutator).
# The mutator, if not None, is called as `mutator(frame_index)` before each
# rendered frame and is expected to mark some widget dirty.
Setup = tuple[object, Callable[[int], None] | None]


def setup_static_simple() -> Setup:
    root = Container(Text("Hello world"), border=Border.all(1), padding=Padding.all(8))
    return root, None


def _grid(rows: int, cols: int) -> Column:
    return Column(
        [
            Row(
                [
                    Container(
                        Text(f"{r}.{c}"), border=Border.all(1), padding=Padding.all(2)
                    )
                    for c in range(cols)
                ]
            )
            for r in range(rows)
        ]
    )


def _build_complex_root_and_progress() -> tuple[object, ProgressBar]:
    progress = ProgressBar(value=0.0)
    root = Column(
        [
            Text("Header"),
            Container(_grid(8, 6), border=Border.all(1), padding=Padding.all(4)),
            Column([ProgressBar(value=i / 10.0) for i in range(6)]),
            progress,
        ]
    )
    return root, progress


def setup_static_complex() -> Setup:
    root, _ = _build_complex_root_and_progress()
    return root, None


def setup_dirty_one() -> Setup:
    root, progress = _build_complex_root_and_progress()

    def mutate(i: int) -> None:
        progress.value = (i % 100) / 100.0

    return root, mutate


def setup_dirty_many() -> Setup:
    bars = [ProgressBar(value=0.0) for _ in range(24)]
    root = Column(
        [
            Text("Header"),
            Container(_grid(6, 4), border=Border.all(1), padding=Padding.all(4)),
            Column(bars),
        ]
    )

    def mutate(i: int) -> None:
        v = (i % 100) / 100.0
        for bar in bars:
            bar.value = v

    return root, mutate


def setup_deep_nesting(depth: int = 12) -> Setup:
    inner: object = Text("deep")
    for _ in range(depth):
        inner = Container(inner, border=Border.all(1), padding=Padding.all(2))
    return inner, None


def setup_text_heavy() -> Setup:
    paragraph = " ".join(["The quick brown fox jumps over the lazy dog."] * 30)
    root = Container(Text(paragraph, wrap=TextWrap.WORD), padding=Padding.all(10))
    return root, None


SCENARIOS: dict[str, Callable[[], Setup]] = {
    "static_simple": setup_static_simple,
    "static_complex": setup_static_complex,
    "dirty_one": setup_dirty_one,
    "dirty_many": setup_dirty_many,
    "deep_nesting": setup_deep_nesting,
    "text_heavy": setup_text_heavy,
}


# -----------------------------------------------------------------------------
# Bench loop
# -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Stats:
    median_ms: float
    min_ms: float
    max_ms: float
    stdev_ms: float


def bench(setup: Callable[[], Setup], n_frames: int, n_runs: int) -> Stats:
    per_run_ms: list[float] = []
    for _ in range(n_runs):
        with StepWindow() as win:
            root, mutate = setup()
            win.controls = [root]
            win.render()  # warmup
            t0 = time.perf_counter()
            for i in range(n_frames):
                if mutate is not None:
                    mutate(i)
                win.render()
            elapsed = time.perf_counter() - t0
            per_run_ms.append(elapsed / n_frames * 1000.0)
    return Stats(
        median_ms=statistics.median(per_run_ms),
        min_ms=min(per_run_ms),
        max_ms=max(per_run_ms),
        stdev_ms=statistics.stdev(per_run_ms) if len(per_run_ms) > 1 else 0.0,
    )


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------


def _print_header() -> None:
    print(
        f"{'scenario':<16s} | "
        f"{'median':>9s} | "
        f"{'min':>9s} | "
        f"{'max':>9s} | "
        f"{'stdev':>9s}"
    )
    print("-" * 64)


def _print_row(name: str, s: Stats) -> None:
    print(
        f"{name:<16s} | "
        f"{s.median_ms:>6.2f} ms | "
        f"{s.min_ms:>6.2f} ms | "
        f"{s.max_ms:>6.2f} ms | "
        f"{s.stdev_ms:>6.2f} ms"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Videre render performance benchmark.")
    parser.add_argument(
        "--frames",
        type=int,
        default=200,
        help="Frames rendered per run (default: 200).",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Number of independent runs per scenario (default: 5).",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Run a single named scenario instead of all.",
    )
    args = parser.parse_args()

    print(
        f"videre {videre.__name__} | "
        f"frames/run = {args.frames} | "
        f"runs/scenario = {args.runs}"
    )
    print()
    _print_header()

    scenarios = SCENARIOS
    if args.only is not None:
        if args.only not in scenarios:
            available = ", ".join(scenarios)
            raise SystemExit(f"Unknown scenario: {args.only!r}. Available: {available}")
        scenarios = {args.only: scenarios[args.only]}

    for name, setup in scenarios.items():
        result = bench(setup, n_frames=args.frames, n_runs=args.runs)
        _print_row(name, result)


if __name__ == "__main__":
    main()
