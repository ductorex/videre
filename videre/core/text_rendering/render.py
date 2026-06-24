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

import bisect
from dataclasses import dataclass

from videre.colors import Color, Colors
from videre.core.abstract_backend import AbstractBackend
from videre.core.constants import TextAlign, TextSpacePolicy
from videre.core.rectangle import Rectangle
from videre.core.rendering_result import Rendering
from videre.core.text_editing import EditUnit, segment_edit_units
from videre.core.text_rendering.glyph_partition import (
    GlyphLine,
    GlyphMeasure,
    PositionedGlyph,
    ShapedTextLine,
    measure_glyphs,
)
from videre.core.text_rendering.rasterizer import Glyph, GlyphRasterizer, subpixel_split
from videre.core.text_rendering.rendering.layout import (
    FontMetrics,
    RawLine,
    RenderedText,
    build_rendered_text,
)
from videre.core.text_rendering.rendering.reorder import reorder_line
from videre.core.text_rendering.rendering.space_policy import (
    collapse_spaces,
    resolve_space_policy,
)
from videre.core.text_rendering.rendering.wrap import wrap_lines
from videre.core.text_rendering.shaper import Shaper, shape_line
from videre.core.text_rendering.text_partition.partitioner import partition_text
from videre.core.text_rendering.utils import (
    SYNTHETIC_BOLD_STRENGTH,
    line_metrics,
    underline_metrics,
)
from videre.fonts.provider import get_font_provider

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
    space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
    bold: bool = False,
    italic: bool = False,
) -> list[tuple[GlyphLine, bool]]:
    """Run the whole pipeline, returning `(glyph_line, is_paragraph_end)` per
    display line in visual order. = shape (text-only) then `layout_glyph_lines`
    (width-dependent)."""
    shaped_lines = [
        shape_line(line, shaper, size, bold=bold, italic=italic)
        for line in partition_text(text).lines
    ]
    return layout_glyph_lines(
        shaped_lines, width=width, wrap_words=wrap_words, space_policy=space_policy
    )


def layout_glyph_lines(
    shaped_lines: list[ShapedTextLine],
    *,
    width: int | None = None,
    wrap_words: bool = False,
    space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
) -> list[tuple[GlyphLine, bool]]:
    """Width-dependent half of the pipeline: collapse + wrap + reorder per
    already-shaped line, returning `(glyph_line, is_paragraph_end)` in visual
    order. The shape (partition + `shape_line`) is done upstream and cached by
    the document; only this part is replayed on resize."""
    policy = resolve_space_policy(space_policy, wrap_words)
    out: list[tuple[GlyphLine, bool]] = []
    for shaped in shaped_lines:
        if policy is TextSpacePolicy.COLLAPSE:
            shaped = collapse_spaces(shaped)
        subs = (
            list(wrap_lines([shaped], width, wrap_words, policy))
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
    space_policy: TextSpacePolicy = TextSpacePolicy.AUTO,
    align: TextAlign | None = None,
    bold: bool = False,
    italic: bool = False,
    underline: bool = False,
    height_delta: int = 2,
    compact: bool = True,
    subpixel: bool = False,
    selection: tuple[int, int] | None = None,
) -> tuple[RenderedText, Rendering]:
    """Paint `text` and return `(caret info, surface)`. = shape + layout + paint;
    the document path splits these (shape once, `paint_glyph_lines` per width)."""
    lines = build_glyph_lines(
        text,
        shaper,
        size,
        width=width,
        wrap_words=wrap_words,
        space_policy=space_policy,
        bold=bold,
        italic=italic,
    )
    return paint_glyph_lines(
        lines,
        backend=backend,
        rasterizer=rasterizer,
        size=size,
        color=color,
        width=width,
        align=align,
        underline=underline,
        bold=bold,
        height_delta=height_delta,
        compact=compact,
        subpixel=subpixel,
        edit_units=segment_edit_units(text),
        selection=selection,
    )


