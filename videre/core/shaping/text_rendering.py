from videre.colors import Color, Colors
from videre.core.abstract_backend import AbstractBackend
from videre.core.constants import TextAlign
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import AbstractTextRendering, Rendering
from videre.core.shaping.layout import (
    FontMetrics,
    ShapedRenderedText,
    _LineItem,
    _LineLayout,
)
from videre.core.shaping.pipeline import shape_text
from videre.core.shaping.rasterizer import Glyph, GlyphArea, GlyphRasterizer
from videre.core.shaping.shaped import ShapedLine, ShapedWord
from videre.core.shaping.shaper import Shaper
from videre.core.shaping.text_partition.partition_func import get_font_provider
from videre.core.shaping.utils import (
    SYNTHETIC_BOLD_STRENGTH,
    line_metrics,
    space_advance,
    underline_metrics,
)
from videre.core.shaping.wrap import wrap_lines

# Translucent blue selection highlight, matching the legacy
# `PygameTextRendering._render_word_lines_old` color
# `(100, 100, 255, 100)`. The alpha is essential: glyphs are blitted
# OVER the selection so a fully opaque rectangle would tint the text.
_SELECTION_RGBA = Color(100, 100, 255, 100)


class ShapedTextRendering(AbstractTextRendering):
    """Text renderer based on the HarfBuzz Shaper + freetype-py GlyphRasterizer.

    Independent from `PygameTextRendering`, the legacy renderer in
    `videre.core.fontfactory.pygame_text_rendering`. This module produces a
    pygame Surface from a multi-line string with proper script shaping
    (Arabic contextual forms, Indic reordering, Thai mark positioning, Latin
    ligatures), synthetic bold/italic that grow advances rather than
    overlap, and per-script font routing.

    Scope: vertical stacking of lines at a fixed `line_spacing`
    (font-defined line height + `height_delta` extra pixels), horizontal
    juxtaposition of script runs, single foreground color, optional
    synthetic bold/italic and optional underline (drawn per-line at the
    font's natural position without resizing the line box), word- and
    cluster-level wrap, horizontal alignment (LEFT / CENTER / RIGHT /
    JUSTIFY), translucent selection highlight, and a layout-info
    return value (`ShapedRenderedText`) paired with a pygame-rendered
    result. The layout result exposes per-line / per-cluster pixel
    ranges for caret positioning and hit-testing.

    When `compact=True` (default), the first baseline sits at
    `ascender + height_delta` from the top, dropping the leading line
    gap so widgets like buttons and labels do not waste vertical space;
    set it to False for paragraph-style layout.
    """

    __slots__ = (
        "_backend",
        "_size",
        "_bold",
        "_italic",
        "_underline",
        "_height_delta",
        "_compact",
        "_subpixel",
        "_shaper",
        "_rasterizer",
        "_ascender",
        "_descender",
        "_line_spacing",
        "_space_advance",
    )

    def __init__(
        self,
        backend: AbstractBackend,
        size: int = 14,
        bold: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int = 2,
        compact: bool = True,
        subpixel: bool = False,
        *,
        shaper: Shaper | None = None,
        rasterizer: GlyphRasterizer | None = None,
    ) -> None:
        self._backend = backend
        self._size = size
        self._bold = bold
        self._italic = italic
        self._underline = underline
        self._height_delta = height_delta
        self._compact = compact
        # When True, each glyph is blitted at its sub-pixel-quantized
        # position (4 phases). Keeps multi-script kerning and GPOS mark
        # offsets accurate at the cost of a 4× glyph-cache footprint
        # under `GlyphRasterizer`. Default `False` (pixel-aligned) keeps
        # the cache compact for UI use; opt in for paragraph rendering.
        self._subpixel = subpixel
        self._shaper = shaper or Shaper()
        self._rasterizer = rasterizer or GlyphRasterizer()

        # Reference font for line metrics: whatever the FontProvider picks
        # for a regular space. Keeps line spacing deterministic and
        # independent of the rendered text. Multi-script content with
        # uncommonly tall ascenders (some Indic, some Arabic with stacked
        # marks) may overflow this by a couple of pixels; matches what
        # PygameTextRendering does. The provider call is lru-cached, so
        # this stays cheap even when many ShapedTextRendering instances
        # are created.
        _, ref_path = get_font_provider().get_font_info(" ")
        asc, desc, line_h = line_metrics(ref_path, size)
        self._ascender = asc
        self._descender = desc
        self._line_spacing = line_h + height_delta
        # Inter-word advance, computed once on the reference font (matches
        # PygameTextRendering's `space_shift`). The space character is never
        # stored or shaped as a glyph in the shaped pipeline; instead each
        # word boundary in the layout contributes this advance.
        self._space_advance = space_advance(ref_path, size)

    def render_char(self, c: str, color: Color | None = None) -> Rendering:
        """Rasterize a single character to a tightly-fitted Surface.

        Drop-in replacement for the legacy
        `PygameTextRendering.render_char`: returns just the glyph
        bitmap (no advance padding, no baseline padding), so consumers
        like the `Character` widget — and through it `Checkbox` /
        `Radio` for their `☐ ☑ ○ ◉` symbols — get a surface sized to
        the visible ink. Empty input or unsupported / non-printable
        characters yield a zero-size surface.

        Routes through the full shaping pipeline (font selection,
        script resolution, HarfBuzz shaping) for consistency with
        `render_text`, then extracts the first glyph's bitmap. For
        single characters this is one HarfBuzz call followed by a
        cache lookup; the per-glyph cache means repeated
        `Checkbox`/`Radio` redraws are essentially free.
        `bold`/`italic`/`underline` from the constructor: bold and
        italic are honored via synthetic transforms; underline is
        intentionally NOT applied (matches legacy behavior, where
        `render_char` skipped the per-line underline pass).
        """
        color = color or Colors.black
        if not c:
            return self._backend.zero()
        lines = list(
            shape_text(
                c,
                self._size,
                shaper=self._shaper,
                split_words=False,
                bold=self._bold,
                italic=self._italic,
            )
        )
        if not lines or lines[0].is_empty():
            return self._backend.zero()
        word = lines[0].words[0]
        if not word.runs or not word.runs[0].glyphs:
            return self._backend.zero()
        run = word.runs[0]
        shaped_glyph = run.glyphs[0]
        glyph = self._rasterizer.render_single_glyph(
            run.font_path,
            self._size,
            run.bold,
            run.italic,
            shaped_glyph.glyph_id,
            color,
        )
        return self._glyph_to_surface(glyph)

    @property
    def font_metrics(self) -> FontMetrics:
        """Reference-font metrics used for line stacking. Exposed so
        `widgets/textinput` can size cursors / selection rectangles
        without recomputing them from the rendered surface."""
        return FontMetrics(
            ascender=self._ascender,
            descender=self._descender,
            height_delta=self._height_delta,
            line_spacing=self._line_spacing,
        )

    def render_text(
        self,
        text: str,
        width: int | None = None,
        *,
        color: Color | None = None,
        align: TextAlign | None = None,
        wrap_words: bool = False,
        selection: tuple[int, int] | None = None,
    ) -> tuple[ShapedRenderedText, Rendering]:
        color = color or Colors.black

        # `split_words=True` only matters when wrapping: it gives the
        # wrap engine real word boundaries to break on. With wrap off
        # there is no benefit to word segmentation; keep the legacy
        # behavior of one ShapedWord per script run to avoid the
        # uniseg-based segmentation overhead in the common case.
        split_words = width is not None
        paragraphs: list[ShapedLine] = list(
            shape_text(
                text,
                self._size,
                shaper=self._shaper,
                split_words=split_words,
                bold=self._bold,
                italic=self._italic,
            )
        )
        # Wrap paragraph by paragraph so we know which wrapped sub-lines
        # close a source paragraph. JUSTIFY needs this distinction: the
        # last line of each paragraph stays left-aligned (matches CSS,
        # browsers, Word). LEFT/CENTER/RIGHT ignore the flag.
        # We also accumulate the source-position offset of each emitted
        # line so `selection` can be mapped from logical positions
        # (matching the printable-source convention) to pixel rectangles. The
        # whitespace consumed by a line break (the source space that
        # was BETWEEN sub-line N and sub-line N+1) lives in `pos`
        # between the two and is not charged to either sub-line's
        # length — see `ShapedLine.source_length`.
        lines: list[ShapedLine] = []
        is_paragraph_end: list[bool] = []
        line_source_offsets: list[int] = []
        # Per-line tuple of source offsets (relative to the line start)
        # for each word **in visual order** after L2. Captured before
        # reordering so `_build_line_layout` can still place source
        # positions correctly when visual order != source order.
        line_word_source_offsets: list[tuple[int, ...]] = []
        # Per-line per-word tuple of run source offsets (within the
        # word). Needed because L2 may reorder runs inside a word too
        # (e.g. a single word straddling two bidi levels).
        line_run_source_offsets: list[tuple[tuple[int, ...], ...]] = []
        pos = 0
        for p_idx, p in enumerate(paragraphs):
            if width is not None:
                sub = list(
                    wrap_lines(
                        [p],
                        width,
                        wrap_words=wrap_words,
                        space_advance=self._space_advance,
                    )
                )
            else:
                sub = [p]
            if not sub:
                if p_idx < len(paragraphs) - 1:
                    pos += 1
                continue
            for sl_idx, sl in enumerate(sub):
                if sl_idx > 0 and sl.words and sl.words[0].space_before:
                    # Inter-sub-line whitespace consumed by the wrap.
                    pos += 1
                # Apply UAX#9 L2 visual reordering at word + run
                # granularity. In pure-LTR / single-RTL-run layouts the
                # result is the identity, so this is a no-op for the
                # common case.
                sl_visual, word_offsets, run_offsets = _apply_l2_to_line(sl)
                line_source_offsets.append(pos)
                lines.append(sl_visual)
                line_word_source_offsets.append(word_offsets)
                line_run_source_offsets.append(run_offsets)
                is_paragraph_end.append(sl_idx == len(sub) - 1)
                pos += sl.source_length()
            if p_idx < len(paragraphs) - 1:
                pos += 1  # newline between paragraphs

        # `compact` drops the leading `line_gap` for content-on-first-line
        # and for the degenerate empty-input case (a single empty line, kept
        # tight). An explicit `\n` at the start — i.e. multiple lines with
        # the first one empty — is a user-authored gap that must keep its
        # full `line_spacing`, otherwise paragraphs starting with a blank
        # line collapse by `line_gap` px. Matches legacy and CSS/Word.
        compact_first = self._compact and (len(lines) <= 1 or not lines[0].is_empty())
        first_baseline = (
            self._ascender + self._height_delta if compact_first else self._line_spacing
        )
        if not lines:
            # Empty input: still produce a surface of one full line so
            # downstream layout reserves the right vertical slot.
            total_height = first_baseline + self._descender
            surface_h = max(total_height, 1)
            empty_surface = self._backend.new_surface(1, surface_h)
            return ShapedRenderedText(
                font_metrics=self.font_metrics,
                line_layouts=(),
                width=1,
                height=surface_h,
            ), empty_surface

        # Two-pass rendering for JUSTIFY: a first pass measures each line
        # at its natural inter-word gap so we know the slack, then a
        # second pass re-renders justifiable lines with widened gaps.
        # LEFT/CENTER/RIGHT don't need the second pass — they only shift
        # x-offset at blit time. Compute target_width from the natural
        # measure (so `width=None` still produces a tight surface).
        natural: list[tuple[Rendering, int, int]] = [
            self._render_line(line, color) for line in lines
        ]
        natural_max = max(lw for _, _, lw in natural)
        target_width = width if width is not None else natural_max

        n = len(lines)
        baselines = [first_baseline + i * self._line_spacing for i in range(n)]
        total_height = baselines[-1] + self._descender

        # Decide per line whether to re-render with a justified gap, and
        # the x-offset at blit time. Track the per-line `extra_word_gap`
        # so the layout helper can build pixel ranges with matching gaps.
        rendered: list[tuple[Rendering, int, int]] = []
        x_offsets: list[int] = []
        line_extra_gaps: list[float] = []
        for i, (line, n_render) in enumerate(zip(lines, natural)):
            surface, baseline, line_width = n_render
            extra: float = 0.0
            if (
                align is TextAlign.JUSTIFY
                and width is not None
                and not is_paragraph_end[i]
            ):
                n_gaps = sum(
                    1
                    for w_idx, w in enumerate(line.words)
                    if w_idx > 0 and w.space_before
                )
                slack = target_width - line_width
                if n_gaps > 0 and slack > 0:
                    extra = slack / n_gaps
                    surface, baseline, line_width = self._render_line(
                        line, color, extra_word_gap=extra
                    )
            rendered.append((surface, baseline, line_width))
            x_offsets.append(_align_x_offset(align, line_width, target_width))
            line_extra_gaps.append(extra)

        # Build the per-line layouts (for cursor / selection helpers).
        line_layouts: list[_LineLayout] = []
        for i, line in enumerate(lines):
            top_y = baselines[i] - self._ascender
            line_layouts.append(
                _build_line_layout(
                    line=line,
                    line_source_offset=line_source_offsets[i],
                    y_top=top_y,
                    y_bottom=top_y + self._ascender + self._descender,
                    x_offset=x_offsets[i],
                    extra_word_gap=line_extra_gaps[i],
                    space_advance=self._space_advance,
                    word_source_offsets=line_word_source_offsets[i],
                    run_source_offsets_per_word=line_run_source_offsets[i],
                )
            )

        surface_w = max(target_width, 1)
        surface_h = max(total_height, 1)
        out = self._backend.new_surface(surface_w, surface_h)

        rendered_text = ShapedRenderedText(
            font_metrics=self.font_metrics,
            line_layouts=tuple(line_layouts),
            width=surface_w,
            height=surface_h,
        )

        # Pass 1: paint the selection background (translucent) BEFORE
        # blitting glyphs. The order matters: selection must sit behind
        # the glyphs so it doesn't tint them. We use `gfxdraw.box` for
        # alpha-correct fills (`draw.rect` ignores the alpha channel).
        # `selection` is a half-open range of *visual* positions; the
        # backend returns one rectangle per line touched, each a
        # contiguous pixel ribbon (items being in visual pixel order).
        if selection is not None and selection[0] < selection[1]:
            for rect in rendered_text.visual_selection_rects(*selection):
                self._backend.box(out, rect, _SELECTION_RGBA)

        # Pass 2: glyphs (each line surface includes its underline).
        for (surface, intrinsic_baseline, _), baseline, x in zip(
            rendered, baselines, x_offsets
        ):
            self._backend.blit(out, surface, (x, baseline - intrinsic_baseline))
        return rendered_text, out

    def _render_line(
        self, line: ShapedLine, color: Color, *, extra_word_gap: float = 0.0
    ) -> tuple[Rendering, int, int]:
        """Render a single line.

        Returns ``(surface, baseline_y_in_surface, line_width)``. The
        surface holds only the glyphs (and underline if requested), tightly
        sized; the caller is responsible for placing it so its baseline
        aligns with the line's global baseline.

        ``extra_word_gap`` (in pixels) widens each inter-word gap on top
        of the natural ``space_advance``. Used by JUSTIFY in
        `render_text` to spread the slack of a non-final line across its
        word boundaries; defaults to 0 for the LEFT/CENTER/RIGHT path.
        """
        if line.is_empty():
            # Empty line: zero-width surface, baseline at the reference
            # ascender (so the line still occupies one full slot vertically
            # via the global baseline arithmetic).
            return self._backend.zero(), self._ascender, 0

        # Per-run tuples: (surface, baseline, gap_before). `gap_before`
        # is True only on the *first* run of a word that the source put
        # behind a whitespace separator (`ShapedWord.space_before`), and
        # is forced False on the very first run of the line so we never
        # leave a leading indent. Two consecutive words with no source
        # whitespace between them (e.g. `Hello` and `世界` in
        # `"Hello世界"` after UAX#29 segmentation) carry `space_before=
        # False` and are blitted flush.
        rendered: list[tuple[Rendering, int, bool]] = []
        for w_idx, word in enumerate(line.words):
            gap_before_word = w_idx > 0 and word.space_before
            for r_idx, run in enumerate(word.runs):
                area = self._rasterizer.render_run(
                    run, self._size, color, subpixel=self._subpixel
                )
                surf = self._glyph_area_to_surface(area)
                baseline = area.baseline_y
                rendered.append((surf, baseline, r_idx == 0 and gap_before_word))
        if not rendered:
            return self._backend.zero(), self._ascender, 0
        max_baseline = max(b for _, b, _ in rendered)
        max_below = max(s.get_height() - b for s, b, _ in rendered)
        line_height = max_baseline + max_below
        gap = int(round(self._space_advance + extra_word_gap))
        runs_width = sum(s.get_width() for s, _, _ in rendered)
        n_gaps = sum(1 for _, _, has_gap in rendered if has_gap)
        line_width = runs_width + gap * n_gaps
        out = self._backend.new_surface(max(line_width, 1), line_height)
        x = 0
        for s, b, has_gap in rendered:
            if has_gap:
                x += gap
            self._backend.blit(out, s, (x, max_baseline - b))
            x += s.get_width()

        if self._underline and line_width > 0:
            # Standard typographic behavior (CSS, browsers, Word): the
            # underline is drawn at the font-defined position without
            # adjusting the line box. If `offset + thickness` overflows
            # the descender, the overflow falls into the inter-line gap
            # (or, when no gap exists, gets clipped at the surface bottom).
            # Resizing the line box per-line would make paragraph heights
            # depend on whether text is underlined, breaking layout stability.
            ul_offset, ul_thickness = underline_metrics(
                line.words[0].runs[0].font_path, self._size
            )
            if self._bold:
                # Thicken the underline to mimic what a native bold font
                # variant would carry. Real bold variants typically declare
                # `post.underlineThickness` ≈ 2× the regular's (Noto, Roboto,
                # Helvetica…), so adding `2 * strength * size_px` here gets
                # us close to the same effective doubling for synthetic bold.
                ul_thickness += int(round(2 * SYNTHETIC_BOLD_STRENGTH * self._size))
            self._backend.rectangle(
                out,
                Rectangle(0, max_baseline + ul_offset, line_width, ul_thickness),
                color,
            )

        return out, max_baseline, line_width

    def _glyph_to_surface(self, glyph: Glyph) -> Rendering:
        if glyph.image is None:
            return self._backend.zero()
        return self._backend.image_from_bytes(
            glyph.image.tobytes(), (glyph.width, glyph.height)
        )

    def _glyph_area_to_surface(self, area: GlyphArea) -> Rendering:
        surface = self._backend.new_surface(area.width, area.height)
        for sprite, blit_x, blit_y in area.glyphs:
            if sprite.empty():
                continue
            self._backend.blit(
                surface,
                self._glyph_to_surface(sprite),
                (blit_x, area.baseline_y + blit_y),
            )
        return surface


