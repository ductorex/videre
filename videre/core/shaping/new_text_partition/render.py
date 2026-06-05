"""Paint a partition to a surface + caret info, on the flat glyph model.

`partition_text -> shape_line -> wrap -> reorder` yields visual-order
`GlyphLine`s; this module stacks them vertically (font line metrics, optional
`compact` first baseline), aligns them horizontally (LEFT / CENTER / RIGHT /
JUSTIFY), paints every glyph straight to the surface via
`GlyphRasterizer.render_single_glyph` (pen accumulates in float, rounds per
glyph), and returns a `RenderedText` (caret / hit-test) alongside the surface.

During painting it also records, per line, the cluster pixel ranges that the
caret needs; the selection highlight is painted from the same `RenderedText`,
so there is a single source of truth for cluster geometry.
"""

from __future__ import annotations

from videre.colors import Color, Colors
from videre.core.abstract_backend import AbstractBackend
from videre.core.constants import TextAlign
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import Rendering
from videre.core.shaping.new_text_partition.layout import (
    FontMetrics,
    RawLine,
    RenderedText,
    build_rendered_text,
)
from videre.core.shaping.new_text_partition.model import GlyphLine, PositionedGlyph
from videre.core.shaping.new_text_partition.partitioner import partition_text
from videre.core.shaping.new_text_partition.reorder import reorder_line
from videre.core.shaping.new_text_partition.shaping import shape_line
from videre.core.shaping.new_text_partition.wrap import wrap_lines
from videre.core.shaping.rasterizer import Glyph, GlyphRasterizer, subpixel_split
from videre.core.shaping.shaper import Shaper
from videre.core.shaping.text_partition.partition_func import get_font_provider
from videre.core.shaping.utils import (
    SYNTHETIC_BOLD_STRENGTH,
    line_metrics,
    underline_metrics,
)

# Translucent blue selection highlight (matches the legacy renderer). The
# alpha is essential: glyphs are blitted OVER it, so an opaque fill would tint
# the text.
_SELECTION_RGBA = Color(100, 100, 255, 100)


def font_metrics(size: int, height_delta: int = 2) -> FontMetrics:
    """Reference-font line metrics (the space glyph's font), like the legacy."""
    _, ref_path = get_font_provider().get_font_info(" ")
    asc, desc, line_h = line_metrics(ref_path, size)
    return FontMetrics(
        ascender=asc,
        descender=desc,
        height_delta=height_delta,
        line_spacing=line_h + height_delta,
    )


def build_glyph_lines(
    text: str,
    shaper: Shaper,
    size: int,
    *,
    width: int | None = None,
    wrap_words: bool = False,
    bold: bool = False,
    italic: bool = False,
) -> list[tuple[GlyphLine, bool]]:
    """Run the whole pipeline, returning `(glyph_line, is_paragraph_end)` per
    display line in visual order."""
    out: list[tuple[GlyphLine, bool]] = []
    for line in partition_text(text).lines:
        shaped = shape_line(line, shaper, size, bold=bold, italic=italic)
        subs = (
            list(wrap_lines([shaped], width, wrap_words))
            if width is not None
            else [shaped]
        )
        for i, sub in enumerate(subs):
            out.append((reorder_line(sub), i == len(subs) - 1))
    return out


