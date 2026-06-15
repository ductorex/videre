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
- **Abstractions in `videre/core/rendering_result.py`**: `Rendering` (a surface — `get_width`/`get_height`/`get_at`), `AbstractTextRendering`, `TextRenderingResult`, `CursorState`, `AbstractTextDocument` (a cacheable text-only shape whose `render(width, …)` replays only the width-dependent half). These are the pygame-free types that flow through widget code and the two text renderers.

**In-progress (do not assume wired):**

- `videre/core/drawer.py` — `Drawer` is a per-widget **command IR**: instead of building a surface eagerly, a widget records draw commands (`FillArgs`, `BlitArgs`, `TextArgs`, …) and an external visitor replays them, ideally without allocating intermediate surfaces. Intended to replace direct `window.backend.*` surface building in `draw()`. Widgets still return `Rendering` today.
- `videre/core/text_sizing.py` — backend-independent text measurement (`get_char_sizing`, `get_text_sizing`) that `Drawer.character`/`Drawer.text` depend on. Currently `NotImplementedError` stubs.

### Text rendering (`videre/core/shaping/`, two implementations)

Widgets call `Window.text_rendering(size, strong, italic, height_delta)` → `backend.text_rendering(...)` → an `AbstractTextRendering`. It both renders eagerly (`render_text(text, width, …, underline, selection)` → `(TextRenderingResult, Rendering)`; `render_char(…)` → `Rendering`) AND builds a cacheable **document** (`document(text)` → `AbstractTextDocument`). The document holds the text-only *shape* and its `render(width, …)` replays only the width-dependent *layout + paint*, so a resize never re-shapes — the `Text` widget caches it (`_document`, invalidated on `{text,size,strong,italic,height_delta}`, not on width/wrap/align/underline), giving ~5× faster resizes (`tools/bench_resize.py`). `TextRenderingResult` (`core/rendering_result.py`) is the cursor/hit-test contract `widgets/textinput` relies on — bidi-aware visual navigation through an opaque `CursorState`, **every position on an edit-unit boundary**, plus surface-less sizing (`get_width/height`) for the `Drawer`/`text_sizing` path.

Two implementations both satisfy `AbstractTextRendering`:

1. **Legacy pygame — currently LIVE.** `pygame_backend/text_rendering.py::PygameTextRendering`, on `pygame.freetype` + `PygameFontFactory`. No bidi (visual order = source order); its `PygameTextDocument` is a transparent wrapper (re-renders per `render`, no cached shape) whose `edit_units` are one-per-codepoint (`segment_codepoints`) — the legacy composes nothing, so codepoint *is* its edit unit. `PygameBackend.text_rendering()` always returns this today.