def _apply_l2_to_line(
    line: ShapedLine,
) -> tuple[ShapedLine, tuple[int, ...], tuple[tuple[int, ...], ...]]:
    """Apply UAX#9 rule L2 visual reordering at two granularities:

    1. Within each `ShapedWord`, reorder its runs in visual order
       (matters when a word straddles bidi levels — e.g. a paragraph
       rendered as a single word in ``split_words=False`` mode whose
       runs span both LTR and RTL chunks).
    2. Reorder the words of the line in visual order (matters when
       several words on a line have different bidi levels).

    Returns ``(reordered_line, word_source_offsets,
    run_source_offsets_per_word)``: the source offset (within the line,
    pre-`line_source_offset` shift) of each visual word, and within
    each visual word the source offset (relative to the word's first
    codepoint in source order) of each visual run. `_build_line_layout`
    uses these to place source positions correctly when visual order
    differs from source order.
    """
    if not line.words:
        return line, (), ()
    base_level = line.bidi_base_level
    # Step 1: per-word reorder of runs.
    word_source_offsets: list[int] = []
    new_words_intermediate: list[ShapedWord] = []
    run_source_offsets_per_word: list[tuple[int, ...]] = []
    cumulative = 0
    for w_idx, w in enumerate(line.words):
        if w_idx > 0 and w.space_before:
            cumulative += 1
        word_source_offsets.append(cumulative)
        # Compute each run's source offset within the word (in source
        # order), then L2-reorder the runs.
        run_offsets_source_order: list[int] = []
        run_cumulative = 0
        for r in w.runs:
            run_offsets_source_order.append(run_cumulative)
            run_cumulative += len(r.source_text)
        cumulative += run_cumulative
        run_levels = [r.bidi_level for r in w.runs]
        run_perm = _l2_reorder(run_levels, base_level)
        reordered_runs = tuple(w.runs[i] for i in run_perm)
        reordered_run_offsets = tuple(run_offsets_source_order[i] for i in run_perm)
        new_words_intermediate.append(
            ShapedWord(
                atomic=w.atomic, runs=reordered_runs, space_before=w.space_before
            )
        )
        run_source_offsets_per_word.append(reordered_run_offsets)
    # Step 2: word-level reorder.
    word_levels = [
        w.runs[0].bidi_level if w.runs else base_level for w in new_words_intermediate
    ]
    word_perm = _l2_reorder(word_levels, base_level)
    new_words = tuple(new_words_intermediate[i] for i in word_perm)
    new_offsets = tuple(word_source_offsets[i] for i in word_perm)
    new_run_offsets = tuple(run_source_offsets_per_word[i] for i in word_perm)
    new_line = ShapedLine(words=new_words, bidi_base_level=base_level)
    return new_line, new_offsets, new_run_offsets


