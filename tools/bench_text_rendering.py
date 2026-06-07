"""Benchmark: legacy (pygame.freetype) vs shaped (HarfBuzz) text rendering.

    uv run python tools/bench_text_rendering.py

Both renderers implement the same `render_text` / `render_char`; we build each
on the SAME headless backend and time them on a set of samples, in two regimes:

- **warm** — one renderer instance reused, caches hot. This is the steady-state
  cost paid whenever the text CHANGES (typing in a TextInput, scrolling,
  animation). Widgets cache their rendered surface, so static UI never
  re-renders — the warm number is the one that matters in practice.
- **cold** — a fresh renderer per call (empty glyph / shaping caches; fonts
  already loaded). Approximates the first paint of never-seen text. The two
  renderers cache different things, so treat cold as indicative, not exact.

Reported per sample: median microseconds per `render_text` call for each
renderer and the shaped/legacy ratio.
"""

import statistics
import time

from videre.colors import Color
from videre.core.shaping import ShapedTextRendering
from videre.testing.step_window import StepWindow
from videre.testing.utils import LOREM_IPSUM, TEXT_SAMPLES

_SIZE = 16
_WIDTH = 600
_BLACK = Color(0, 0, 0)


def _samples() -> dict[str, tuple[str, int, int]]:
    """name -> (text, warm_iters, cold_iters). Iter counts are tuned so each
    cell takes a fraction of a second (heavier texts get fewer iterations)."""
    paragraph = LOREM_IPSUM.split("\n\n")[0].strip()  # one long Latin paragraph
    arabic = TEXT_SAMPLES["arabic"].splitlines()[0]  # the demo's RTL+Latin line
    cjk = TEXT_SAMPLES["japanese"].replace("\n", " ")[:90]
    mixed = "Hello مرحبا World العالم 123 שלום test"
    return {
        "latin_label": ("Open file", 400, 60),
        "latin_sentence": ("The quick brown fox jumps over the lazy dog.", 400, 50),
        "latin_paragraph": (paragraph, 60, 15),
        "arabic_line": (arabic, 120, 20),
        "cjk": (cjk, 150, 25),
        "mixed_bidi": (mixed, 200, 30),
    }


def _median_us(call, iters: int) -> float:
    samples = []
    for _ in range(iters):
        t0 = time.perf_counter_ns()
        call()
        samples.append(time.perf_counter_ns() - t0)
    return statistics.median(samples) / 1000.0


def _render(renderer, text: str) -> None:
    renderer.render_text(text, _WIDTH, color=_BLACK, wrap_words=True)


def _warm(make_renderer, text: str, iters: int) -> float:
    renderer = make_renderer()
    for _ in range(5):  # warm the glyph / measure caches
        _render(renderer, text)
    return _median_us(lambda: _render(renderer, text), iters)


def _cold(make_renderer, reset, text: str, iters: int) -> float:
    def call():
        reset()
        _render(make_renderer(), text)

    call()  # one priming call so font files / provider are loaded (a fixed
    # startup cost we don't want to fold into every "cold" sample)
    return _median_us(call, iters)


def main() -> None:
    with StepWindow(width=900, height=600) as win:
        be = win.backend

        def make_legacy():
            return be.text_rendering(size=_SIZE)

        def make_shaped():
            return ShapedTextRendering(be, size=_SIZE)

        # Cold reset: legacy shares the backend's font factory, so clear its
        # measure cache; shaped gets a fresh shaper+rasterizer from make_shaped.
        def reset_legacy():
            be._fonts._cached_char_measures.clear()

        def reset_shaped():
            pass

        print(f"render_text  size={_SIZE}  width={_WIDTH}  (median us/call)\n")
        head = f"{'sample':16} | {'warm legacy':>11} {'warm shaped':>11} {'x':>5} |"
        head += f" {'cold legacy':>11} {'cold shaped':>11} {'x':>5}"
        print(head)
        print("-" * len(head))
        for name, (text, wi, ci) in _samples().items():
            lw = _warm(make_legacy, text, wi)
            sw = _warm(make_shaped, text, wi)
            lc = _cold(make_legacy, reset_legacy, text, ci)
            sc = _cold(make_shaped, reset_shaped, text, ci)
            print(
                f"{name:16} | {lw:11.1f} {sw:11.1f} {sw / lw:4.1f}x |"
                f" {lc:11.1f} {sc:11.1f} {sc / lc:4.1f}x"
            )

        # render_char (Checkbox / Radio / Character path), warm.
        print(f"\nrender_char  size={_SIZE}  (median us/call, warm)")
        legacy, shaped = make_legacy(), make_shaped()
        for label, ch in [("latin 'A'", "A"), ("cjk '世'", "世"), ("arabic 'ا'", "ا")]:
            for r in (legacy, shaped):
                r.render_char(ch, _BLACK)  # warm
            lc = _median_us(lambda: legacy.render_char(ch, _BLACK), 500)
            sc = _median_us(lambda: shaped.render_char(ch, _BLACK), 500)
            print(f"  {label:12} legacy {lc:7.2f}  shaped {sc:7.2f}  {sc / lc:4.1f}x")


if __name__ == "__main__":
    main()
