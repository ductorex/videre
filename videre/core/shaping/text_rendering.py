import pygame
import pygame.gfxdraw

from videre.core.constants import TextAlign
from videre.core.pygame_utils import PygameRendered
from videre.core.shaping.layout import (
    FontMetrics,
    ShapedRenderedText,
    _LineItem,
    _LineLayout,
)
from videre.core.shaping.pipeline import shape_text
from videre.core.shaping.rasterizer import Glyph, GlyphArea, GlyphRasterizer
from videre.core.shaping.shaped import ShapedLine
from videre.core.shaping.shaper import Shaper
from videre.core.shaping.texts.textutils import get_font_provider
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
_SELECTION_RGBA = (100, 100, 255, 100)


class ShapedTextRendering:
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

    def render_char(self, c: str, color: tuple[int, ...] = (0, 0, 0)) -> pygame.Surface:
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
        if not c:
            return pygame.Surface((0, 0), pygame.SRCALPHA)
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
            return pygame.Surface((0, 0), pygame.SRCALPHA)
        word = lines[0].words[0]
        if not word.runs or not word.runs[0].glyphs:
            return pygame.Surface((0, 0), pygame.SRCALPHA)
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
        return _glyph_to_surface(glyph)

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
        color: tuple[int, ...] = (0, 0, 0),
        *,
        width: int | None = None,
        wrap_words: bool = True,
        align: TextAlign | None = None,
        selection: tuple[int, int] | None = None,
    ) -> tuple[ShapedRenderedText, PygameRendered]:
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
        # (matching `TextSequence` indexing) to pixel rectangles. The
        # whitespace consumed by a line break (the source space that
        # was BETWEEN sub-line N and sub-line N+1) lives in `pos`
        # between the two and is not charged to either sub-line's
        # length — see `ShapedLine.source_length`.
        lines: list[ShapedLine] = []
        is_paragraph_end: list[bool] = []
        line_source_offsets: list[int] = []
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
                line_source_offsets.append(pos)
                lines.append(sl)
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
            empty_surface = pygame.Surface((1, max(total_height, 1)), pygame.SRCALPHA)
            return ShapedRenderedText(
                font_metrics=self.font_metrics, line_layouts=()
            ), PygameRendered(empty_surface)

        # Two-pass rendering for JUSTIFY: a first pass measures each line
        # at its natural inter-word gap so we know the slack, then a
        # second pass re-renders justifiable lines with widened gaps.
        # LEFT/CENTER/RIGHT don't need the second pass — they only shift
        # x-offset at blit time. Compute target_width from the natural
        # measure (so `width=None` still produces a tight surface).
        natural: list[tuple[pygame.Surface, int, int]] = [
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
        rendered: list[tuple[pygame.Surface, int, int]] = []
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
                )
            )

        out = pygame.Surface(
            (max(target_width, 1), max(total_height, 1)), pygame.SRCALPHA
        )

        # Pass 1: paint the selection background (translucent) BEFORE
        # blitting glyphs. The order matters: selection must sit behind
        # the glyphs so it doesn't tint them. We use `gfxdraw.box` for
        # alpha-correct fills (`draw.rect` ignores the alpha channel).
        if selection is not None and selection[0] < selection[1]:
            for layout in line_layouts:
                for rect_x, rect_w in _selection_rects_from_layout(layout, selection):
                    pygame.gfxdraw.box(
                        out,
                        pygame.Rect(
                            rect_x, layout.y_top, rect_w, layout.y_bottom - layout.y_top
                        ),
                        _SELECTION_RGBA,
                    )

        # Pass 2: glyphs (each line surface includes its underline).
        for (surface, intrinsic_baseline, _), baseline, x in zip(
            rendered, baselines, x_offsets
        ):
            out.blit(surface, (x, baseline - intrinsic_baseline))
        return ShapedRenderedText(
            font_metrics=self.font_metrics, line_layouts=tuple(line_layouts)
        ), PygameRendered(out)

    def _render_line(
        self, line: ShapedLine, color: tuple[int, ...], *, extra_word_gap: float = 0.0
    ) -> tuple[pygame.Surface, int, int]:
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
            return pygame.Surface((0, 0), pygame.SRCALPHA), self._ascender, 0

        # Per-run tuples: (surface, baseline, gap_before). `gap_before`
        # is True only on the *first* run of a word that the source put
        # behind a whitespace separator (`ShapedWord.space_before`), and
        # is forced False on the very first run of the line so we never
        # leave a leading indent. Two consecutive words with no source
        # whitespace between them (e.g. `Hello` and `世界` in
        # `"Hello世界"` after UAX#29 segmentation) carry `space_before=
        # False` and are blitted flush.
        rendered: list[tuple[pygame.Surface, int, bool]] = []
        for w_idx, word in enumerate(line.words):
            gap_before_word = w_idx > 0 and word.space_before
            for r_idx, run in enumerate(word.runs):
                area = self._rasterizer.render_run(
                    run, self._size, color, subpixel=self._subpixel
                )
                surf = _glyph_area_to_surface(area)
                baseline = area.baseline_y
                rendered.append((surf, baseline, r_idx == 0 and gap_before_word))
        if not rendered:
            return pygame.Surface((0, 0), pygame.SRCALPHA), self._ascender, 0
        max_baseline = max(b for _, b, _ in rendered)
        max_below = max(s.get_height() - b for s, b, _ in rendered)
        line_height = max_baseline + max_below
        gap = int(round(self._space_advance + extra_word_gap))
        runs_width = sum(s.get_width() for s, _, _ in rendered)
        n_gaps = sum(1 for _, _, has_gap in rendered if has_gap)
        line_width = runs_width + gap * n_gaps
        out = pygame.Surface((max(line_width, 1), line_height), pygame.SRCALPHA)
        x = 0
        for s, b, has_gap in rendered:
            if has_gap:
                x += gap
            out.blit(s, (x, max_baseline - b))
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
            ul_color = color if len(color) == 4 else (color[0], color[1], color[2], 255)
            pygame.draw.rect(
                out, ul_color, (0, max_baseline + ul_offset, line_width, ul_thickness)
            )

        return out, max_baseline, line_width


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
) -> _LineLayout:
    """Build a `_LineLayout` for the rendered line.

    Walks word/run/cluster in source order, emitting one `_LineItem`
    per HarfBuzz cluster (a group of glyphs sharing one source-index)
    and one per inter-word gap. The pixel positions inside the line
    use the same gap arithmetic as `_render_line` (and the same
    JUSTIFY-driven `extra_word_gap`), so caret / selection helpers
    stay aligned with what was actually painted.

    LTR-correct. Pure-RTL lines have their clusters laid out in
    visual order by HarfBuzz, with cluster ids decreasing — the
    items still get contiguous pixel ranges, but their source
    positions go right-to-left. Mixed bidi within a single line is
    not handled by this layout pass.
    """
    items: list[_LineItem] = []
    pos = line_source_offset
    pixel_x = 0.0
    gap_px = space_advance + extra_word_gap
    for w_idx, word in enumerate(line.words):
        if w_idx > 0 and word.space_before:
            items.append(
                _LineItem(
                    source_start=pos,
                    source_end=pos + 1,
                    x_start=int(round(pixel_x)),
                    x_end=int(round(pixel_x + gap_px)),
                )
            )
            pos += 1
            pixel_x += gap_px
        for run in word.runs:
            run_source_len = len(run.source_text)
            n = len(run.glyphs)
            i = 0
            while i < n:
                cluster_id = run.glyphs[i].cluster
                j = i + 1
                while j < n and run.glyphs[j].cluster == cluster_id:
                    j += 1
                cluster_source_start = pos + cluster_id
                if j < n:
                    cluster_source_end = pos + run.glyphs[j].cluster
                else:
                    cluster_source_end = pos + run_source_len
                if cluster_source_end < cluster_source_start:
                    cluster_source_start, cluster_source_end = (
                        cluster_source_end,
                        cluster_source_start,
                    )
                cluster_pixel_width = sum(g.x_advance for g in run.glyphs[i:j])
                items.append(
                    _LineItem(
                        source_start=cluster_source_start,
                        source_end=cluster_source_end,
                        x_start=int(round(pixel_x)),
                        x_end=int(round(pixel_x + cluster_pixel_width)),
                    )
                )
                pixel_x += cluster_pixel_width
                i = j
            pos += run_source_len
    return _LineLayout(
        y_top=y_top,
        y_bottom=y_bottom,
        x_offset=x_offset,
        source_offset=line_source_offset,
        source_length=line.source_length(),
        items=tuple(items),
    )


