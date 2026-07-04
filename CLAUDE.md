# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Videre is a Python GUI framework built on Pygame. It provides a widget/layout system with dirty rendering, event propagation, and a property tracking mechanism. Python >= 3.13 required. Package managed with `uv` and built with `hatchling`.

The rendering layer is **decoupled from Pygame** behind an abstract backend so an alternative backend (SFML is the candidate) can be swapped in; only `videre/core/pygame_backend/` imports `pygame`. See `docs/rendering-backend-strategy.md` for the rationale.

This file is the map, not the reference: module docstrings carry the detailed design (rationale, edge cases, numeric examples). When a bullet says "see \<module\>", read that docstring.

## Real-world testbed: videroid

Videre is battle-tested by **videroid** — the full UI of the pysaurus video-collection manager, reimplemented on videre: `pysaurus/interface/videroid/` in https://github.com/notoraptor/pysaurus (also checked out locally as a sibling folder, `../pysaurus`, where videre is installed as an *editable* dependency — working-tree changes to videre are live there).

- Run it: `uv run -m pysaurus.interface.videroid.run_with_videroid` (from the pysaurus repo).
- Test it: `.venv/Scripts/python -m pytest -n auto tests/interface/videroid_interface` (from the pysaurus repo; 100% coverage) — a cheap non-regression check after touching videre.
- Framework gaps found there: `pysaurus/interface/videroid/GAPS.md`; UI parity vs the reference interface (`pysaurus/interface/kyuti/`, PySide6): `PARITY.md`.

## Common Commands

```bash
# Run all tests in parallel (pytest-xdist)
uv run pytest -n auto tests

# Run all tests with coverage
uv run pytest -n auto --cov=videre --cov-report=term-missing tests

# Run a single test file / a single test
uv run pytest tests/widget_tests/test_file.py
uv run pytest tests/widget_tests/test_file.py::test_name

# Format / lint
uv run ruff format
uv run ruff check --fix

# Type-check (ty)
uv run poe typecheck

# Import every videre submodule (catches circular imports — ty/ruff never execute imports)
uv run poe imports

# Full pre-commit gate: format + lint --fix + typecheck + imports
uv run poe check
```

The `poe` tasks live in `pyproject.toml`. Interactive demo: `uv run python -m examples.demo`.

## Architecture

### Widget System (`videre/widgets/`)

All UI elements inherit from `Widget` (widget.py):

- **Property tracking (`__wprops__`)**: declared per class; values live in `_new`, previous values in `_old`; access via `_get_wprop()`/`_set_wprop()`; change detection is `_old != _new`.
- **Rendering pipeline**: `render(window, width, height)` calls `draw()` only when dirty (`_surface is None`, render context changed, or `has_changed()`). `draw()` returns a `Drawer` (command IR, cached in `_surface`) and never allocates a surface nor imports pygame.
- **Transient state**: `update()` forces the next render without changing properties.
- All widgets use `__slots__`.
- **Child positioning**: layouts call `_set_child_position(child, x, y)` during `draw()`; widget `x`/`y` query the parent's `PositionMapping`; `global_x`/`global_y` climb the tree.
- **Mouse ownership**: `get_mouse_owner()` checks children before parents, top-most first.

### Layout Hierarchy (`videre/layouts/`)

- `AbstractLayout` (base: `_controls` wprop, recursive `has_changed()`/`flush_changes()`, `__size__` = enforced child count, `__capture_mouse__`) → `AbstractControlsLayout` (public `controls`) → `ControlLayout` (single-child wrapper).
- Concrete: `Column`, `Row`, `Container` (single child + border/padding), `ScrollView`, `Div`, `Form`, `RadioGroup`, `Animator`.
- Weight-based sizing (Column/Row): unweighted children render first, then remaining space is split as `remaining * weight // total_weight`.

### Div/Style System

`Div` = CSS-like styling: `StyleDef` holds `default`/`hover`/`click` `Style`s (missing states auto-filled from `default`); `Style` fields: border, padding, background_color, alignments, width, height, square, color. `Div` tracks `_hover`/`_down` and swaps styles on transitions. `Button` extends `Div` via `AbstractButton` (adds a disabled style).

### Windowing (`videre/windowing/`)

- `Window`: entry point. Takes an `AbstractBackend` (default `PygameBackend()`) and gets a renderer + a windowing from it (`Window.renderer` / `Window.windowing`). `run()` drives the event loop at 60 FPS; `Window._refresh` paints via `renderer.render_drawer(drawer, dst=screen)` and skips the repaint when the screen buffer and the root `Drawer` are both unchanged by identity. Also: `call_later`/`call_async`/`call_now` (callback scheduling), `text_rendering(...)`.
- `WindowLayout`: root layout wrapping user controls.
- `EventPropagator`: `_handle()` for click/focus/keydown (a truthy handler stops propagation, else bubble to parent); `_handle_mouse_event()` for motion (transforms coordinates up the tree, emits `mouse_enter`/`mouse_exit` via `get_lineage()`).

### Rendering backend (`videre/core/abstract_backend.py`, `videre/core/pygame_backend/`)

