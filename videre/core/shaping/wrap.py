"""Width-based wrapping of `ShapedLine`s.

Public entry point: ``wrap_lines(lines, width, wrap_words)``. Given an
iterable of `ShapedLine`s (the output of `shape_text`), produces a new
iterable where every line fits within ``width`` pixels, breaking longer
lines as needed.

Two strategies, parameterized by ``wrap_words``:

- ``wrap_words=True`` (word wrap): the line is filled word-by-word.
  When the next word would not fit, the current line is flushed and the
  word starts a new line. A word that does not fit alone on a fresh
  line is either taken whole if it is atomic (Latin, Arabic, Hebrew —
  forced overflow) or split at a cluster boundary if it is non-atomic
  (CJK, SE-Asian — natural break points exist inside).

- ``wrap_words=False`` (character / cluster wrap): the line is filled
  one cluster at a time, regardless of word boundaries. The first
  cluster that would exceed ``width`` triggers a flush, and the line
  resumes from that cluster. Atomic-word boundaries are ignored.

A cluster here is a maximal run of consecutive glyphs in a single
`ShapedRun` that share the same source-character ``cluster`` index;
HarfBuzz guarantees these are the smallest indivisible visual units
(a base + combining marks, or all the glyphs from a ligature
substitution). Breaking inside a cluster would corrupt the rendering.

The output preserves the original word/run structure: each emitted
`ShapedLine` regroups its clusters back into the same `ShapedWord` /
`ShapedRun` shells they came from, so downstream code (rendering,
underline, future selection) keeps the same invariants. ``source_text``
on each sub-run is recomputed from the cluster range covered by its
glyphs (an approximation that is exact for LTR runs and contiguous
for RTL runs since we never reshuffle clusters).
"""

from dataclasses import dataclass
from typing import Iterable, Iterator

from videre.core.shaping.shaped import ShapedGlyph, ShapedLine, ShapedRun, ShapedWord


@dataclass(frozen=True, slots=True)
class _Cluster:
    """One indivisible visual unit inside a `ShapedLine`.

    `word_idx` and `run_idx` locate the parent word and run in the
    original line. `glyph_start` / `glyph_end` are the half-open glyph
    range inside that run. `width` is the cumulative `x_advance` of
    those glyphs. `real_right` is the cluster's visual right edge from
    its left edge (= `max(width, max ink_right of any glyph in the
    cluster)`); used by the wrap engine to spot glyphs whose bitmap
    overhangs their advance.
    """

    word_idx: int
    run_idx: int
    glyph_start: int
    glyph_end: int
    width: float
    real_right: float


def wrap_lines(
    lines: Iterable[ShapedLine],
    width: int,
    wrap_words: bool = True,
    *,
    space_advance: float = 0.0,
) -> Iterator[ShapedLine]:
    """Subdivide each input line into one or more lines fitting within ``width``.

    ``space_advance`` is the virtual horizontal advance inserted between
    two consecutive `ShapedWord`s on the same line **iff** the second
    word carries `space_before=True` (set by `_split_by_word` from the
    source whitespace). The shaped pipeline does not store inter-word
    spaces as glyphs, so callers must pass the advance computed on the
    reference font (matches what `pygame_text_rendering` does with
    `space_shift`). With ``space_advance == 0`` words are packed tight,
    which is rarely what you want for natural-language text. Two
    consecutive words with no source whitespace between them (e.g. a
    UAX#29 word break inside `"Hello世界"`) get no gap regardless of
    `space_advance`, matching what `_render_line` does.

    Empty lines are passed through unchanged. ``width`` is in pixels and
    must be positive; with ``width <= 0`` we cannot make any progress and
    the original line is yielded as-is to avoid an infinite loop.
    """
    if width <= 0:
        yield from lines
        return
    for line in lines:
        if line.is_empty():
            yield line
            continue
        if wrap_words:
            yield from _wrap_by_words(line, width, space_advance)
        else:
            yield from _wrap_by_clusters(line, width, space_advance)


# ---------------------------------------------------------------------------
# Word-level wrap
# ---------------------------------------------------------------------------


