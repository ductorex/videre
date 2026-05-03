from typing import Iterable, Iterator

from videre.core.shaping.texts.textutils import RenderableLine


class TextSequence:
    """Character-indexed view over the output of `split_text_to_renderable`.

    Wraps a renderable-line stream so it behaves like a flat sequence of
    characters. `len()`, integer indexing and slicing return Python str
    matching the original input as preserved by the segmentation, with
    a single '\\n' inserted between consecutive `RenderableLine` to
    mirror what `_split_by_line` consumed. Unprintable characters are
    not preserved (they are stripped during segmentation).

    Iteration walks lines / texts / pieces in source order: it follows
    the *logical* order of the original string, not the visual order of
    the rendered output. RTL segments are still stored in their logical
    order at this layer; visual order only emerges after shaping (each
    `ShapedRun.glyphs` is in visual order, with `cluster` mapping back
    to a logical index in `source_text`). `TextSequence` sits one level
    upstream and stays direction-agnostic.

    Useful for testing the segmentation: `str(TextSequence(...))` must
    equal the input string for any input made of printable characters
    (modulo `\\r\\n` / `\\r` normalization to `\\n`). Slicing lets one
    feed progressive prefixes/substrings to the shaping pipeline to
    inspect how each chunk renders independently.
    """

    __slots__ = ("_lines",)

    def __init__(self, lines: Iterable[RenderableLine]) -> None:
        self._lines: tuple[RenderableLine, ...] = tuple(lines)

    @property
    def lines(self) -> tuple[RenderableLine, ...]:
        return self._lines

    def _iter_chars(self) -> Iterator[str]:
        first_line = True
        for line in self._lines:
            if not first_line:
                yield "\n"
            first_line = False
            for el_idx, el in enumerate(line.elements):
                # In `split_words=True` mode, source whitespace was
                # consumed during segmentation; reinsert one space per
                # element that carried `space_before`. In
                # `split_words=False` mode the whitespace is still
                # inside the piece text and `space_before` is always
                # False, so this branch is a no-op.
                if el_idx > 0 and el.space_before:
                    yield " "
                for p in el.pieces:
                    yield from p.text

    def __len__(self) -> int:
        n = 0
        first_line = True
        for line in self._lines:
            if not first_line:
                n += 1
            first_line = False
            for el_idx, el in enumerate(line.elements):
                if el_idx > 0 and el.space_before:
                    n += 1
                for p in el.pieces:
                    n += len(p.text)
        return n

    def __getitem__(self, key: int | slice) -> str:
        if isinstance(key, slice):
            return "".join(list(self._iter_chars())[key])
        n = len(self)
        index = key + n if key < 0 else key
        if index < 0 or index >= n:
            raise IndexError("TextSequence index out of range")
        for i, c in enumerate(self._iter_chars()):
            if i == index:
                return c
        raise IndexError("TextSequence index out of range")

    def __iter__(self) -> Iterator[str]:
        return self._iter_chars()

    def __str__(self) -> str:
        return "".join(self._iter_chars())

    def __repr__(self) -> str:
        return f"TextSequence({str(self)!r})"