**Widget/layout/event code must not import `pygame`.**

- **Contract = two ABCs + a factory** (`abstract_backend.py`): `AbstractRenderer` — `render_drawer(drawer, dst)` (paint the root screen) + `materialize(drawer)` (a Drawer → its own surface), both silent on *how* (caching, immediate vs retained); `AbstractWindowing` — event loop, cursor, screenshot, resize, `post_event`, mutable state; `AbstractBackend` — pairs the two (`Window` never mixes providers). The low-level drawing primitives and the surface cache are `PygameRenderer` implementation details, **not** contract — a GPU backend (SFML) can flatten the Drawer tree into draw calls and cache nothing.
- **Pygame backend** (`pygame_backend/backend.py`): `PygameRenderer` (instantiable alone; by-value per-frame double-buffer cache `_cache`/`_prev_cache` over its `_paint` seam — an unchanged sub-tree, i.e. a clean widget handing back the *same* `Drawer`, is reused, not repainted), `PygameWindowing` (display, clock, pygame event loop), `PygameBackend` (the factory). Pygame `Surface`s are wrapped in `PygameRendering`; `_deref()` unwraps at the boundary.
- **Pygame-free types** (`core/rendering_result.py`): `Rendering` (a surface), plus the text contracts `AbstractTextRendering`, `TextRenderingResult`, `CursorState`, `AbstractTextDocument`. Colors are `Color` (`videre/colors.py`), rectangles `Rectangle` (`videre/core/rectangle.py`).

**Drawer command IR** — every `draw()` returns a `Drawer`:

- `videre/core/drawer.py` = the IR itself, policy-free (frozen `*Args` dataclasses + `Drawer`; command coordinates are device pixels; `Position` is defined here, value-equal). `videre/core/drawing.py` = the record-time scaling policy (`Drawing`/`ScaledDrawing` — what `window.drawing` returns). `videre/core/drawer_crop.py` = `crop_drawer` (viewport pruning). **These three docstrings are the reference for the whole drawing model.**
- `Drawer` is hashable (memoized, reset on mutation) and treated as immutable once cached; `Drawer.copy()` shields in-place edits (e.g. `TextInput` paints its caret on a copy).
- `crop_drawer` lets `ScrollView` paint only the visible slice: paint cost ∝ visible children, not total (90-card hover: ~63 → ~17 ms). It virtualizes *rasterization*, not *construction* — the `has_changed` dirty-walk stays the O(n) ceiling for huge lists.

**DPI (opt-in `Window(dpi_aware=True)`)** — the display scale is applied at ONE boundary, record time, by `window.drawing` (the Qt/Flutter model): layout, wprops, events and every `draw()` stay in *logical* pixels; `Drawer` commands are *device* pixels; the renderer replays them 1:1 and is scale-free (a second backend inherits the whole policy). Text scales the font size once at the source and its result types carry both units themselves (`TextDocument`, `RenderedText`). At scale 1.0 everything is the strict identity — snapshots stay pixel-identical. Reference docstrings: `videre/core/dpi.py` (the **naming glossary** — a bare "logical" always means pixels; text order is logical/visual, string indices are `source_*` — and the **rounding vocabulary**: `to_device`/`to_logical` half-up, `_ceil` cover, `_floor` stay-inside, `to_logical_slot` for pointers), `videre/core/drawing.py` (edge scaling, flush anchoring, `screen_surface` — the root drawer is sized on the *real* OS buffer), `Drawer.at_scale` (why the device size is ceil, and the known ≤1-px overlap under a transparent sibling at fractional scales). Non-negotiables:

