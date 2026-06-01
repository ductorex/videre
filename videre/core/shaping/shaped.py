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

    The source text was already split so that this run uses a single
    font, single script and single bidi level. `bold` / `italic` record
    whether synthetic bold or slant was applied during shaping; the
    rasterizer needs them to apply matching outline transformations on
    each glyph so positions and pixels stay aligned.
    """

    font_path: str
    font_name: str
    script: str
    bidi_level: int
    bold: bool
    italic: bool
    source_text: str
    glyphs: tuple[ShapedGlyph, ...]

    @property
    def right_to_left(self) -> bool:
        """Derived from the UAX#9 bidi level (odd = RTL)."""
        return self.bidi_level % 2 == 1