def _wrap_by_words(
    line: ShapedLine, width: int, space_advance: float
) -> Iterator[ShapedLine]:
    pending: list[ShapedWord] = list(line.words)
    current: list[ShapedWord] = []
    current_width: float = 0.0
    current_real_right: float = 0.0
    while pending:
        word = pending[0]
        w_width = _word_width(word)
        w_real_right = _word_real_right(word)
        # Inter-word advance only matters when there's already content on
        # the current line AND the source had whitespace before this word
        # (`space_before`). The first word starts flush-left, and a word
        # that follows the previous one with no source whitespace (UAX#29
        # word break, e.g. inside `"Hello世界"`) packs flush.
        gap = space_advance if (current and word.space_before) else 0.0
        # Test against the visual right edge (which can exceed the
        # advance for italics, swashes, certain punctuation), not just
        # the cumulative advance — otherwise a glyph's bitmap can spill
        # past the surface and get clipped at the right edge.
        new_real_right = max(current_real_right, current_width + gap + w_real_right)
        if new_real_right <= width:
            current.append(word)
            current_width += gap + w_width
            current_real_right = new_real_right
            pending.pop(0)
            continue
        # Doesn't fit on the current accumulator.
        if current:
            # Flush and retry the word on an empty line. The trailing
            # `space_advance` of the last word is *not* counted in the
            # flushed line.
            yield ShapedLine(words=tuple(current))
            current = []
            current_width = 0.0
            current_real_right = 0.0
            continue
        # Current line is empty AND word alone doesn't fit.
        if word.atomic:
            # Atomic word: emit alone, accept the overflow (no legal break).
            yield ShapedLine(words=(word,))
            pending.pop(0)
            continue
        # Non-atomic: split at a cluster boundary. Intra-word splits don't
        # involve `space_advance`.
        fit_word, rest_word = _split_word(word, width)
        if fit_word is None:
            # Even the first cluster doesn't fit; emit as-is, single overflow.
            yield ShapedLine(words=(word,))
            pending.pop(0)
            continue
        yield ShapedLine(words=(fit_word,))
        pending.pop(0)
        if rest_word is not None:
            pending.insert(0, rest_word)
    if current:
        yield ShapedLine(words=tuple(current))


# ---------------------------------------------------------------------------
# Cluster-level wrap
# ---------------------------------------------------------------------------


def _wrap_by_clusters(
    line: ShapedLine, width: int, space_advance: float
) -> Iterator[ShapedLine]:
    clusters = list(_iter_clusters(line))
    if not clusters:
        yield line
        return
    current: list[_Cluster] = []
    current_width: float = 0.0
    current_real_right: float = 0.0
    prev_word_idx: int = -1
    for c in clusters:
        # Insert the inter-word gap when this cluster opens a new word
        # AND that word carried `space_before` AND we already have
        # content on the current line. On a fresh line (current empty)
        # no gap is inserted regardless of how the original line was
        # structured. A new word with `space_before=False` (UAX#29 word
        # break with no source whitespace) packs flush against the
        # previous word's last cluster.
        opens_new_word = c.word_idx != prev_word_idx
        word_wants_gap = opens_new_word and line.words[c.word_idx].space_before
        gap = space_advance if (current and word_wants_gap) else 0.0
        # Test against the visual right edge (the cluster's
        # `real_right` includes any glyph overhang past its advance) —
        # not just the cumulative advance. Otherwise an italic letter
        # at the line edge would have its bitmap clipped.
        new_real_right = max(current_real_right, current_width + gap + c.real_right)
        if current and new_real_right > width:
            yield _build_line(line, current)
            current = []
            current_width = 0.0
            current_real_right = 0.0
            gap = 0.0
            new_real_right = max(0.0, c.real_right)
        current.append(c)
        current_width += gap + c.width
        current_real_right = new_real_right
        prev_word_idx = c.word_idx
    if current:
        yield _build_line(line, current)


# ---------------------------------------------------------------------------
# Cluster iteration and width helpers
# ---------------------------------------------------------------------------


def _iter_clusters(line: ShapedLine) -> Iterator[_Cluster]:
    """Yield clusters in source iteration order (= visual left-to-right
    for LTR runs, visual left-to-right for RTL runs since HarfBuzz
    returned them in visual order)."""
    for w_idx, word in enumerate(line.words):
        for r_idx, run in enumerate(word.runs):
            n = len(run.glyphs)
            i = 0
            while i < n:
                cluster_id = run.glyphs[i].cluster
                j = i + 1
                while j < n and run.glyphs[j].cluster == cluster_id:
                    j += 1
                # Cumulative advance for the cluster, plus visual right
                # edge: walk the glyphs once, tracking pen and the
                # right-most ink boundary they touch. Use the same
                # `int(round(...))` rounding as the rasterizer
                # (`render_run` blits each glyph at
                # `int(round(pen + x_offset + bitmap_left))`), otherwise
                # the wrap engine and the rasterizer disagree on whether
                # a glyph fits inside the surface width.
                pen = 0.0
                real_right = 0.0
                for k in range(i, j):
                    g = run.glyphs[k]
                    draw_x = int(round(pen + g.x_offset + g.ink_left))
                    ink_width = g.ink_right - g.ink_left
                    real_right = max(real_right, draw_x + ink_width)
                    pen += g.x_advance
                width = pen
                real_right = max(real_right, width)
                yield _Cluster(w_idx, r_idx, i, j, width, real_right)
                i = j


def _word_width(word: ShapedWord) -> float:
    return sum(g.x_advance for run in word.runs for g in run.glyphs)