@dataclass(slots=True, frozen=True)
class AssembledText:
    """Geometry result of `assemble_glyph_lines`: the caret / hit-test
    `RenderedText` plus the paint plan (glyphs + placement) and surface size that
    `paint_assembled` needs. Color / underline / selection play no part here, so
    one `AssembledText` is reusable across paints — it is what `document.layout`
    returns and what `document.render` paints from (computed once, shared)."""

    rendered: RenderedText
    paint: list[tuple[list[PositionedGlyph], int, float, int]]
    surface_w: int
    surface_h: int


def assemble_glyph_lines(
    lines: list[tuple[GlyphLine, bool]],
    *,
    size: int,
    width: int | None = None,
    align: TextAlign | None = None,
    height_delta: int = 2,
    compact: bool = True,
    edit_units: tuple[EditUnit, ...] = (),
) -> AssembledText:
    """Geometry half of `paint_glyph_lines`: stack (font line metrics, optional
    `compact` first baseline) + align pre-built visual glyph lines into caret /
    hit-test info plus a paint plan, touching NO surface. Color / underline /
    selection are paint-time only and absent here, so the result is reusable
    across paints — `document.layout` returns its `rendered`, `document.render`
    feeds it to `paint_assembled`."""
    m = font_metrics(size, height_delta)

    # `compact` drops the leading line gap unless the first line is an
    # author-authored blank line (a leading `\n`), matching the legacy / CSS.
    compact_first = compact and (len(lines) <= 1 or bool(lines[0][0].glyphs))
    first_baseline = m.ascender + m.height_delta if compact_first else m.line_spacing
    n = len(lines)
    baselines = [first_baseline + i * m.line_spacing for i in range(n)]
    total_height = baselines[-1] + m.descender

    measures = [measure_glyphs(gl.glyphs) for gl, _ in lines]
    natural_max = max((measure.width for measure in measures), default=0.0)
    target_width = float(width) if width is not None else natural_max
    # Width is the natural content width (0 when nothing is visible): no floor,
    # so empty / glyphless text claims no horizontal space -- like render_char
    # and the legacy renderer. Height keeps a 1px floor so a glyphless line still
    # reserves its one-line slot (a caret needs a line to sit on).
    surface_w = max(int(round(target_width)), 0)
    surface_h = max(total_height, 1)

    # Per line: alignment offset, justify slack, and the cluster geometry the
    # caret needs. `paint` keeps the glyphs + baseline for the paint pass.
    raw_lines: list[RawLine] = []
    paint: list[tuple[list[PositionedGlyph], int, float, int]] = []
    eu_starts = [eu.source_start for eu in edit_units]
    for i, (gl, is_end) in enumerate(lines):
        measure = measures[i]
        extra = _justify_extra(gl, measure, align, width, is_end)
        x_offset = _align_offset(align, measure, target_width)
        raw_lines.append(
            RawLine(
                y_top=baselines[i] - m.ascender,
                y_bottom=baselines[i] + m.descender,
                x_offset=x_offset,
                clusters=_line_items(gl, extra, eu_starts),
                source_start=gl.source_start,
                source_end=(
                    gl.terminator.source_end
                    if gl.terminator is not None
                    else gl.source_end
                ),
                terminator=gl.terminator,
                terminator_at_visual_start=gl.terminator is not None and gl.base_is_rtl,
            )
        )
        paint.append((gl.glyphs, x_offset, extra, baselines[i]))

    rendered = build_rendered_text(raw_lines, m, surface_w, surface_h)
    return AssembledText(rendered, paint, surface_w, surface_h)


