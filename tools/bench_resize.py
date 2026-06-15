"""Benchmark the document cache on resize: text fixed, width sweeps.

    uv run python tools/bench_resize.py

The C refactor split text rendering into a cacheable text-only *shape*
(partition + HarfBuzz) and a width-dependent *layout + paint*. A widget caches
its `ShapedDocument`, so a window resize replays only `document.render(width)`
instead of the whole `render_text` (which re-shapes every time).

This times one resize gesture = a sweep over several widths, three ways:

- **legacy**          — `render_text(text, w)` per width (no cache; re-renders).
- **shaped no-cache** — `render_text(text, w)` per width  → re-shapes (= before C).
- **shaped cached**   — `document.render(w)` per width, document built ONCE
                        outside the measurement → shape paid once (= after C).

Reported per sample: median microseconds per single-width render, and the
cache speed-up (no-cache / cached) plus the cached/legacy ratio.
"""

import statistics
import time

from videre.colors import Color
from videre.core.shaping import ShapedTextRendering
from videre.testing.step_window import StepWindow
from videre.testing.utils import LOREM_IPSUM, TEXT_SAMPLES

_SIZE = 16
_BLACK = Color(0, 0, 0)
_WIDTHS = [300, 350, 400, 450, 500, 550, 600, 650]  # a resize sweep
_ITERS = 15


def _median_us_per_render(sweep, iters: int) -> float:
    samples = []
    for _ in range(iters):
        t0 = time.perf_counter_ns()
        sweep()
        samples.append(time.perf_counter_ns() - t0)
    return statistics.median(samples) / 1000.0 / len(_WIDTHS)


def main() -> None:
    paragraph = LOREM_IPSUM.split("\n\n")[0].strip()
    arabic = TEXT_SAMPLES["arabic"].splitlines()[0]
    cjk = TEXT_SAMPLES["japanese"].replace("\n", " ")[:90]
    samples = {"latin_paragraph": paragraph, "arabic_line": arabic, "cjk": cjk}

    with StepWindow(width=900, height=600) as win:
        be = win.backend
        legacy = be.text_rendering(size=_SIZE)
        shaped = ShapedTextRendering(be, size=_SIZE)

        print(
            f"resize sweep over {len(_WIDTHS)} widths  size={_SIZE}  "
            f"(median us per single-width render)\n"
        )
        head = (
            f"{'sample':16} | {'legacy':>9} {'shaped/no-cache':>16} "
            f"{'shaped/cached':>14} | {'cache x':>8} {'vs legacy':>10}"
        )
        print(head)
        print("-" * len(head))

        for name, text in samples.items():

            def legacy_sweep():
                for w in _WIDTHS:
                    legacy.render_text(text, w, color=_BLACK, wrap_words=True)

            def nocache_sweep():
                for w in _WIDTHS:
                    shaped.render_text(text, w, color=_BLACK, wrap_words=True)

            doc = shaped.document(text)  # shape ONCE, outside the measurement

            def cached_sweep():
                for w in _WIDTHS:
                    doc.render(w, color=_BLACK, wrap_words=True)

            for _ in range(3):  # warm glyph / measure caches
                legacy_sweep()
                nocache_sweep()
                cached_sweep()

            lg = _median_us_per_render(legacy_sweep, _ITERS)
            nc = _median_us_per_render(nocache_sweep, _ITERS)
            ca = _median_us_per_render(cached_sweep, _ITERS)
            print(
                f"{name:16} | {lg:9.1f} {nc:16.1f} {ca:14.1f} | "
                f"{nc / ca:7.1f}x {ca / lg:9.1f}x"
            )


if __name__ == "__main__":
    main()
