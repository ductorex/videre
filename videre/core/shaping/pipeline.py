from typing import Iterator

from videre.core.shaping.shaped import ShapedLine, ShapedRun, ShapedWord
from videre.core.shaping.shaper import Shaper
from videre.core.shaping.textutils import split_text_to_renderable


def shape_text(
    text: str,
    size_px: int,
    *,
    shaper: Shaper | None = None,
    split_words: bool = True,
    bold: bool = False,
    italic: bool = False,
) -> Iterator[ShapedLine]:
    """Pipeline: textutils segmentation -> HarfBuzz shaping.

    For each input line, splits into `RenderableText` (one per word) via
    `split_text_to_renderable`. Each `RenderablePiece` of a word becomes a
    `ShapedRun`, and all runs of the same word are grouped under one
    `ShapedWord` so the wrap engine knows the word boundary even for
    multi-font / multi-script words. The word's `atomic` and
    `space_before` flags are propagated to `ShapedWord`: `atomic` lets
    the wrap engine decide whether to break inside the word
    (atomic=False, e.g. CJK runs) or only between words; `space_before`
    lets the renderer / wrap engine insert a `space_advance` only where
    a real source whitespace existed (so `"Hello世界"`, where UAX#29
    splits between `Hello` and `世` without any whitespace, renders
    flush instead of with a phantom gap).
    `bold` and `italic` apply synthetic emboldening / slant to the entire
    text via HarfBuzz; per-word variants are not supported here, the whole
    paragraph is shaped with the same flags.
    """
    s = shaper or Shaper()
    for line in split_text_to_renderable(text, split_words=split_words):
        words: list[ShapedWord] = []
        for rt in line.elements:
            word_runs: list[ShapedRun] = []
            for piece in rt.pieces:
                glyphs = s.shape(
                    text=piece.text,
                    font_path=piece.font_path,
                    size_px=size_px,
                    script=piece.script,
                    right_to_left=piece.right_to_left,
                    bold=bold,
                    italic=italic,
                )
                word_runs.append(
                    ShapedRun(
                        font_path=piece.font_path,
                        font_name=piece.font_name,
                        script=piece.script,
                        bidi_level=piece.bidi_level,
                        bold=bold,
                        italic=italic,
                        source_text=piece.text,
                        glyphs=glyphs,
                    )
                )
            words.append(
                ShapedWord(
                    atomic=rt.atomic,
                    runs=tuple(word_runs),
                    space_before=rt.space_before,
                )
            )
        yield ShapedLine(words=tuple(words), bidi_base_level=line.bidi_base_level)