def paint_assembled(
    assembled: AssembledText,
    *,
    backend: AbstractBackend,
    rasterizer: GlyphRasterizer,
    size: int,
    color: Color | None = None,
    underline: bool = False,
    bold: bool = False,
    subpixel: bool = False,
    selection: tuple[int, int] | None = None,
) -> Rendering:
    """Paint half of `paint_glyph_lines`: blit an `AssembledText`'s paint plan
    onto a fresh surface (selection ribbon first, so glyphs sit over it). Pure
    rasterization, no geometry — the only part `document.render` runs that
    `document.layout` skips."""
    color = color or Colors.black
    out = backend.new_surface(assembled.surface_w, assembled.surface_h)
    # Selection background first, so glyphs sit on top of it.
    if selection is not None and selection[0] < selection[1]:
        for rect in assembled.rendered._selection_rects(*selection):
            backend.box(out, rect, _SELECTION_RGBA)
    for glyphs, x_offset, extra, baseline in assembled.paint:
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
    return out


def paint_glyph_lines(
    lines: list[tuple[GlyphLine, bool]],
    *,
    backend: AbstractBackend,
    rasterizer: GlyphRasterizer,
    size: int,
    color: Color | None = None,
    width: int | None = None,
    align: TextAlign | None = None,
    underline: bool = False,
    bold: bool = False,
    height_delta: int = 2,
    compact: bool = True,
    subpixel: bool = False,
    edit_units: tuple[EditUnit, ...] = (),
    selection: tuple[int, int] | None = None,
) -> tuple[RenderedText, Rendering]:
    """Lay out + paint pre-built visual glyph lines (the output of
    `layout_glyph_lines`) into `(caret info, surface)`. = `assemble_glyph_lines`
    then `paint_assembled`; the document caches the former (paint-free, shared
    with `layout`) and replays only the latter per paint."""
    assembled = assemble_glyph_lines(
        lines,
        size=size,
        width=width,
        align=align,
        height_delta=height_delta,
        compact=compact,
        edit_units=edit_units,
    )
    out = paint_assembled(
        assembled,
        backend=backend,
        rasterizer=rasterizer,
        size=size,
        color=color,
        underline=underline,
        bold=bold,
        subpixel=subpixel,
        selection=selection,
    )
    return assembled.rendered, out


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
        for cluster in sline.clusters:
            if cluster.glyphs:
                g = cluster.glyphs[0]
                if not g.paint:
                    return backend.zero()
                glyph = rasterizer.render_single_glyph(
                    g.font_path, size, g.bold, g.italic, g.glyph_id, color
                )
                if glyph.image is None:
                    return backend.zero()
                return _sprite_surface(backend, glyph)
    return backend.zero()


def _line_items(
    line: GlyphLine, justify_extra: float, edit_unit_starts: list[int]
) -> list[tuple[int, int, int, int, bool]]:
    """Per visual EDIT UNIT, return `(source_start, source_end, x_start, x_end,
    is_rtl)`, x relative to the line's `x_offset`. Consecutive visual clusters in
    the same edit unit are merged into one item, so every caret position lands on
    a grapheme boundary (a ligature spanning several graphemes stays one item —
    the caret skips it whole, as the snapping did before). x-bounds come from the
    shared `_pen_track`. With no `edit_unit_starts`, degrades to one item per
    cluster."""
    track = _pen_track(line.glyphs, justify_extra)
    items: list[tuple[int, int, int, int, bool]] = []
    clusters = line.clusters
    n = len(clusters)
    i = 0
    offset = 0
    while i < n:
        end_offset = offset + len(clusters[i].glyphs)
        j = i + 1
        if edit_unit_starts:
            eu = _edit_unit_index(edit_unit_starts, clusters[i].logical_position)
            while (
                j < n
                and _edit_unit_index(edit_unit_starts, clusters[j].logical_position)
                == eu
            ):
                end_offset += len(clusters[j].glyphs)
                j += 1
        group = clusters[i:j]
        items.append(
            (
                min(c.logical_position for c in group),
                max(c.source_end for c in group),
                int(round(track[offset])),
                int(round(track[end_offset])),
                group[0].is_rtl,
            )
        )
        offset = end_offset
        i = j
    if line.terminator is not None:
        x = (
            items[0][2]
            if line.base_is_rtl and items
            else (items[-1][3] if items else 0)
        )
        term = (
            line.terminator.source_start,
            line.terminator.source_end,
            x,
            x,
            line.base_is_rtl,
        )
        if line.base_is_rtl:
            items.insert(0, term)
        else:
            items.append(term)
    return items