def _l2_reorder(levels: list[int], base_level: int) -> list[int]:
    """Apply UAX#9 rule L2 to a sequence of items identified by their
    bidi levels. Returns the permutation (a list of source indices in
    visual order) that visually reorders the items left-to-right.

    L2: from the highest level present down to ``min(base_level | 1,
    lowest_odd_level)``, reverse every maximal sub-sequence whose
    levels are >= that threshold. Levels at or below `base_level` are
    never reversed. For a pure-LTR paragraph (`base_level == 0`) with
    all-zero levels the result is the identity; for a paragraph with a
    single isolated RTL run the result is also the identity (the run
    is one item, reversing one element is a no-op); only when several
    items have level >= the threshold does the order actually change.
    """
    n = len(levels)
    if n == 0:
        return []
    order = list(range(n))
    highest = max(levels)
    # The lowest level that is allowed to be reversed: the lowest odd
    # level in the paragraph, but no lower than `base_level | 1`
    # (which is `base_level + 1` if base is even, `base_level` if odd).
    odd_levels = [lv for lv in levels if lv % 2 == 1]
    if not odd_levels:
        return order
    lowest_odd = min(odd_levels)
    floor = max(lowest_odd, base_level | 1)
    for threshold in range(highest, floor - 1, -1):
        i = 0
        while i < n:
            if levels[order[i]] >= threshold:
                j = i
                while j + 1 < n and levels[order[j + 1]] >= threshold:
                    j += 1
                order[i : j + 1] = reversed(order[i : j + 1])
                i = j + 1
            else:
                i += 1
    return order