def render_text(
    text: str,
    *,
    backend: AbstractBackend,
    rasterizer: GlyphRasterizer,
    shaper: Shaper,
    size: int,
    color: Color | None = None,
    width: int | None = None,
    wrap_words: bool = False,
    align: TextAlign | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    height_delta: int = 2,
    compact: bool = True,
    subpixel: bool = False,
    selection: tuple[int, int] | None = None,
) -> tuple[RenderedText, Rendering]:
    """Paint `text` and return `(caret info, surface)`."""
    color = color or Colors.black
    m = font_metrics(size, height_delta)
    lines = build_glyph_lines(
        text, shaper, size, width=width, wrap_words=wrap_words, bold=bold, italic=italic
    )

    # `compact` drops the leading line gap unless the first line is an
    # author-authored blank line (a leading `\n`), matching the legacy / CSS.
    compact_first = compact and (len(lines) <= 1 or bool(lines[0][0].glyphs))
    first_baseline = m.ascender + m.height_delta if compact_first else m.line_spacing
    n = len(lines)
    baselines = [first_baseline + i * m.line_spacing for i in range(n)]
    total_height = baselines[-1] + m.descender

    measures = [_measure(gl.glyphs) for gl, _ in lines]
    natural_max = max((rr for _, rr in measures), default=0.0)
    target_width = float(width) if width is not None else natural_max
    surface_w = max(int(round(target_width)), 1)
    surface_h = max(total_height, 1)

    # Per line: alignment offset, justify slack, and the cluster geometry the
    # caret needs. `paint` keeps the glyphs + baseline for the second pass.
    raw_lines: list[RawLine] = []
    paint: list[tuple[list[PositionedGlyph], int, float, int]] = []
    for i, (gl, is_end) in enumerate(lines):
        advance, _ = measures[i]
        extra = _justify_extra(gl, advance, align, width, is_end)
        x_offset = _align_offset(align, advance, target_width)
        raw_lines.append(
            RawLine(
                y_top=baselines[i] - m.ascender,
                y_bottom=baselines[i] + m.descender,
                x_offset=x_offset,
                clusters=_line_clusters(gl.glyphs, extra),
            )
        )
        paint.append((gl.glyphs, x_offset, extra, baselines[i]))

    rendered = build_rendered_text(raw_lines, len(text), m, surface_w, surface_h)

    out = backend.new_surface(surface_w, surface_h)
    # Selection background first, so glyphs sit on top of it.
    if selection is not None and selection[0] < selection[1]:
        for rect in rendered._selection_rects(*selection):
            backend.box(out, rect, _SELECTION_RGBA)
    for glyphs, x_offset, extra, baseline in paint:
        _paint_line(
            out,
            glyphs,
            backend,
            rasterizer,
            size,
            color,
            baseline,
            x_offset,
            extra,
            underline,
            bold,
            subpixel,
        )
    return rendered, out


def render_char(
    c: str,
    *,
    backend: AbstractBackend,
    rasterizer: GlyphRasterizer,
    shaper: Shaper,
    size: int,
    color: Color | None = None,
    bold: bool = False,
    italic: bool = False,
) -> Rendering:
    """Rasterize a single character to a tightly-fitted surface — just the
    glyph bitmap, no advance / baseline padding. Empty or unsupported input
    yields a zero-size surface. Underline is intentionally not applied (matches
    the legacy `render_char`). Used by `Character` / `Checkbox` / `Radio`."""
    color = color or Colors.black
    if not c:
        return backend.zero()
    for line in partition_text(c).lines:
        sline = shape_line(line, shaper, size, bold=bold, italic=italic)
        for unit in sline.units:
            if unit.glyphs:
                g = unit.glyphs[0]
                glyph = rasterizer.render_single_glyph(
                    g.font_path, size, g.bold, g.italic, g.glyph_id, color
                )
                if glyph.image is None:
                    return backend.zero()
                return _sprite_surface(backend, glyph)
    return backend.zero()


def _line_clusters(
    glyphs: list[PositionedGlyph], justify_extra: float
) -> list[tuple[int, int, int, bool]]:
    """Group glyphs into clusters (consecutive same `logical_position`) and
    return `(source_start, x_start, x_end, is_rtl)` per cluster, with x relative
    to the line's `x_offset`. Same pen + justify arithmetic as `_paint_line`,
    so caret geometry matches the painted glyphs."""
    if not glyphs:
        return []
    gap_ends = _gap_run_ends(glyphs) if justify_extra else frozenset()
    clusters: list[tuple[int, int, int, bool]] = []
    pen = 0.0
    i = 0
    n = len(glyphs)
    while i < n:
        lp = glyphs[i].logical_position
        rtl = glyphs[i].is_rtl
        x_start = int(round(pen))
        j = i
        while j < n and glyphs[j].logical_position == lp:
            pen += glyphs[j].x_advance
            if j in gap_ends:
                pen += justify_extra
            j += 1
        clusters.append((lp, x_start, int(round(pen)), rtl))
        i = j
    return clusters


