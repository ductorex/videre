"""Benchmark Uniseg against Videre's specialized UAX #29 splitter.

uv run python tools/bench_word_splitter.py
"""

import statistics
import time

from uniseg.wordbreak import words as uniseg_words

from videre.core.text_rendering.text_partition.word_splitter import (
    split_word_spans,
    word_boundaries,
)
from videre.testing.utils import LOREM_IPSUM, TEXT_SAMPLES


def _samples() -> dict[str, str]:
    return {
        "latin_label": "Open file",
        "latin_sentence": "The quick brown fox jumps over the lazy dog.",
        "latin_paragraph": LOREM_IPSUM.split("\n\n")[0].strip(),
        "arabic_line": TEXT_SAMPLES["arabic"].splitlines()[0],
        "cjk": TEXT_SAMPLES["japanese"].replace("\n", " ")[:90],
        "mixed_bidi": "Hello \u0645\u0631\u062d\u0628\u0627 World 123 \u05e9\u05dc\u05d5\u05dd test",
    }


def _median_us(call, iterations: int) -> float:
    samples = []
    for _ in range(7):
        start = time.perf_counter_ns()
        for _ in range(iterations):
            call()
        samples.append((time.perf_counter_ns() - start) / iterations / 1000)
    return statistics.median(samples)


def main() -> None:
    print("word splitting (median us/call, warm property caches)\n")
    head = (
        f"{'sample':16} | {'uniseg':>10} {'uax29':>10} {'profile':>10} "
        f"{'uax speedup':>11}"
    )
    print(head)
    print("-" * len(head))
    for name, text in _samples().items():
        list(uniseg_words(text))
        word_boundaries(text)
        split_word_spans(text)
        iterations = 500 if len(text) < 100 else 80
        uniseg = _median_us(lambda: list(uniseg_words(text)), iterations)
        uax29 = _median_us(lambda: word_boundaries(text), iterations)
        profile = _median_us(lambda: split_word_spans(text), iterations)
        print(
            f"{name:16} | {uniseg:10.1f} {uax29:10.1f} {profile:10.1f} "
            f"{uniseg / uax29:10.2f}x"
        )


if __name__ == "__main__":
    main()