def _edit_unit_index(starts: list[int], pos: int) -> int:
    """Index of the edit unit containing source position `pos` (edit units tile
    the text, sorted by `source_start`)."""
    return bisect.bisect_right(starts, pos) - 1


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
    track = _pen_track(glyphs, justify_extra)
    for i, g in enumerate(glyphs):
        # The phase is part of the bitmap's cache key, so resolve it from the
        # float pen BEFORE rasterizing. In pixel mode `subpixel_split` returns
        # `(round(origin), 0)`, so this stays bit-for-bit the pixel-aligned path.
        int_x, phase = subpixel_split(x_offset + track[i] + g.x_offset, subpixel)
        if g.paint:
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

    if underline:
        line_width = track[-1]
        line_start = float(x_offset)
        ul_offset, ul_thickness = underline_metrics(glyphs[0].font_path, size)
        if bold:
            ul_thickness += int(round(2 * SYNTHETIC_BOLD_STRENGTH * size))
        # `box` (filled), not `rectangle` (1px outline): a thickness >= 3px
        # underline drawn as an outline renders hollow ("rectangle" look).
        backend.box(
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
# Alignment helpers
# ---------------------------------------------------------------------------


def _gap_run_ends(glyphs: list[PositionedGlyph]) -> frozenset[int]:
    """Index of the last glyph of each maximal gap run (= one inter-word gap).
    JUSTIFY adds its extra once per such run."""
    return frozenset(
        i
        for i, g in enumerate(glyphs)
        if g.is_gap and (i + 1 == len(glyphs) or not glyphs[i + 1].is_gap)
    )


def _pen_track(glyphs: list[PositionedGlyph], justify_extra: float) -> list[float]:
    """Pen origin before each glyph, relative to the line's `x_offset`.

    `track[i]` is the origin of glyph `i`; the trailing `track[-1]` is the
    line's total advance width (so `len(track) == len(glyphs) + 1`). JUSTIFY
    slack is added once after the last glyph of each gap run. This is the single
    source of truth for horizontal placement, shared by `_paint_line` (glyph
    blit origin) and `_line_items` (edit-unit x-bounds) so the painted glyphs
    and the caret geometry can never drift apart."""
    gap_ends = _gap_run_ends(glyphs) if justify_extra else frozenset()
    track = [0.0]
    pen = 0.0
    for i, g in enumerate(glyphs):
        pen += g.x_advance
        if i in gap_ends:
            pen += justify_extra
        track.append(pen)
    return track


def _justify_extra(
    gl: GlyphLine,
    measure: GlyphMeasure,
    align: TextAlign | None,
    width: int | None,
    is_paragraph_end: bool,
) -> float:
    if align is not TextAlign.JUSTIFY or width is None or is_paragraph_end:
        return 0.0
    gaps = len(_gap_run_ends(gl.glyphs))
    slack = width - measure.width
    return slack / gaps if gaps > 0 and slack > 0 else 0.0


def _align_offset(
    align: TextAlign | None, measure: GlyphMeasure, target_width: float
) -> int:
    """Pen-origin offset that places the complete ink envelope in the surface."""
    slack = max(0.0, target_width - measure.width)
    if align is None or align is TextAlign.LEFT or align is TextAlign.JUSTIFY:
        envelope_offset = 0.0
    elif align is TextAlign.CENTER:
        envelope_offset = slack // 2
    elif align is TextAlign.RIGHT:
        envelope_offset = slack
    else:
        envelope_offset = 0.0
    # `measure.left` may be negative (e.g. regular J). Shift the pen while
    # leaving every glyph advance and caret interval unchanged.
    return int(round(envelope_offset - measure.left))


def _sprite_surface(backend: AbstractBackend, glyph: Glyph) -> Rendering:
    assert glyph.image is not None
    return backend.image_from_bytes(glyph.image.tobytes(), (glyph.width, glyph.height))
