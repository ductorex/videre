# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Videre is a Python GUI framework built on Pygame. It provides a widget/layout system with dirty rendering, event propagation, and a property tracking mechanism. Python >= 3.13 required. Package managed with `uv` and built with `hatchling`.

The codebase is mid-refactor: the rendering layer is being **decoupled from Pygame** behind an abstract backend so an alternative backend can be swapped in. Most of `videre/` is now pygame-free and talks to an `AbstractBackend`; only `videre/core/pygame_backend/` imports `pygame`. See "Rendering backend" below and `docs/rendering-backend-strategy.md` for the rationale.

## Common Commands

```bash
# Run all tests in parallel (pytest-xdist)
uv run pytest -n auto tests

# Run all tests with coverage
uv run pytest -n auto --cov=videre --cov-report=term-missing tests

# Run a single test file
uv run pytest tests/videre_tests/test_file.py

# Run a single test
uv run pytest tests/videre_tests/test_file.py::test_name

# Format code
uv run ruff format

# Lint (--fix to auto-fix)
uv run ruff check
uv run ruff check --fix

# Type-check (ty)
uv run poe typecheck

# Import every videre submodule to surface import-time / circular-import errors
uv run poe imports

# Full pre-commit gate: format + lint --fix + typecheck + imports
uv run poe check
```

The `poe` tasks live in `pyproject.toml` under `[tool.poe.tasks]`. `typecheck` runs `ty check` against `videre`, `examples`, and `tests`. `imports` runs `tools/import_all.py`, which imports every `videre` submodule — `ty`/`ruff` never execute imports, so this is what catches circular imports ("partially initialized module") and other import-time failures. `check` chains all four.

To run the interactive demo: `uv run python -m examples.demo`.

## Architecture

### Widget System (`videre/widgets/`)

All UI elements inherit from `Widget` (widget.py). Key mechanisms:

- **Property tracking via `__wprops__`**: Each widget class declares properties in a `__wprops__` tuple (or set). Values are stored in `_new` dict, previous values in `_old` dict. Access via `_get_wprop()`/`_set_wprop()`. `_has_wprop()` walks the MRO to find properties across the inheritance hierarchy. Change detection compares `_old != _new`.
- **Rendering pipeline**: `render(window, width, height)` checks three conditions: `_surface is None`, `_old_update != (window, width, height)` (context changed), or `has_changed()` (properties changed). Only when dirty does it call `draw()`, which returns a `Rendering` (see "Rendering backend"). After rendering it syncs `_old = _new.copy()` and clears `_transient_state`. Each widget caches its `_surface` (a `Rendering`) for reuse when clean. `draw()` builds its surface via `window.backend.*` — never via `pygame` directly.
- **Transient state**: `update()` sets `_transient_state["redraw"] = True` to force the next render without changing actual properties. Transient state is cleared after each render cycle.
- **`__slots__`**: All widgets use `__slots__` for memory efficiency.
- **Child positioning**: Widgets track children via `PositionMapping` (`_children_pos`). Layouts call `_set_child_position(child, x, y)` during `draw()`. Widget `x`/`y` properties query the parent's position mapping. `global_x`/`global_y` recursively climb the tree.
- **Mouse ownership**: Hit-testing propagates through the widget tree via `get_mouse_owner()`. Children are checked before parents, in reverse order (top-most first). Layouts delegate to `get_top_mouse_owner()` which iterates `reversed(controls)`.

### Layout Hierarchy (`videre/layouts/`)

Layouts form a clear inheritance chain:

- **`AbstractLayout`**: Base for all containers. Holds `_controls` wprop. Recursively propagates `has_changed()` and `flush_changes()` to children. Defines `__size__` (enforces exact child count if set) and `__capture_mouse__` (if True, captures mouse even outside children).
- **`AbstractControlsLayout`**: Adds public `controls` property and setter.
- **`ControlLayout`**: Single-child wrapper that delegates `draw()` to its child.
- **Concrete layouts**: `Column` (vertical), `Row` (horizontal), `Container` (single-child with borders/padding), `ScrollView`, `Div`, `Form`, `RadioGroup`, `Animator`.

**Weight-based sizing** (Column/Row): Two-pass algorithm. First renders all unweighted children (`weight=0`). Then distributes remaining space to weighted children proportionally: `available_size = remaining * widget_weight // total_weight`.

### Div/Style System

`Div` provides CSS-like styling with state management:

- **`StyleDef`**: Holds `default`, `hover`, `click` `Style` instances. Missing states are auto-filled from `default`.
- **`Style` fields**: `border`, `padding`, `background_color`, `vertical_alignment`, `horizontal_alignment`, `width`, `height`, `square`, `color`.
- **State machine**: Div tracks `_hover` and `_down` booleans; calls `_set_style()` on state transitions.
- **`Button`** extends `Div` via `AbstractButton`, adding `_disabled_style` toggling.

### Windowing (`videre/windowing/`)

- `Window`: Main entry point. Owns an `AbstractBackend` (a `PygameBackend`, exposed as `Window.backend`) and a `TaskManager`. `Window.run()` delegates to `backend.run()`, which drives the event loop at 60 FPS (`WINDOW_FPS`). Provides `call_later`/`call_async`/`call_now` for callback scheduling with different timing guarantees, and `text_rendering(...)` (delegates to the backend).
- `WindowLayout`: Root layout wrapping user controls.
- `EventPropagator`: Routes events to target widgets. Two patterns:
  - `_handle()`: For non-mouse events (click, focus, keydown). Calls handler on widget; if truthy, stops; otherwise propagates to parent.
  - `_handle_mouse_event()`: For mouse motion. Transforms coordinates as it propagates up the tree. Uses `get_lineage()` to track ancestor changes and emit `mouse_enter`/`mouse_exit` on intermediate widgets.

### Rendering backend (`videre/core/abstract_backend.py`, `videre/core/pygame_backend/`)

The rendering + windowing seam. **Widget/layout/event code must not import `pygame`** — it goes through the backend.

- **`AbstractBackend`** declares the whole surface of contact: drawing primitives (`new_surface`, `fill`, `blit`, `line`, `rectangle`, `box`, `filled_polygon`, `smoothscale`, `copy`, `image`, `image_from_bytes`), the event loop (`start`/`stop`/`run`/`step`/`_step`), cursor, `screenshot`, `resize_screen`, `post_event`, and `text_rendering(...)`. All of these traffic in pygame-free types: surfaces are `Rendering`, colors are `Color` (`videre/colors.py`), rectangles are `Rectangle` (`videre/core/rectangle.py`).
- **`PygameBackend`** (`pygame_backend/backend.py`) is the only concrete backend. The `Pygame` base implements the primitives and event posting; `PygameBackend` adds the display, clock, the pygame event loop, and the font factory. Pygame `Surface`s are wrapped in `PygameRendering` (`pygame_backend/definitions.py`); `_deref()` unwraps them at the boundary.
- **Abstractions in `videre/core/rendering_result.py`**: `Rendering` (a surface — `get_width`/`get_height`/`get_at`), `AbstractTextRendering`, `TextRenderingResult`, `CursorState`. These are the pygame-free types that flow through widget code and the two text renderers.

**In-progress (do not assume wired):**

- `videre/core/drawer.py` — `Drawer` is a per-widget **command IR**: instead of building a surface eagerly, a widget records draw commands (`FillArgs`, `BlitArgs`, `TextArgs`, …) and an external visitor replays them, ideally without allocating intermediate surfaces. Intended to replace direct `window.backend.*` surface building in `draw()`. Widgets still return `Rendering` today.
- `videre/core/text_sizing.py` — backend-independent text measurement (`get_char_sizing`, `get_text_sizing`) that `Drawer.character`/`Drawer.text` depend on. Currently `NotImplementedError` stubs.

### Text rendering (`videre/core/shaping/`, two implementations)

Widgets render text via `Window.text_rendering(size, strong, italic, underline, height_delta)` → `backend.text_rendering(...)`, which returns an `AbstractTextRendering`. `render_text(...)` returns `(TextRenderingResult, Rendering)`; `render_char(...)` returns a `Rendering`. `TextRenderingResult` is the cursor/hit-test surface `widgets/textinput` relies on — bidi-aware visual navigation through an opaque `CursorState`. Its 11 abstractmethods: `visual_state{,_at,_at_pixel}`, `next/prev_visual{,_word}`, `visual_range_to_source_set`, `total_visual_count`, and `get_width/get_height` (the last two for the surface-less sizing path — `Drawer`/`text_sizing` — which has no surface to measure).

Two implementations both satisfy `AbstractTextRendering`:

1. **Legacy pygame, currently live** — `videre/core/pygame_backend/text_rendering.py::PygameTextRendering`, built on `pygame.freetype` + `PygameFontFactory` (`font_factory.py`) + `font_factory_utils.py` (layout, wrapping, measurement, alignment). `PygameBackend.text_rendering()` always returns this today. No bidi awareness (visual order = source order).

