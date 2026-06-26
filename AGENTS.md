# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

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
uv run pytest tests/widget_tests/test_file.py

# Run a single test
uv run pytest tests/widget_tests/test_file.py::test_name

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
- **Rendering pipeline**: `render(window, width, height)` checks three conditions: `_surface is None`, `_old_update != (window, width, height)` (context changed), or `has_changed()` (properties changed). Only when dirty does it call `draw()`, which returns a `Drawer` (a command IR — see "Rendering backend"). After rendering it syncs `_old = _new.copy()` and clears `_transient_state`. Each widget caches its `_surface` (a `Drawer`) for reuse when clean. `draw()` records commands via `Drawing.*` / `Drawer` methods — it never allocates a surface or imports `pygame`; the backend rasterizes the `Drawer` afterwards.
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

- `Window`: Main entry point. Takes an `AbstractBackend` (default `PygameBackend()`) and asks it for a renderer + a windowing — exposed as `Window.renderer` / `Window.windowing` — plus a `TaskManager`. `Window.run()` delegates to `windowing.run()`, which drives the event loop at 60 FPS (`WINDOW_FPS`); `Window._refresh` paints via `renderer.render_drawer(drawer, dst=screen)`. Provides `call_later`/`call_async`/`call_now` for callback scheduling with different timing guarantees, and `text_rendering(...)` (builds a `TextRendering`).
- `WindowLayout`: Root layout wrapping user controls.
- `EventPropagator`: Routes events to target widgets. Two patterns:
  - `_handle()`: For non-mouse events (click, focus, keydown). Calls handler on widget; if truthy, stops; otherwise propagates to parent.
  - `_handle_mouse_event()`: For mouse motion. Transforms coordinates as it propagates up the tree. Uses `get_lineage()` to track ancestor changes and emit `mouse_enter`/`mouse_exit` on intermediate widgets.

### Rendering backend (`videre/core/abstract_backend.py`, `videre/core/pygame_backend/`)

The rendering + windowing seam. **Widget/layout/event code must not import `pygame`** — it goes through the backend.

