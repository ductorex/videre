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

2. **Shaping pipeline (`videre/core/shaping/`), tested but not yet live** — a from-scratch FLAT Unicode stack on `AbstractBackend` primitives only. Flow: `partition_text → shape_line → wrap → reorder → render`, exposed by `text_rendering.py::ShapedTextRendering`. The package mirrors the data flow: `text_partition/` = logical segmentation; root = the shaped/visual model (`glyph_partition.py`), shaping (`shaper.py`), rasterization (`rasterizer.py`, FreeType), painting (`render.py`), the `AbstractTextRendering` entry (`text_rendering.py`), shared FreeType caches + synthetic bold/slant constants (`utils.py`); `rendering/` = line assembly (wrap, space policy, reorder, caret).
   - `core/text_editing.py` — source-text editing model shared by shaping and `TextInput`: Unicode 16 UAX#29 extended grapheme clusters become immutable `EditUnit(source_start, source_end, kind)` ranges. Structural and invisible content (`CRLF`, tabs, bidi controls, soft hyphen, ZWSP/WJ, hidden controls, invalid surrogates) is classified, never destructively filtered. Backspace/Delete mutate the original string by edit-unit range.
   - `text_partition/model.py` — logical model: `TextPartition → Line → TextUnit → LogicalCharacter` (inter-word whitespace is an explicit gap `TextUnit`; each unit cuts on `is_rtl`; `logical_position` indexes the original text; every character references its `EditUnit`). `TextPartition` stores the full edit-unit tuple; each `Line` stores its exact source range and optional line-terminator unit. `TextUnit` also carries word-wrap metadata (`can_break_before`, `no_break_before`) for opportunities/constraints that cannot be represented by `atomic` alone. `Line` carries a `LineBidi` so the reorder can run real UAX#9 L2; embedding levels stay internal to vibidi (`base_is_rtl` is a convenience property).
   - `glyph_partition.py` — shaped/visual model: intermediate `ShapedUnit`/`ShapedTextLine` (units in logical order, carrying the `LineBidi`); flat visual `PositionedGlyph`/`GlyphLine` — each glyph self-describes (font/bold/italic/is_rtl/is_gap/logical_position), no per-run grouping. Also `measure_glyphs` → `GlyphMeasure(advance, left, right)`, the one measurement shared by the wrap engine and the paint pass.
   - `text_partition/partitioner.py::partition_text` — segmentation. Per-char bidi direction (`is_rtl`) + `base_is_rtl` come from `videre.core.vibidi`; `text_partition/word_splitter.py` implements Unicode 16 UAX#29 word boundaries directly on `unicodedataplus` properties, then applies Videre's UAX#14-based profile to emit source-offset `WordSpan`/`GapSpan` objects (`atomic=False` coalesces CJK/SA shaping runs while preserving cluster-level word-wrap). The profile applies LB9 inheritance for combining marks/variation selectors, keeps CJK punctuation attached at legal line edges, and exposes break-after-hyphen opportunities. UAX#24 script and grapheme-cluster font routing live in `partition_utils.py` (`_split_by_script/font`, `_shaping_script`, `TextScript`/`PerFont`); variation selectors, combining marks and emoji controls stay with the base cluster. Font lookup goes through `fonts/provider.py::get_font_provider`. Conformance is pinned to the official `WordBreakTest-16.0.0.txt`; `tools/bench_word_splitter.py` compares the specialized engine against Uniseg.
   - `shaper.py` — `Shaper` (uharfbuzz wrapper: FreeType-hinted advances injected via custom `FontFuncs`, synthetic bold/slant; returns `ShapedGlyph`) + `shape_line` (HarfBuzz per `TextUnit` → `PositionedGlyph`; `logical_position = unit.characters[cluster].logical_position`).
   - `rendering/wrap.py::wrap_lines` — one unified greedy over atoms (clusters) + glues (gaps), with `real_right` ink-overhang accounting. Atomization combines `atomic`/`is_breakable` with each unit's explicit break metadata, so punctuation constraints and hyphen opportunities survive script/font splitting. Edge trimming is **word-wrap-only**: word wrap drops the break gap (COLLAPSE) or hangs it on the head (PRESERVE); char wrap atomizes gaps per character and keeps them (split across lines, never dropped) regardless of policy, so an edge space (word boundary vs mid-word break) stays visible.
   - `rendering/space_policy.py` — `resolve_space_policy(policy, wrap_words)` maps `AUTO` → COLLAPSE (word wrap) / PRESERVE (char wrap or no wrap); `collapse_spaces(line)` is the COLLAPSE pre-pass (shrink each gap run to one space, **no edge trimming** — that is word-wrap-only, in the wrap), applied in `render.build_glyph_lines` before wrap so it also runs with no width. The full start/inside/end gap table per (width × wrap_words × policy) lives in `rendering/wrap.py`'s module docstring; `TextSpacePolicy` (`core/constants.py`) carries the CSS mapping.
   - `rendering/reorder.py::reorder_line` — flat visual `GlyphLine` via `LineBidi.vibidi_text.reorder(start, end)` (real UAX#9 L2 on the line's true levels): each glyph is ranked by vibidi's visual order for its source position (stable sort keeps HarfBuzz intra-cluster order), so it is correct per-glyph even when a parity-uniform unit mixes levels (e.g. a digit run inside RTL).
   - `render.py::render_text`/`render_char` — paint glyph-by-glyph via `rasterizer.py::GlyphRasterizer.render_single_glyph` (no per-run sub-surfaces); alignment (LEFT/CENTER/RIGHT/JUSTIFY), underline, selection highlight, optional sub-pixel positioning (`subpixel` → `rasterizer.subpixel_split` → per-glyph `phase`); also collects the caret geometry.
   - `rendering/layout.py::RenderedText` (implements `TextRenderingResult`) — caret / hit-test, entirely glyph-cursor based (no `pos_to_pixel`/`pixel_to_pos`).
   - Wiring: there are **no env flags** (the former `env.py` is gone). `subpixel` is a plain `ShapedTextRendering` constructor parameter (default `False`), threaded through `render_text → _paint_line → render_single_glyph(subpixel, phase)`. `Window.__init__(handle_text_sub_pixels: bool | None)` stores it as `Window._subpixel`, **not read by anything yet** — it is the intended hook for wiring the shaped renderer in; `PygameBackend.text_rendering()` still always returns the legacy renderer. `tools/bench_text_rendering.py` benchmarks legacy vs shaped (`uv run python tools/bench_text_rendering.py`).
   - **Bidi: `videre/core/vibidi/`** — `vibidi(text) -> VibidiText` resolves UAX#9 phases P → X1–X10 → W → N0 → N → I (**N0** paired brackets included) in pure Python on `unicodedata` + a bundled `BidiBrackets.txt`, and `VibidiText.reorder(start, end)` applies L2 to a display line. The explicit stack handles embeddings, overrides, isolates, overflow depth and FSI direction; X10 applies W/N/I per isolating run sequence. X9-removed characters remain as invisible source/editing anchors with a neighbouring level so ZWJ/ZWNJ stay in their HarfBuzz run; the standard reorder omits them, while the shaping pipeline uses `reorder_retaining_controls`. Replaces `python-bidi` (whose pure-Python path lacked N0 → the RTL bracket bug). Levels stay internal; the public surface is `is_rtl` (used at segmentation, incl. HarfBuzz mirroring) + reorder methods (per display line). Validated in `tests/vibidi` against every case in Unicode's `BidiCharacterTest.txt`.

   Removed along the way (do not look for them): the `python-bidi` dependency and its path (`_split_by_bidi/level/line`, `BidiRun`, `TextLine`) — vibidi took over; the old renderable model (`split_text_to_renderable`, `RenderableLine/Text/Piece`) and the per-run shaping pipeline (`pipeline.py`, `ShapedWord/ShapedLine`, `ShapedRun`, the rasterizer's `render_run`/`GlyphArea`); the transitional `new_text_partition/` package — the 2026-06 reorg split it into `text_partition/` + `rendering/` + root modules, merged `shaping.py::shape_line` and `shaped_glyph.py::ShapedGlyph` into `shaper.py`, extracted the shaped/visual model from `model.py` into `glyph_partition.py`, and deleted `env.py` (`VIDERE_USE_SHAPED_RENDERING` / `VIDERE_USE_SHAPED_SUBPIXEL` no longer exist).

**Font discovery** (`videre/fonts/`): `provider.py::FontProvider` discovers the bundled fonts and provides both legacy per-character lookup and cluster-aware fallback. The generated `font-capabilities.json` inventories standalone Unicode 16 codepoints, cmap format 14 variation sequences, and GSUB/GPOS scripts; `sequence-to-font.json` routes standardized/ideographic variants and official emoji sequences. `coverage-report.json` records missing codepoints/sequences plus HarfBuzz `.notdef` and multi-glyph checks. The font profile excludes PUA and default-ignorable codepoints as standalone requirements while preserving them inside shaping clusters. `tools/update_unicode_font_data.py` refreshes the pinned Unicode/IVD sequence registry; `python -m videre.fonts._gen_char_cov` regenerates all coverage artifacts.

### Testing (`videre/testing/`, `tests/`)

- **`StepWindow`** (`videre/testing/step_window.py`): headless `Window` (`hide=True`) used as a context manager (`with StepWindow() as win`). No event loop — drive it manually with `render()` (one backend step), then `screenshot()`. Also `find(widget_cls, **wprops)` and the `user` property (a `FakeUser`). `run()` is disabled.
- **`FakeUser`** (`videre/testing/fake_user.py`): simulates user interactions (click, keyboard, mouse) by posting real events through the backend. Obtain it via `fake_win.user` (it is **not** a fixture). Prefer `FakeUser` + `fake_win.render()` over mocking for event-related tests.
- **Fixtures** (`tests/conftest.py`): `fake_win` — a `FakeWindow` (LD size by default) whose `.check(basename=None)` renders and compares a snapshot; `snap_win` — a `fake_win` that auto-`check()`s on exit. (There is no `fake_user`/`image_testing` fixture.) Image regression via `pytest-regressions` with `diff_threshold=0`.
- **`tests/common.py`** helpers: `win_parameters` / `win_hd_parameters` / `win_sd_parameters` build `@pytest.mark.win_params(...)`; `TrackerWidget` records received events; `pixels_alpha`/`pixels_red`/`pixels_green`/`pixels_blue(rendering)` are backend-agnostic pixel readers (via `Rendering.get_at`, replacing `pygame.surfarray`).
- **Test layout**: `tests/widget_tests/` (widgets, layouts, windowing — anything that **renders** and snapshots, e.g. `test_text`/`test_textinput`/`test_button`/`test_column`/`test_window*`), `tests/videre_tests/` (the **non-rendering** rest — `test_clipboard`/`test_colors`/`test_sides`/`test_fonts`/`test_unicode_utils`/`test_utils`/`test_windowutils`/`test_gradient`/`test_dialog`/`test_event_propagator`/`test_keyboard_events`/`test_mouse_events`), `tests/pygame_tests/` (the pygame backend + font factory), `tests/new_text_rendering/` (the shaping pipeline — `test_new_partition`/`test_shape_line`/`test_new_wrap`/`test_new_reorder`/`test_new_render`/`test_new_caret`/`test_new_shaped_rendering` for the flat pipeline; `test_segmentation` for the low-level `_split_by_*` helpers; `test_space_policy` for the gap matrix; `test_align`/`test_selection`/`test_rasterizer`/`test_shaped_text_rendering`/`test_textinput_visual`; and `test_text_samples` image-regression snapshots). The `new_text_rendering` tests import from `tests.common`, reuse the root `fake_win` fixture, and init `pygame.freetype` in a module-scoped fixture.
- **Shaped mirror harness** (`tests/new_text_rendering/on_videre/on_widgets/`): re-runs the whole `tests/widget_tests/` suite against the **shaped** renderer without duplicating any test file. Its `conftest.py` defines a `pytest_collect_file` hook (triggered by the otherwise-empty `_mirror.py`) that builds one virtual `pytest.Module` per `tests/widget_tests/test_*.py`, anchored under `on_widgets/` so its snapshots land in `on_widgets/<module>/`; the parent `on_videre/conftest.py` provides the autouse fixture that monkeypatches `PygameBackend.text_rendering` to return a `ShapedTextRendering`. This is how the not-yet-live shaped renderer is exercised against the real widget suite (the monkeypatch is the only switch — there is no env flag). Only the rendering subset (`widget_tests/`) is mirrored, so process-global tests like the clipboard are excluded by construction. To run a single mirrored test, use `-k` (e.g. `uv run pytest tests/new_text_rendering/on_videre/on_widgets -k "test_button and test_click"`): the virtual module files don't exist on disk, so `::nodeid` path selection raises "file or directory not found" (no conftest hook can intercept it — positional args are validated before any conftest loads). Two companion tools sit alongside the mirror: `test_snapshots.py` pixel-compares each mirrored snapshot against its `widget_tests` baseline (one parametrized case per snapshot via PIL+numpy, passes iff pixel-identical — so the failure count *is* the divergence count), and `make_diffs.py` (standalone: `uv run python -m tests.new_text_rendering.on_videre.on_widgets.make_diffs`) writes `[baseline | shaped | heatmap]` composites to the git-ignored `_diffs/<module>/<name>.png` for visual inspection (heatmap: yellow = small/antialiasing delta, red = structural).
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

`CLAUDE.md` is the Claude-facing twin of this file. When you change architecture docs here, update `CLAUDE.md` too so the two stay in sync.