- **Widget `draw()` code never constructs a bare `Drawer(...)`** — always `window.drawing.new_surface(...)`. A bare drawer is correct at 1.0 and silently wrong on a scaled display (only the device-native text pipeline records raw).
- Never pre-resize a bitmap to its display size — `Picture` always displays through `drawing.smoothscale` (a no-op when sizes match).
- `FakeUser` posts device pixels, like the OS. DPI snapshots cover ×2 **and** ×1.5 (`tests/widget_tests/test_dpi_text.py`) — but on integer sizes neither separates half-up from ceil (fracs 0/.5 round the same way). The scales that do (frac .25: ×1.25, ×1.75, 170/96) are pinned by self-comparing tests, not snapshots: the crop-vs-blit matrix (`test_drawer_crop.py`) and the window-size + round-trip tests (`test_dpi.py`).
- Remaining: per-monitor dynamic scale (the *system* scale is read once; SDL3's `GetWindowDisplayScale` will fix), the OS awareness declaration is per-*process* while the opt-in is per-`Window`, sub-pixel AA (ClearType).

### Text rendering (`videre/core/text_rendering/`)

`Window.text_rendering(size, strong, italic, height_delta, compact)` → a `TextRendering` (the `Shaper` + `GlyphRasterizer` are shared per-`Window`, so their caches serve every widget). It renders eagerly (`render_text` → `(TextRenderingResult, Drawer)`, `render_char` → `Drawer`) and builds a cacheable **document** (`document(text)` → `AbstractTextDocument`): the text-only *shape*, whose `render(width, …)` replays only layout + paint — a resize never re-shapes (~5× faster; the `Text` widget caches its document, invalidated on `{text, size, strong, italic, height_delta}`, not on width/wrap/align/underline). `document.layout(width, …)` returns just the caret/hit-test `TextRenderingResult` from the same single-entry cache, paint-free. `TextRenderingResult` is the cursor/hit-test contract `TextInput` relies on: bidi-aware visual navigation through an opaque `CursorState`, every position on an edit-unit boundary.

Flow: `partition_text → shape_line → wrap → reorder → render`; the package layout mirrors it (`text_partition/` = logical segmentation; root = shaping, rasterization, painting; `rendering/` = line assembly: wrap, space policy, reorder, caret). **Each module has a dense docstring — read it for the detail.** Cross-cutting facts:

- `core/text_editing.py`: the `EditUnit` model (UAX#29 grapheme ranges) is the one editing granularity — pipeline, document (`AbstractTextDocument.edit_units`) and `TextInput` all share it; the renderer aligns every caret on an edit-unit boundary, so `TextInput` never re-segments.
- `core/vibidi/`: home-grown UAX#9, pure Python (replaces `python-bidi`, which lacked rule N0). Public surface: `is_rtl` + `reorder{,_retaining_controls}`; levels stay internal. Validated against the full `BidiCharacterTest.txt`.
- The wrap fits on ink width (`glyph_partition.measure_glyphs` → `GlyphMeasure`), not advance — overhang (italic `f`, `J`) is never clipped.
- `underline` is a per-render arg (not renderer config), so the document cache survives an underline toggle. Sub-pixel positioning: `Window.__init__(handle_text_sub_pixels)`.
- Known gap: soft hyphens (U+00AD) are classified but not wired into the wrap (xfail in `test_word_splitter.py`).
- Removed — see git, don't look for them: the legacy `pygame.freetype` renderer + font factory, the mirror test harness, `python-bidi`, `ShapedUnit` (the model is flat: one `ShapedCluster` end-to-end, see `docs/shaping-cluster-model.md`), `new_text_partition/`.

**Font discovery** (`videre/fonts/`): `provider.py::FontProvider` does per-character lookup + cluster-aware fallback over the bundled fonts, driven by generated artifacts (`font-capabilities.json`, `sequence-to-font.json`, `_coverage-report.json`). Regenerate: `python -m videre.fonts._gen_char_cov`; refresh the Unicode/IVD registry: `python -m videre.fonts._update_unicode_font_data`; audit bundled fonts vs upstream: `python -m videre.fonts._audit_fonts`. PUA + default-ignorable codepoints are excluded as standalone requirements but kept inside shaping clusters.

### Testing (`videre/testing/`, `tests/`)

- **`StepWindow`**: headless `Window` used as a context manager; no event loop — drive with `render()` then `screenshot()`. Also `find(widget_cls, **wprops)` and `user` (a `FakeUser`).
- **`FakeUser`** posts real events through the backend (click, keyboard, mouse). Prefer it over mocking for event tests. It is a property of the window fixture, not a fixture itself.
- **Fixtures** (`tests/conftest.py`): `fake_win` (LD-sized `FakeWindow`; `.check(basename=None)` renders and compares a snapshot), `snap_win` (auto-checks on exit). Image regression via `pytest-regressions`, `diff_threshold=0`.
- **`tests/common.py`**: `win_parameters`/`win_hd_parameters`/`win_sd_parameters` (build `@pytest.mark.win_params(...)` — which passes kwargs to `StepWindow`), `TrackerWidget`, `pixels_alpha`/`pixels_red`/`pixels_green`/`pixels_blue` (backend-agnostic pixel readers).
- **Test layout**: `tests/widget_tests/` = anything that renders + snapshots; `tests/videre_tests/` = the non-rendering rest; `tests/pygame_tests/` = pygame backend; `tests/text_rendering/` = the text pipeline (one module per stage + image snapshots).
- To regenerate snapshots after an intended rendering change: `--regen-all`, then restore the pixel-identical re-encodes so the diff stays scoped to real changes.
- Predefined window sizes (`videre/testing/utils.py`): `LD` (320x240, default), `SD`, `HD`, `FHD`.
- Tests run in parallel (`-n auto`) — avoid global mutable state.
- `Clipboard` backend is injectable via the `Clipboard._copy`/`Clipboard._paste` class attributes — substitute those instead of patching `pyperclip`.

## Ruff / ty Configuration

- `skip-magic-trailing-comma = true` (and isort `split-on-trailing-comma = false`): don't rely on magic trailing commas.
- `line-ending = "cr-lf"`: .py files are CRLF.
- Import sorting enforced (`extend-select = ["I"]`).
- `__init__.py`: `F401` suppressed (public API re-exports).
- ty: `unresolved-import` ignored for `shaper.py` (uharfbuzz has no type stubs).

## Note for agents

`AGENTS.md` is a Codex-facing mirror of this file. When you change architecture docs here, update `AGENTS.md` too so the two stay in sync.