2. **Shaping pipeline (`videre/core/shaping/new_text_partition/`), tested but not yet live** — a from-scratch FLAT Unicode stack on `AbstractBackend` primitives only. Flow: `partition_text → shape_line → wrap → reorder → render`, exposed by `text_rendering.py::ShapedTextRendering`.
   - `model.py` — data model. Logical: `TextPartition → Line → TextUnit → LogicalCharacter` (inter-word whitespace is an explicit gap `TextUnit`; each unit cuts on `is_rtl`; `logical_position` indexes the original text). `Line`/`ShapedTextLine` carry a `LineBidi` (the line's `VibidiText` + a filtered-index→original-position map) so the reorder can run real UAX#9 L2; the embedding levels stay internal to vibidi, never exposed on the model (`base_is_rtl` is a convenience property). Intermediate `ShapedUnit`/`ShapedTextLine`. Flat visual `PositionedGlyph`/`GlyphLine` — each glyph self-describes (font/bold/italic/is_rtl/is_gap/logical_position), no per-run grouping.
   - `partitioner.py::partition_text` — segmentation. Per-char bidi direction (`is_rtl`) + `base_is_rtl` come from `videre.core.vibidi`; UAX#29 words (uniseg), UAX#24 script (fontTools) and per-char font routing reuse the helpers in `text_partition/partition_func.py` (`_split_by_word/script/font`, `_shaping_script`, `get_font_provider`).
   - `shaping.py::shape_line` — HarfBuzz per `TextUnit` via `shaper.py::Shaper` (still returns `ShapedGlyph`) → `PositionedGlyph` (`logical_position = unit.characters[cluster].logical_position`).
   - `wrap.py::wrap_lines` — one unified greedy over atoms (clusters) + glues (gaps), with `real_right` ink-overhang accounting. Takes a resolved `space_policy`: COLLAPSE drops gaps at line edges + consumes the break glue (the long-standing behaviour); PRESERVE keeps every gap (no edge strip) — a word-wrap break glue hangs on the head line, a char-wrap gap is atomized per character so it splits across lines.
   - `space_policy.py` — `resolve_space_policy(policy, wrap_words)` maps `AUTO` → COLLAPSE (word wrap) / PRESERVE (char wrap or no wrap); `collapse_spaces(line)` is the COLLAPSE pre-pass (reduce each inner gap to one space, drop the line's leading/trailing gaps), applied in `render.build_glyph_lines` before wrap so it also runs when there is no width. The full start/inside/end gap table per (width × wrap_words × policy) lives in `wrap.py`'s module docstring; `TextSpacePolicy` (`core/constants.py`) carries the CSS mapping.
   - `reorder.py::reorder_line` — flat visual `GlyphLine` via `LineBidi.vibidi_text.reorder(start, end)` (real UAX#9 L2 on the line's true levels): each glyph is ranked by vibidi's visual order for its source position (stable sort keeps HarfBuzz intra-cluster order), so it is correct per-glyph even when a parity-uniform unit mixes levels (e.g. a digit run inside RTL).
   - `render.py::render_text`/`render_char` — paint glyph-by-glyph via `rasterizer.py::GlyphRasterizer.render_single_glyph` (no per-run sub-surfaces); alignment (LEFT/CENTER/RIGHT/JUSTIFY), underline, selection highlight, optional sub-pixel positioning (`subpixel` → `rasterizer.subpixel_split` → per-glyph `phase`); also collects the caret geometry.
   - `layout.py::RenderedText` (implements `TextRenderingResult`) — caret / hit-test, entirely glyph-cursor based (no `pos_to_pixel`/`pixel_to_pos`).
   - `env.py` exposes two flags: `VIDERE_USE_SHAPED_RENDERING` is still **not consulted** by `Window.text_rendering()`, so this renderer is not live yet; `VIDERE_USE_SHAPED_SUBPIXEL` **is** consulted — `ShapedTextRendering(subpixel=None)` defaults to it, then threads `subpixel` through `render_text → _paint_line → render_single_glyph(subpixel, phase)`.
   - **Bidi: `videre/core/vibidi/`** — `vibidi(text) -> VibidiText` resolves the full UAX#9 levels (P → W → N0 → N → I; **N0** paired brackets included) in pure Python on `unicodedata` + a bundled `BidiBrackets.txt`, and `VibidiText.reorder(start, end)` applies L2 to a display line. Replaces `python-bidi` (whose pure-Python path lacked N0 → the RTL bracket bug). Levels stay internal; the public surface is `is_rtl` (used at segmentation, incl. HarfBuzz mirroring) + `reorder` (per display line). Validated in `tests/vibidi` against Unicode's `BidiCharacterTest.txt` (fetched at the `unicodedata` version).

   `text_partition/` now holds only the reusable **non-bidi** segmentation helpers (`partition_func._split_by_word/script/font` + classifiers, `partition_repr.{Word,TextScript,PerFont}`); the old python-bidi path (`_split_by_bidi/level/line`, `_strip_bidi_controls`, `BidiRun`, `TextLine`) and the `python-bidi` dependency were removed once vibidi took over bidi. The old renderable model (`split_text_to_renderable`, `RenderableLine/Text/Piece`) and the old shaping pipeline (`pipeline.py`, `wrap.py`, `layout.py`, the old `text_rendering.py`, `shaped.ShapedWord/ShapedLine`) were removed earlier; `shaped_glyph.py` now keeps only `ShapedGlyph` (produced by `shaper.py::Shaper`, consumed by the flat pipeline). The legacy `ShapedRun` and the rasterizer's per-run path (`render_run`, `GlyphArea`) are gone too — the flat pipeline rasterizes glyph-by-glyph via `render_single_glyph`.

**Font discovery** (`videre/fonts/`): `provider.py::FontProvider` discovers Noto font files and provides per-character fallback across Unicode; `unicode_utils.py` classifies characters. Both renderers route font selection through the provider.

### Testing (`videre/testing/`, `tests/`)

- **`StepWindow`** (`videre/testing/step_window.py`): headless `Window` (`hide=True`) used as a context manager (`with StepWindow() as win`). No event loop — drive it manually with `render()` (one backend step), then `screenshot()`. Also `find(widget_cls, **wprops)` and the `user` property (a `FakeUser`). `run()` is disabled.
- **`FakeUser`** (`videre/testing/fake_user.py`): simulates user interactions (click, keyboard, mouse) by posting real events through the backend. Obtain it via `fake_win.user` (it is **not** a fixture). Prefer `FakeUser` + `fake_win.render()` over mocking for event-related tests.
- **Fixtures** (`tests/conftest.py`): `fake_win` — a `FakeWindow` (LD size by default) whose `.check(basename=None)` renders and compares a snapshot; `snap_win` — a `fake_win` that auto-`check()`s on exit. (There is no `fake_user`/`image_testing` fixture.) Image regression via `pytest-regressions` with `diff_threshold=0`.
- **`tests/common.py`** helpers: `win_parameters` / `win_hd_parameters` / `win_sd_parameters` build `@pytest.mark.win_params(...)`; `TrackerWidget` records received events; `pixels_alpha`/`pixels_red`/`pixels_green`/`pixels_blue(rendering)` are backend-agnostic pixel readers (via `Rendering.get_at`, replacing `pygame.surfarray`).
- **Test layout**: `tests/videre_tests/` (widgets, layouts, windowing, events), `tests/pygame_tests/` (the pygame backend + font factory), `tests/new_text_rendering/` (the shaping pipeline — `test_new_partition`/`test_shape_line`/`test_new_wrap`/`test_new_reorder`/`test_new_render`/`test_new_caret`/`test_new_shaped_rendering` for the flat pipeline; `test_segmentation` for the low-level `_split_by_*` helpers; `test_align`/`test_selection`/`test_rasterizer`/`test_shaped_text_rendering`/`test_textinput_visual`; and `test_text_samples` image-regression snapshots). The `new_text_rendering` tests import from `tests.common`, reuse the root `fake_win` fixture, and init `pygame.freetype` in a module-scoped fixture.
- `@pytest.mark.win_params(dict)` passes kwargs to `StepWindow.__init__`. Predefined sizes in `videre/testing/utils.py`: `LD` (320x240, default), `SD` (640x480), `HD` (1280x720), `FHD` (1920x1080).
- Tests run in parallel via `pytest-xdist` (`-n auto`). Avoid global mutable state in tests.
- `Clipboard` backend is injectable via `Clipboard._copy`/`Clipboard._paste` class attributes — substitute in tests instead of patching `pyperclip`.

## Ruff / ty Configuration

- `skip-magic-trailing-comma = true`: Ruff collapses lines even when they contain a trailing comma (and isort uses `split-on-trailing-comma = false` to match). Don't rely on magic trailing commas for formatting.
- `line-ending = "cr-lf"`: files are CRLF.
- `extend-select = ["I"]`: import sorting is enforced.
- `__init__.py` files: `F401` (unused imports) suppressed — they re-export the public API.
- ty override: `unresolved-import` is ignored for `videre/core/shaping/shaper.py` (uharfbuzz ships no type stubs).

## Note for agents

`AGENTS.md` is a Codex-facing mirror of this file. When you change architecture docs here, update `AGENTS.md` too so the two stay in sync.