def _paint_line(
    out: Rendering,
    glyphs: list[PositionedGlyph],
    backend: AbstractBackend,
    rasterizer: GlyphRasterizer,
    size: int,
    color: Color,
    baseline: int,
    x_offset: int,
    justify_extra: float,
    underline: bool,
    bold: bool,
    subpixel: bool,
) -> None:
    if not glyphs:
        return
    gap_ends = _gap_run_ends(glyphs) if justify_extra else frozenset()
    pen_x = float(x_offset)
    line_start = pen_x
    for i, g in enumerate(glyphs):
        # The phase is part of the bitmap's cache key, so resolve it from the
        # float pen BEFORE rasterizing. In pixel mode `subpixel_split` returns
        # `(round(origin), 0)`, so this stays bit-for-bit the pixel-aligned path.
        int_x, phase = subpixel_split(pen_x + g.x_offset, subpixel)
        sprite = rasterizer.render_single_glyph(
            g.font_path,
            size,
            g.bold,
            g.italic,
            g.glyph_id,
            color,
            subpixel=subpixel,
            phase=phase,
        )
        if not sprite.empty():
            blit_x = int_x + sprite.bitmap_left
            blit_y = baseline + int(round(-g.y_offset)) - sprite.bitmap_top
            backend.blit(out, _sprite_surface(backend, sprite), (blit_x, blit_y))
        pen_x += g.x_advance
        if i in gap_ends:
            pen_x += justify_extra

    if underline:
        line_width = pen_x - line_start
        ul_offset, ul_thickness = underline_metrics(glyphs[0].font_path, size)
        if bold:
            ul_thickness += int(round(2 * SYNTHETIC_BOLD_STRENGTH * size))
        backend.rectangle(
            out,
            Rectangle(
                int(line_start),
                baseline + ul_offset,
                int(round(line_width)),
                ul_thickness,
            ),
            color,
        )


# ---------------------------------------------------------------------------
# Measurement / alignment helpers
# ---------------------------------------------------------------------------


def _measure(glyphs: list[PositionedGlyph]) -> tuple[float, float]:
    """`(advance, real_right)` of a glyph line: cumulative advance and the
    rightmost ink edge, same arithmetic as the wrap engine."""
    pen = 0.0
    real_right = 0.0
    for g in glyphs:
        draw_x = int(round(pen + g.x_offset + g.ink_left))
        real_right = max(real_right, draw_x + (g.ink_right - g.ink_left))
        pen += g.x_advance
    return pen, max(real_right, pen)


def _gap_run_ends(glyphs: list[PositionedGlyph]) -> frozenset[int]:
    """Index of the last glyph of each maximal gap run (= one inter-word gap).
    JUSTIFY adds its extra once per such run."""
    return frozenset(
        i
        for i, g in enumerate(glyphs)
        if g.is_gap and (i + 1 == len(glyphs) or not glyphs[i + 1].is_gap)
    )


def _justify_extra(
    gl: GlyphLine,
    advance: float,
    align: TextAlign | None,
    width: int | None,
    is_paragraph_end: bool,
) -> float:
    if align is not TextAlign.JUSTIFY or width is None or is_paragraph_end:
        return 0.0
    gaps = len(_gap_run_ends(gl.glyphs))
    slack = width - advance
    return slack / gaps if gaps > 0 and slack > 0 else 0.0


def _align_offset(
    align: TextAlign | None, line_width: float, target_width: float
) -> int:
    """X offset of a line within the surface. LEFT / JUSTIFY / None flush left
    (JUSTIFY spreads its slack via gap widening instead); CENTER / RIGHT shift."""
    if align is None or align is TextAlign.LEFT or align is TextAlign.JUSTIFY:
        return 0
    slack = max(0.0, target_width - line_width)
    if align is TextAlign.CENTER:
        return int(slack // 2)
    if align is TextAlign.RIGHT:
        return int(slack)
    return 0


def _sprite_surface(backend: AbstractBackend, glyph: Glyph) -> Rendering:
    assert glyph.image is not None
    return backend.image_from_bytes(glyph.image.tobytes(), (glyph.width, glyph.height))