def _word_real_right(word: ShapedWord) -> float:
    """Visual right edge of `word` from its left edge, in pixels.

    Equal to the cumulative advance for most words, but can exceed it
    when a glyph (italic letter, swash, ASCII `f` or `T`, certain
    punctuation) has a bitmap that overhangs its OpenType advance.
    Mirrors the rasterizer's pixel-position arithmetic —
    `int(round(...))` rounding on `pen + x_offset + ink_left` followed
    by adding the integer bitmap width — so the wrap decision matches
    what `render_run` will actually paint and bitmaps never spill past
    the surface edge.
    """
    pen = 0.0
    real_right = 0.0
    for run in word.runs:
        for g in run.glyphs:
            draw_x = int(round(pen + g.x_offset + g.ink_left))
            ink_width = g.ink_right - g.ink_left
            real_right = max(real_right, draw_x + ink_width)
            pen += g.x_advance
    return max(real_right, pen)


# ---------------------------------------------------------------------------
# Reconstruction
# ---------------------------------------------------------------------------


def _build_line(original: ShapedLine, clusters: list[_Cluster]) -> ShapedLine:
    """Reconstruct a `ShapedLine` from a contiguous subset of clusters of
    `original`. Clusters are grouped back into their `ShapedWord` /
    `ShapedRun` shells; partial words / runs get the corresponding subset
    of glyphs, and `source_text` is sliced from the cluster range covered."""
    new_words: list[ShapedWord] = []
    cur_word_idx: int | None = None
    cur_word_runs: list[ShapedRun] = []
    cur_run_idx: int | None = None
    cur_run_glyphs: list[ShapedGlyph] = []

    def _flush_run() -> None:
        nonlocal cur_run_glyphs, cur_run_idx
        if cur_run_glyphs and cur_run_idx is not None and cur_word_idx is not None:
            old_run = original.words[cur_word_idx].runs[cur_run_idx]
            cur_word_runs.append(_subrun(old_run, tuple(cur_run_glyphs)))
            cur_run_glyphs = []

    def _flush_word() -> None:
        nonlocal cur_word_runs
        _flush_run()
        if cur_word_runs and cur_word_idx is not None:
            old_word = original.words[cur_word_idx]
            new_words.append(
                ShapedWord(
                    atomic=old_word.atomic,
                    runs=tuple(cur_word_runs),
                    space_before=old_word.space_before,
                )
            )
            cur_word_runs = []

    for c in clusters:
        if c.word_idx != cur_word_idx:
            _flush_word()
            cur_word_idx = c.word_idx
            cur_run_idx = None
        if c.run_idx != cur_run_idx:
            _flush_run()
            cur_run_idx = c.run_idx
        old_run = original.words[c.word_idx].runs[c.run_idx]
        cur_run_glyphs.extend(old_run.glyphs[c.glyph_start : c.glyph_end])
    _flush_word()

    return ShapedLine(words=tuple(new_words))


def _subrun(old: ShapedRun, glyphs: tuple[ShapedGlyph, ...]) -> ShapedRun:
    """Build a `ShapedRun` from a subset of `old`'s glyphs, slicing
    `source_text` to the cluster range covered. Approximate for RTL runs
    when the subset is a prefix or suffix in visual order: clusters
    decrease in source order, so taking [min_cluster..max_cluster+1]
    yields a contiguous slice that covers exactly the source characters
    represented by the chosen visual glyphs."""
    if glyphs:
        cluster_ids = {g.cluster for g in glyphs}
        lo = min(cluster_ids)
        hi = max(cluster_ids) + 1
        new_source = old.source_text[lo:hi]
    else:
        new_source = ""
    return ShapedRun(
        font_path=old.font_path,
        font_name=old.font_name,
        script=old.script,
        right_to_left=old.right_to_left,
        bold=old.bold,
        italic=old.italic,
        source_text=new_source,
        glyphs=glyphs,
    )


def _split_word(
    word: ShapedWord, max_width: int
) -> tuple[ShapedWord | None, ShapedWord | None]:
    """Split a word so the prefix fits within `max_width`.

    Returns ``(fit_word, rest_word)``. ``fit_word`` is None when even the
    first cluster does not fit; ``rest_word`` is None when the whole word
    fits. Both are None only when the word has no clusters at all
    (degenerate case, never produced by `_iter_clusters`).
    """
    fake_line = ShapedLine(words=(word,))
    clusters = list(_iter_clusters(fake_line))
    if not clusters:
        return None, None
    fit_clusters: list[_Cluster] = []
    cw: float = 0.0
    real_right: float = 0.0
    for c in clusters:
        candidate_real_right = max(real_right, cw + c.real_right)
        if candidate_real_right > max_width and fit_clusters:
            break
        fit_clusters.append(c)
        cw += c.width
        real_right = candidate_real_right
    if not fit_clusters:
        return None, word
    if len(fit_clusters) == len(clusters):
        return word, None
    rest_clusters = clusters[len(fit_clusters) :]
    fit_line = _build_line(fake_line, fit_clusters)
    rest_line = _build_line(fake_line, rest_clusters)
    fit_word = fit_line.words[0] if fit_line.words else None
    rest_word = rest_line.words[0] if rest_line.words else None
    return fit_word, rest_word
