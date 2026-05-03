from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class ShapedGlyph:
    """A single glyph as produced by HarfBuzz, with positions in pixels.

    `cluster` is the Python index of the source character in the
    `ShapedRun.source_text` string, such that `source_text[g.cluster]`
    yields the source character (or the first one when several codepoints
    collapsed into a single cluster via a ligature or Indic reordering).
    It is NOT a UTF-8 byte index nor a UTF-16 code-unit index; we feed
    HarfBuzz with `Buffer.add_str` which works on Python codepoints.
    When one codepoint produces several glyphs (decomposition), they all
    carry that codepoint's cluster. Clusters are monotonic for LTR runs
    and reversed for RTL runs (HarfBuzz returns glyphs in visual order).
    Use it to find legal break positions: two consecutive glyphs with
    different clusters delimit a cluster boundary safe to wrap on.

    `ink_left` / `ink_right` describe the glyph's bitmap bounding box
    along the x-axis, **in pixels and relative to the glyph's origin**
    (= `pen_x + x_offset` at draw time). They come straight from
    HarfBuzz `font.get_glyph_extents` (`x_bearing` and
    `x_bearing + width` respectively). Most glyphs have
    `ink_right <= x_advance`, but italic letters and a few sidebearing-
    light glyphs (e.g. `f`, `T`, certain punctuation, RTL letters with
    swashes) overhang past the advance — which means the wrap engine
    must compare the cluster's effective right edge to the available
    width, not just the cumulative advance.
    """

    glyph_id: int
    cluster: int
    x_advance: float
    y_advance: float
    x_offset: float
    y_offset: float
    ink_left: float = 0.0
    ink_right: float = 0.0


@dataclass(slots=True, frozen=True)
class ShapedRun:
    """One contiguous run of glyphs that share the same font and script.

    Mirrors a `RenderablePiece` from `textutils` after shaping: the text
    was already split so that this run uses a single font and single script.
    `bold` / `italic` record whether synthetic bold or slant was applied
    during shaping; the rasterizer needs them to apply matching outline
    transformations on each glyph so positions and pixels stay aligned.
    The `atomic` flag lives one level up on `ShapedWord`, since a single
    word may span several runs when its characters require several fonts
    (e.g. Latin letters mixed with combining marks served by a fallback).
    """

    font_path: str
    font_name: str
    script: str
    right_to_left: bool
    bold: bool
    italic: bool
    source_text: str
    glyphs: tuple[ShapedGlyph, ...]


@dataclass(slots=True, frozen=True)
class ShapedWord:
    """One word's worth of shaped runs.

    Mirrors a `RenderableText` from `textutils` after shaping. A word is
    typically a single run, but multi-font (or multi-script) words become
    several runs grouped under one `ShapedWord`. Multi-script words are
    rare but legal here: UAX#29 word boundaries do not always coincide
    with script boundaries, so a single linguistic word may contain runs
    of different scripts (e.g. a base letter and a combining mark from a
    different script).

    `atomic` is propagated from the source `RenderableText` and tells the
    wrap engine whether the word must stay on a single line (True) or may
    be broken between two cluster boundaries within one of its runs
    (False, e.g. CJK or SE-Asian content).

    `space_before` is True when the source had whitespace immediately
    before this word; the renderer inserts a `space_advance` gap in front
    of such words (except for the first word of a line, where the leading
    gap is always suppressed).
    """

    atomic: bool
    runs: tuple[ShapedRun, ...]
    space_before: bool = False


@dataclass(slots=True, frozen=True)
class ShapedLine:
    """One line worth of shaped words, before any width-based wrapping."""

    words: tuple[ShapedWord, ...]

    def is_empty(self) -> bool:
        return not self.words

    def source_length(self) -> int:
        """Number of source codepoints this line covers, post-printable
        filter (matches what `TextSequence` indexes into).

        Counts the characters of every run plus one position per
        inter-word source whitespace (ie. words with `space_before`,
        excluding the first word of the line — its `space_before` either
        is False or, for a wrap-induced sub-line, represents the
        whitespace consumed by the wrap that lives between *this* sub-
        line and the previous one and therefore belongs to *this*
        sub-line's offset, not its length).
        """
        total = sum(len(r.source_text) for w in self.words for r in w.runs)
        # Skip word 0: a leading whitespace before the first word of a
        # wrapped sub-line is accounted for by that sub-line's
        # source_offset increase, not by this sub-line's own length.
        for i in range(1, len(self.words)):
            if self.words[i].space_before:
                total += 1
        return total