def _align_x_offset(align: TextAlign | None, line_width: int, target_width: int) -> int:
    """X-position of a line within the output surface for a given align.

    LEFT (default), JUSTIFY (handled separately by gap stretching), and
    None all flush left. CENTER splits the slack evenly; RIGHT pushes
    the line to the right edge. The returned offset is clamped to >= 0
    so an over-wide line (atomic word overflowing the box) never gets
    a negative x.
    """
    if align is None or align is TextAlign.LEFT or align is TextAlign.JUSTIFY:
        return 0
    slack = max(0, target_width - line_width)
    if align is TextAlign.CENTER:
        return slack // 2
    if align is TextAlign.RIGHT:
        return slack
    return 0


def _build_line_layout(
    line: ShapedLine,
    line_source_offset: int,
    y_top: int,
    y_bottom: int,
    x_offset: int,
    extra_word_gap: float,
    space_advance: float,
    word_source_offsets: tuple[int, ...],
    run_source_offsets_per_word: tuple[tuple[int, ...], ...],
) -> _LineLayout:
    """Build a `_LineLayout` for the rendered line.

    Walks word/run/cluster in the order in which the line is painted
    (post-L2 visual order, see `_l2_reorder` in `render_text`),
    emitting one `_LineItem` per HarfBuzz cluster (a group of glyphs
    sharing one source-index) and one per inter-word gap. The pixel
    positions inside the line use the same gap arithmetic as
    `_render_line` (and the same JUSTIFY-driven `extra_word_gap`), so
    caret / selection helpers stay aligned with what was actually
    painted.

    For RTL runs, HarfBuzz returns glyphs in visual order (left-to-
    right pixel-wise) with cluster ids decreasing in source order.
    Each cluster's source extent is recovered by looking at the
    *previous* visual glyph's cluster id (which is the *next* in
    source order) — symmetric to LTR where we look at the next
    visual glyph. Items carry their `bidi_level` (and a derived
    `right_to_left`) so caret helpers can flip the visual-edge
    interpretation.

    Source positions inside `pos` advance in *source* order across the
    line (using each run's `source_text` length), but `pixel_x`
    advances in *visual* order; the result is items whose
    `(source_start, source_end)` ranges are non-monotonic in mixed
    bidi but whose `(x_start, x_end)` ranges are strictly increasing.
    """
    items: list[_LineItem] = []
    pixel_x = 0.0
    gap_px = space_advance + extra_word_gap
    base_level = line.bidi_base_level
    assert len(word_source_offsets) == len(line.words)
    assert len(run_source_offsets_per_word) == len(line.words)
    for w_idx, word in enumerate(line.words):
        word_src = line_source_offset + word_source_offsets[w_idx]
        if w_idx > 0 and word.space_before:
            # Source position of the gap: it sits at `word_src - 1` (the
            # whitespace that lives just before this word in source
            # order, regardless of where the word lands visually after
            # L2). Pixel position is the current visual cursor.
            items.append(
                _LineItem(
                    source_start=word_src - 1,
                    source_end=word_src,
                    x_start=int(round(pixel_x)),
                    x_end=int(round(pixel_x + gap_px)),
                    bidi_level=base_level,
                )
            )
            pixel_x += gap_px
        run_offsets = run_source_offsets_per_word[w_idx]
        assert len(run_offsets) == len(word.runs)
        for r_idx, run in enumerate(word.runs):
            # `pos` is the source position of this run's first codepoint
            # in source order, regardless of where this run lands
            # visually after L2.
            pos = word_src + run_offsets[r_idx]
            rtl = run.right_to_left
            run_source_len = len(run.source_text)
            n = len(run.glyphs)
            i = 0
            while i < n:
                cluster_id = run.glyphs[i].cluster
                j = i + 1
                while j < n and run.glyphs[j].cluster == cluster_id:
                    j += 1
                if rtl:
                    # Previous glyph in visual order is the next in
                    # source order; if none, this cluster reaches the
                    # run's source end.
                    if i == 0:
                        next_in_source = run_source_len
                    else:
                        next_in_source = run.glyphs[i - 1].cluster
                else:
                    if j < n:
                        next_in_source = run.glyphs[j].cluster
                    else:
                        next_in_source = run_source_len
                cluster_source_start = pos + cluster_id
                cluster_source_end = pos + next_in_source
                cluster_pixel_width = sum(g.x_advance for g in run.glyphs[i:j])
                items.append(
                    _LineItem(
                        source_start=cluster_source_start,
                        source_end=cluster_source_end,
                        x_start=int(round(pixel_x)),
                        x_end=int(round(pixel_x + cluster_pixel_width)),
                        bidi_level=run.bidi_level,
                    )
                )
                pixel_x += cluster_pixel_width
                i = j
    return _LineLayout(
        y_top=y_top,
        y_bottom=y_bottom,
        x_offset=x_offset,
        source_offset=line_source_offset,
        source_length=line.source_length(),
        items=tuple(items),
    )