def _selection_rects_from_layout(
    layout: _LineLayout, selection: tuple[int, int]
) -> list[tuple[int, int]]:
    """Pixel ``(x, width)`` tuples (absolute in the surface) for the
    items of `layout` that intersect ``selection`` half-open range.

    Each item in the layout already carries its absolute source range
    and its line-relative pixel range; we just shift x by the line's
    `x_offset` and intersect against the selection.
    """
    sel_start, sel_end = selection
    rects: list[tuple[int, int]] = []
    for item in layout.items:
        if item.source_start < sel_end and item.source_end > sel_start:
            rects.append(
                (layout.x_offset + item.x_start, max(item.x_end - item.x_start, 1))
            )
    return rects


def _glyph_to_surface(glyph: Glyph) -> pygame.Surface:
    if glyph.image is None:
        return pygame.Surface((0, 0), pygame.SRCALPHA)
    return pygame.image.frombuffer(
        glyph.image.tobytes(), (glyph.width, glyph.height), "RGBA"
    )


def _glyph_area_to_surface(area: GlyphArea) -> pygame.Surface:
    surface = pygame.Surface((area.width, area.height), pygame.SRCALPHA)
    for sprite, blit_x, blit_y in area.glyphs:
        if sprite.empty():
            continue
        surface.blit(_glyph_to_surface(sprite), (blit_x, area.baseline_y + blit_y))
    return surface