2. **Shaping pipeline (`videre/core/shaping/`) — tested, NOT live.** A from-scratch flat Unicode stack on `AbstractBackend` primitives only. Flow: `partition_text → shape_line → wrap → reorder → render`, exposed by `text_rendering.py::ShapedTextRendering`. Package layout mirrors the data flow: `text_partition/` = logical segmentation; root = shaped/visual model + shaping + rasterization + painting; `rendering/` = line assembly (wrap, space policy, reorder, caret). **Each module has a dense docstring — read it for the detail.** The non-obvious cross-cutting facts:
   - **`core/text_editing.py`** — the `EditUnit` model (immutable UAX#29 grapheme ranges, classified, never filtered) is the editing granularity shared by the pipeline, the document (`AbstractTextDocument.edit_units`), *and* `TextInput`. The renderer aligns every caret position onto an edit-unit boundary (shaped: graphemes, via `render.py::_line_items` grouping clusters per edit unit; legacy: codepoints), so `TextInput` neither snaps nor re-segments — it reads `document.edit_units` and lets the contract align (`_ensure_state` re-syncs the raw cursor to the aligned `pos`). Backspace/delete/selection/insertion all work at edit-unit granularity. Grapheme-vs-codepoint editing is therefore backend-specific (shaped vs legacy); the `widget_tests` grapheme tests are skipped off the shaped backend.
   - **Bidi `core/vibidi/`** — home-grown UAX#9 (P→X1–X10→W→N0→N→I + L2), pure-Python, replaces `python-bidi` (which lacked N0 → the RTL-bracket bug). Public surface: `is_rtl` (segmentation) + `reorder{,_retaining_controls}` (per display line); levels stay internal. Validated against the whole `BidiCharacterTest.txt`.
   - **Ink bounds** — `glyph_partition.measure_glyphs → GlyphMeasure(advance, left, right)` is the one measurement shared by wrap and paint; the wrap fits on ink width (`real_left`/`real_right`), not advance, so overhang (italic `f`, `J`) is never clipped.
   - **Wiring** — no env flags. `underline` is a per-render arg (`render_text` / `document.render`), not renderer config, so the document cache survives an underline toggle. `ShapedTextRendering(subpixel=…)` threads sub-pixel positioning; `Window.__init__(handle_text_sub_pixels)` stores `Window._subpixel` but **nothing reads it yet** — it is the intended hook to make the shaped renderer live. Benches: `tools/bench_text_rendering.py` (one-shot render), `tools/bench_resize.py` (the document cache).
   - **Known gap** — conditional hyphenation: a soft hyphen (U+00AD) is classified `EditUnitKind.SOFT_HYPHEN` but not wired into the wrap (see `word_splitter.py` docstring + the xfail in `test_word_splitter.py`).

   Removed (don't look for them — see git): `python-bidi`, the old renderable model, the per-run shaping pipeline, `ShapedUnit` (the model is now fully flat — one `ShapedCluster` carried end-to-end; see `docs/shaping-cluster-model.md`), and the transitional `new_text_partition/` package (the 2026-06 reorg split it into `text_partition/` + `rendering/` + root modules; `env.py` is gone).

**Font discovery** (`videre/fonts/`): `provider.py::FontProvider` does per-character lookup + cluster-aware fallback over the bundled fonts. Generated artifacts: `font-capabilities.json` (standalone codepoints, cmap-14 variation sequences, GSUB/GPOS scripts), `sequence-to-font.json` (variation/emoji-sequence routing), `coverage-report.json` (audit). PUA + default-ignorable codepoints are excluded as standalone requirements but kept inside shaping clusters. Regenerate via `python -m videre.fonts._gen_char_cov`; refresh the Unicode/IVD registry via `tools/update_unicode_font_data.py`.

### Testing (`videre/testing/`, `tests/`)

- **`StepWindow`** (`videre/testing/step_window.py`): headless `Window` (`hide=True`) used as a context manager (`with StepWindow() as win`). No event loop — drive it manually with `render()` (one backend step), then `screenshot()`. Also `find(widget_cls, **wprops)` and the `user` property (a `FakeUser`). `run()` is disabled.
- **`FakeUser`** (`videre/testing/fake_user.py`): simulates user interactions (click, keyboard, mouse) by posting real events through the backend. Obtain it via `fake_win.user` (it is **not** a fixture). Prefer `FakeUser` + `fake_win.render()` over mocking for event-related tests.
- **Fixtures** (`tests/conftest.py`): `fake_win` — a `FakeWindow` (LD size by default) whose `.check(basename=None)` renders and compares a snapshot; `snap_win` — a `fake_win` that auto-`check()`s on exit. (There is no `fake_user`/`image_testing` fixture.) Image regression via `pytest-regressions` with `diff_threshold=0`.
- **`tests/common.py`** helpers: `win_parameters` / `win_hd_parameters` / `win_sd_parameters` build `@pytest.mark.win_params(...)`; `TrackerWidget` records received events; `pixels_alpha`/`pixels_red`/`pixels_green`/`pixels_blue(rendering)` are backend-agnostic pixel readers (via `Rendering.get_at`, replacing `pygame.surfarray`).
- **Test layout**: `tests/widget_tests/` (anything that **renders** + snapshots — widgets, layouts, windowing), `tests/videre_tests/` (the **non-rendering** rest — clipboard, colors, fonts, events, utils…), `tests/pygame_tests/` (pygame backend + font factory), `tests/new_text_rendering/` (the shaping pipeline — one unit-test module per stage, plus `test_text_samples` image snapshots; tests import from `tests.common`, reuse the root `fake_win`, and init `pygame.freetype` in a module-scoped fixture).
- **Shaped mirror harness** (`tests/new_text_rendering/on_videre/on_widgets/`): re-runs the whole `widget_tests/` suite against the **shaped** renderer with no duplicated test file. A `pytest_collect_file` hook (triggered by the empty `_mirror.py`) builds one virtual `pytest.Module` per `widget_tests/test_*.py` under `on_widgets/`; the parent `on_videre/conftest.py` monkeypatches `PygameBackend.text_rendering` to a `ShapedTextRendering` (the only switch — no env flag). **Run a single mirrored test with `-k`**, not `::nodeid`: the virtual modules have no on-disk path, so path selection raises "file or directory not found". Companions: `test_snapshots.py` pixel-compares each shaped snapshot vs its `widget_tests` baseline (failure count = divergence count); `make_diffs.py` writes `[baseline | shaped | heatmap]` composites for visual inspection.
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
