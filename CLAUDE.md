# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Videre is a Python GUI framework built on Pygame. It provides a widget/layout system with dirty rendering, event propagation, and a property tracking mechanism. Python >= 3.13 required. Package managed with `uv` and built with `hatchling`.

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

# Lint
uv run ruff check

# Lint with auto-fix
uv run ruff check --fix

# Type-check (ty)
uv run poe typecheck

# Format + lint --fix + typecheck (full pre-commit gate)
uv run poe check
```

The `poe` tasks are defined in `pyproject.toml` under `[tool.poe.tasks]`. `typecheck` runs `ty check` against `videre`, `examples`, and `tests`.

## Architecture

### Widget System (`videre/widgets/`)

All UI elements inherit from `Widget` (widget.py). Key mechanisms:

- **Property tracking via `__wprops__`**: Each widget class declares properties in a `__wprops__` tuple (or set). Values are stored in `_new` dict, previous values in `_old` dict. Access via `_get_wprop()`/`_set_wprop()`. `_has_wprop()` walks the MRO to find properties across the inheritance hierarchy. Change detection compares `_old != _new`.
- **Rendering pipeline**: `render(window, width, height)` checks three conditions: `_surface is None`, `_old_update != (window, width, height)` (context changed), or `has_changed()` (properties changed). Only when dirty does it call `draw()`. After rendering, `flush_changes()` syncs `_old = _new.copy()` and clears `_transient_state`. Each widget caches its `_surface` for reuse when clean.
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

- `Window`: Main entry point. Creates pygame display, runs event loop at 60 FPS (`WINDOW_FPS`). Provides `call_later`/`call_async`/`call_now` for callback scheduling with different timing guarantees.
- `WindowLayout`: Root layout wrapping user controls.
- `EventPropagator`: Routes pygame events to target widgets. Two patterns:
  - `_handle()`: For non-mouse events (click, focus, keydown). Calls handler on widget; if truthy, stops; otherwise propagates to parent.
  - `_handle_mouse_event()`: For mouse motion. Transforms coordinates as it propagates up the tree. Uses `get_lineage()` to track ancestor changes and emit `mouse_enter`/`mouse_exit` on intermediate widgets.

### Font System (`videre/fonts/`, `videre/core/fontfactory/`)

- `provider.py`: Discovers and provides Noto font files with per-character fallback across Unicode.
- `PygameFontFactory`: Creates and caches fonts by (name, strong, italic). Caches character metrics by (char, size, strong, italic).
- `PygameTextRendering`: Text rendering pipeline using `pygame.freetype`.
- `font_factory_utils.py`: Text layout, wrapping, and measurement.

### Testing (`videre/testing/`, `tests/`)

- `StepWindow`: Headless window using context manager (`with StepWindow() as win`). Supports `render()`, `snapshot()`, `screenshot()` for step-by-step testing without an event loop.
- `FakeUser`: Simulates user interactions (click, keyboard, mouse events) by posting real pygame events. Prefer `FakeUser` + `fake_win.render()` over mocking for event-related tests.
- Image regression tests via `pytest-regressions`: snapshots compared with `image_regression.check()`.
- Test fixtures (`conftest.py`): `fake_win` (window with `check()` for snapshot comparison), `snap_win` (auto-checks snapshot on exit), `fake_user`, `image_testing`.
- Marker `@pytest.mark.win_params(dict)` passes kwargs to `StepWindow.__init__`.
- Predefined window sizes in `videre/testing/utils.py`: `LD` (320x240), `SD` (640x480), `HD` (1280x720), `FHD` (1920x1080). Default test window is `LD`.
- Tests run in parallel via `pytest-xdist` (`-n auto`). Avoid global mutable state in tests.
- `Clipboard` backend is injectable via `Clipboard._copy`/`Clipboard._paste` class attributes — substitute in tests instead of patching `pyperclip`.

## Ruff Configuration

- `skip-magic-trailing-comma = true`: Ruff collapses lines with trailing commas.
- `__init__.py` files: `F401` (unused imports) suppressed — they re-export the public API.