- **The backend contract is split into two ABCs** (`videre/core/abstract_backend.py`): **`AbstractRenderer`** declares two rendering seams — **`render_drawer(drawer, dst)`** (paint a `Drawer`'s commands onto `dst`, the root screen; returns nothing) and **`materialize(drawer)`** (turn a `Drawer` into its own surface, for nested sub-drawers and one-shot rasterization) — both silent on *how* (caching, immediate vs retained); **`AbstractWindowing`** declares the OS-facing half (the event loop `start`/`stop`/`run`/`step`/`_step`, cursor, `screenshot`, `resize_screen`, `post_event`) plus the mutable backend state. **`AbstractBackend`** is a *factory* pairing the two (`create_renderer()` + `create_windowing(...)`): `Window` asks ONE backend for both halves and never mixes providers, so a same-backend renderer + windowing may share types or an OS context. Surfaces are `Rendering`, colors `Color` (`videre/colors.py`), rectangles `Rectangle` (`videre/core/rectangle.py`) — all pygame-free. The low-level drawing primitives (`new_surface`, `fill`, `blit`, `line`, `rectangle`, `box`, `filled_polygon`, `smoothscale`, `copy`, `image`, `image_from_bytes`) and the by-value surface cache are **not** part of the contract — they are concrete to `PygameRenderer` (see "Drawer command IR" below). A new backend implements an `AbstractRenderer` + an `AbstractWindowing` + an `AbstractBackend` factory — e.g. an immediate-mode GPU backend (SFML) can flatten the Drawer tree into draw calls and cache nothing.
- **The pygame backend** (`pygame_backend/backend.py`) is the only concrete one, in three classes: **`PygameRenderer`** (`AbstractRenderer`) implements `render_drawer` + `materialize` — a by-value per-frame double-buffer cache (`_cache`/`_prev_cache`) over its `_paint` rasterization seam — plus the drawing primitives it uses; it holds no window state and is instantiable on its own. **`PygameWindowing`** (`AbstractWindowing`) owns the display, clock, pygame event loop, and event posting (`post_event`). **`PygameBackend`** (`AbstractBackend`) is the factory pairing them. Text rendering no longer lives on the backend — `Window` builds it (see "Text rendering"). Pygame `Surface`s are wrapped in `PygameRendering` (`pygame_backend/definitions.py`); `_deref()` unwraps them at the boundary.
- **Abstractions in `videre/core/rendering_result.py`**: `Rendering` (a surface — `get_width`/`get_height`/`get_at`), `AbstractTextRendering`, `TextRenderingResult`, `CursorState`, `AbstractTextDocument` (a cacheable text-only shape whose `render(width, …)` replays only the width-dependent half, with `layout(width, …)` returning just the caret/hit-test `TextRenderingResult` paint-free from the same shared per-width cache). These are the pygame-free types that flow through widget code and the shaped text renderer.

**Drawer command IR (live — every `draw()` returns a `Drawer`):**

- **`videre/core/drawer.py`** — instead of building a surface eagerly, each `draw()` records draw commands in local coordinates (`FillArgs`, `BlitArgs`, `LineArgs`, `RectangleArgs`, `BoxArgs`, `FilledPolygonArgs`, `SmoothScaleArgs`, `CopyArgs`, `ImageArgs`, `ImageFromBytesArgs`); sub-drawers nest through `BlitArgs`/`SmoothScaleArgs`/`CopyArgs`. `widget._surface` is a `Drawer`. `Drawing` is a thin helper mirroring the ops as classmethods that take `PositionTuple`s (widgets pass `(x, y)`; it builds the `Position`). `Position` (a frozen, value-equal dataclass) is defined here and is the only one — `position_mapping` re-exports it (the by-value cache needs value equality).
- **Rasterization is deferred to the backend** via two abstract seams: `render_drawer(drawer, dst)` (paint onto the screen) and `materialize(drawer)` (a `Drawer` → its own surface). `PygameRenderer`'s implementation replays a `Drawer`'s commands onto a surface (`_paint`, recursing into sub-drawers through `materialize`) and memoizes materialized surfaces by value in a per-frame double-buffer (`_cache`/`_prev_cache`, private to `PygameRenderer` — not in the abstract contract, so a GPU backend can skip it; rotated on each root paint, bounding memory to two frames without thrashing): an unchanged sub-tree (a clean widget hands back the *same* `Drawer` object) is reused, not repainted; the root screen (painted onto `dst` by `Window._refresh` via `render_drawer`) is never cached. `Window._refresh` skips the repaint when the screen buffer **and** the root `Drawer` are both unchanged by identity (the screen is a persistent software buffer — `flip()` re-presents it as-is). `Drawer` is hashable (memoized hash, reset on mutation) but treated as immutable once cached; `Drawer.copy()` shields in-place edits (`TextInput` paints its caret on a copy, never on the cached text surface). (The earlier `Drawer.character`/`Drawer.text` + `text_sizing.py` measurement design was dropped — the text renderer emits a `Drawer` directly.)
- **`crop_drawer(drawer, rect)`** (`videre/core/drawer.py`) returns a new viewport-sized `Drawer` holding only the commands of `drawer` that intersect `rect` (local coords), translated to the origin. Off-screen commands are dropped; a kept child keeps its **identity** (so it still hits the `materialize` cache); a straddling child *larger than `rect`* is recursively cropped (else it would re-materialize an oversized surface); a generative drawer (image/scale/copy) can't be pruned so it is re-anchored whole at the negative offset (≡ a plain offset blit). `ScrollView.draw` uses it to paint only the visible slice — `materialize` then allocates a viewport surface and composes the few visible children instead of the whole (possibly huge) content. Pixel-identical to the old offset-blit; paint cost ∝ visible children, not total (hover over a 90-card list dropped ~63 → ~17 ms). It virtualizes *rasterization*, not *construction* (the full content `Drawer` is still built — cheap), and works on any content structure (no per-widget assumptions); the remaining O(n) ceiling for huge lists is the `has_changed` dirty-walk, not painting.

### Text rendering (`videre/core/text_rendering/`)

Widgets call `Window.text_rendering(size, strong, italic, height_delta, compact)` → builds a `TextRendering` (threading `Window._subpixel`; `size=None` falls back to `Window._font_size_pts`; the `Shaper` + `GlyphRasterizer` are **shared per-`Window`** — built once in `Window.__init__` and handed to every `TextRendering`, so their per-instance caches (`_fonts`/`_funcs_cache`, `_glyph_cache`) are reused across all `Text` widgets instead of rebuilt per widget per render — the heavy faces/glyph-slots are also module-`lru_cache`d) → an `AbstractTextRendering`. It both renders eagerly (`render_text(text, width, …, underline, selection)` → `(TextRenderingResult, Drawer)`; `render_char(…)` → `Drawer`) AND builds a cacheable **document** (`document(text)` → `AbstractTextDocument`). The document holds the text-only *shape* and its `render(width, …)` replays only the width-dependent *layout + paint*, so a resize never re-shapes — the `Text` widget caches it (`_document`, invalidated on `{text,size,strong,italic,height_delta}`, not on width/wrap/align/underline), giving ~5× faster resizes (`tools/bench_text.py`). `render(width)` splits into `assemble_glyph_lines` (geometry → `AssembledText`, surface-free) + `paint_assembled`, and `document.layout(width, …)` returns just the `TextRenderingResult` from a shared single-entry cache keyed on `(width, wrap_words, space_policy, align)` — navigation/measurement can refresh without a repaint (the go-live fix for the stale-`_rendered` caret #4, not yet wired into `TextInput`). `TextRenderingResult` (`core/rendering_result.py`) is the cursor/hit-test contract `widgets/textinput` relies on — bidi-aware visual navigation through an opaque `CursorState`, **every position on an edit-unit boundary**, plus surface-less sizing (`get_width/height`).

`TextRendering` (`renderer.py`) is the single, **live** renderer — a from-scratch flat Unicode stack that rasterizes glyphs to bitmaps and assembles them into a `Drawer` (`ImageFromBytesArgs` sprites blitted into place), not direct backend surface drawing. The legacy `pygame.freetype` renderer is gone (see "Removed"). Flow: `partition_text → shape_line → wrap → reorder → render`. Package layout mirrors the data flow: `text_partition/` = logical segmentation; root = shaped/visual model + shaping + rasterization + painting; `rendering/` = line assembly (wrap, space policy, reorder, caret). **Each module has a dense docstring — read it for the detail.** The non-obvious cross-cutting facts:
   - **`core/text_editing.py`** — the `EditUnit` model (immutable UAX#29 grapheme ranges, classified, never filtered) is the editing granularity shared by the pipeline, the document (`AbstractTextDocument.edit_units`), *and* `TextInput`. The renderer aligns every caret position onto an edit-unit boundary (graphemes, via `render.py::_line_items` grouping clusters per edit unit), so `TextInput` neither snaps nor re-segments — it reads `document.edit_units` and lets the contract align (`_ensure_state` re-syncs the raw cursor to the aligned `pos`). Backspace/delete/selection/insertion all work at edit-unit (grapheme) granularity.
   - **Bidi `core/vibidi/`** — home-grown UAX#9 (P→X1–X10→W→N0→N→I + L2), pure-Python, replaces `python-bidi` (which lacked N0 → the RTL-bracket bug). Public surface: `is_rtl` (segmentation) + `reorder{,_retaining_controls}` (per display line); levels stay internal. Validated against the whole `BidiCharacterTest.txt`.
   - **Ink bounds** — `glyph_partition.measure_glyphs → GlyphMeasure(advance, left, right)` is the one measurement shared by wrap and paint; the wrap fits on ink width (`real_left`/`real_right`), not advance, so overhang (italic `f`, `J`) is never clipped.
   - **Wiring** — no env flags. `Window.text_rendering()` builds the `TextRendering` directly (the backend no longer exposes `text_rendering`). `underline` is a per-render arg (`render_text` / `document.render`), not renderer config, so the document cache survives an underline toggle. Sub-pixel positioning is wired end-to-end: `Window.__init__(handle_text_sub_pixels)` → `Window._subpixel` → `TextRendering(subpixel=…)`.
   - **Known gap** — conditional hyphenation: a soft hyphen (U+00AD) is classified `EditUnitKind.SOFT_HYPHEN` but not wired into the wrap (see `word_splitter.py` docstring + the xfail in `test_word_splitter.py`).

   Removed (don't look for them — see git): the legacy `PygameTextRendering` + `PygameFontFactory` + `font_factory_utils` (the shaped renderer is now the only one), the shaped **mirror** test harness (`tests/text_rendering/on_videre/`, now redundant — `widget_tests/` runs against the shaped renderer directly), `python-bidi`, the old renderable model, the per-run shaping pipeline, `ShapedUnit` (the model is now fully flat — one `ShapedCluster` carried end-to-end; see `docs/shaping-cluster-model.md`), and the transitional `new_text_partition/` package (the 2026-06 reorg split it into `text_partition/` + `rendering/` + root modules; `env.py` is gone).

**Font discovery** (`videre/fonts/`): `provider.py::FontProvider` does per-character lookup + cluster-aware fallback over the bundled fonts. Generated artifacts: `font-capabilities.json` (standalone codepoints, cmap-14 variation sequences, GSUB/GPOS scripts), `sequence-to-font.json` (variation/emoji-sequence routing), `_coverage-report.json` (audit). PUA + default-ignorable codepoints are excluded as standalone requirements but kept inside shaping clusters. Regenerate via `python -m videre.fonts._gen_char_cov`; refresh the Unicode/IVD registry via `python -m videre.fonts._update_unicode_font_data`; audit bundled fonts vs upstream (and surface new Noto families) via `python -m videre.fonts._audit_fonts`.

### Testing (`videre/testing/`, `tests/`)

- **`StepWindow`** (`videre/testing/step_window.py`): headless `Window` (`hide=True`) used as a context manager (`with StepWindow() as win`). No event loop — drive it manually with `render()` (one backend step), then `screenshot()`. Also `find(widget_cls, **wprops)` and the `user` property (a `FakeUser`). `run()` is disabled.
- **`FakeUser`** (`videre/testing/fake_user.py`): simulates user interactions (click, keyboard, mouse) by posting real events through the backend. Obtain it via `fake_win.user` (it is **not** a fixture). Prefer `FakeUser` + `fake_win.render()` over mocking for event-related tests.
- **Fixtures** (`tests/conftest.py`): `fake_win` — a `FakeWindow` (LD size by default) whose `.check(basename=None)` renders and compares a snapshot; `snap_win` — a `fake_win` that auto-`check()`s on exit. (There is no `fake_user`/`image_testing` fixture.) Image regression via `pytest-regressions` with `diff_threshold=0`.
- **`tests/common.py`** helpers: `win_parameters` / `win_hd_parameters` / `win_sd_parameters` build `@pytest.mark.win_params(...)`; `TrackerWidget` records received events; `pixels_alpha`/`pixels_red`/`pixels_green`/`pixels_blue(rendering)` are backend-agnostic pixel readers (via `Rendering.get_at`, replacing `pygame.surfarray`).
- **Test layout**: `tests/widget_tests/` (anything that **renders** + snapshots — widgets, layouts, windowing), `tests/videre_tests/` (the **non-rendering** rest — clipboard, colors, fonts, events, utils…), `tests/pygame_tests/` (pygame backend + font factory), `tests/text_rendering/` (the text-rendering pipeline — one unit-test module per stage, plus `test_text_samples` image snapshots; tests import from `tests.common`, reuse the root `fake_win`, and init `pygame.freetype` in a module-scoped fixture).
- **Shaped is the default renderer**, so `tests/widget_tests/` exercises it directly — no separate harness. Bidi `TextInput` tests live in `tests/widget_tests/test_textinput_bidi.py`. To regenerate snapshots after an intended rendering change, use `--regen-all` (regenerates everything in one pass, letting tests pass), then restore the pixel-identical re-encodes so the diff stays scoped to real changes.
- `@pytest.mark.win_params(dict)` passes kwargs to `StepWindow.__init__`. Predefined sizes in `videre/testing/utils.py`: `LD` (320x240, default), `SD` (640x480), `HD` (1280x720), `FHD` (1920x1080).
- Tests run in parallel via `pytest-xdist` (`-n auto`). Avoid global mutable state in tests.
- `Clipboard` backend is injectable via `Clipboard._copy`/`Clipboard._paste` class attributes — substitute in tests instead of patching `pyperclip`.

## Ruff / ty Configuration

- `skip-magic-trailing-comma = true`: Ruff collapses lines even when they contain a trailing comma (and isort uses `split-on-trailing-comma = false` to match). Don't rely on magic trailing commas for formatting.
- `line-ending = "cr-lf"`: files are CRLF.
- `extend-select = ["I"]`: import sorting is enforced.
- `__init__.py` files: `F401` (unused imports) suppressed — they re-export the public API.
- ty override: `unresolved-import` is ignored for `videre/core/text_rendering/shaper.py` (uharfbuzz ships no type stubs).

## Note for agents

`CLAUDE.md` is the Claude-facing twin of this file. When you change architecture docs here, update `CLAUDE.md` too so the two stay in sync.
