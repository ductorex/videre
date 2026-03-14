# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Videre is a Python GUI framework built on Pygame. It provides a widget/layout system with dirty rendering, event propagation, and a property tracking mechanism. Python >= 3.13 required.

## Common Commands

```bash
# Run all tests with coverage
uv run pytest --cov=videre --cov-report=term-missing --cov-report=html --cov-report=json videre_tests

# Run a single test file
uv run pytest videre_tests/test_file.py

# Run a single test
uv run pytest videre_tests/test_file.py::test_name

# Format code
uv run ruff format

# Lint
uv run ruff check

# Lint with auto-fix
uv run ruff check --fix
```

## Architecture

### Widget System (`videre/widgets/`)

All UI elements inherit from `Widget` (widget.py). Key mechanisms:

- **Property tracking via `__wprops__`**: Each widget class declares properties in `__wprops__` tuple. Values are stored in `_new` dict, previous values in `_old` dict. Access via `_get_wprop()`/`_set_wprop()`. Change detection compares `_old != _new`.
- **Rendering**: `render()` calls `draw()` only when properties changed or surface is None. Each widget produces a `pygame.Surface`. Parent layouts compose children via `blit()`.
- **`__slots__`**: All widgets use `__slots__` for memory efficiency.
- **Mouse ownership**: Hit-testing propagates through the widget tree via `get_mouse_owner()`. Children are checked before parents, in reverse order (top-most first).

### Layouts (`videre/layouts/`)

Containers that arrange child widgets: `Column` (vertical), `Row` (horizontal), `Container` (single-child with borders/padding), `ScrollView`, `Div` (CSS-like styling with hover/click states via `StyleDef`/`Style`), `Form`, `RadioGroup`, `Animator`.

`Button` extends `Div` (via `AbstractButton`), inheriting the styling state machine.

### Windowing (`videre/windowing/`)

- `Window`: Main entry point. Creates pygame display, runs event loop at 60 FPS (`WINDOW_FPS`).
- `WindowLayout`: Root layout wrapping user controls.
- `EventPropagator`: Routes pygame events (mouse, keyboard) to target widgets.

### Font System (`videre/fonts/`, `videre/core/fontfactory/`)

- `provider.py`: Discovers and provides Noto font files with per-character fallback across Unicode.
- `PygameFontFactory`: Creates and caches fonts by (name, strong, italic). Caches character metrics by (char, size, strong, italic).
- `PygameTextRendering`: Text rendering pipeline using `pygame.freetype`.
- `font_factory_utils.py`: Text layout, wrapping, and measurement.

### Testing (`videre/testing/`, `videre_tests/`)

- `StepWindow`: Headless window using context manager (`with StepWindow() as win`). Supports `render()`, `snapshot()`, `screenshot()` for step-by-step testing without an event loop.
- `FakeUser`: Simulates user interactions (click, keyboard, mouse events).
- Image regression tests via `pytest-regressions`: snapshots compared with `image_regression.check()`.
- Test fixtures: `fake_win` (window with snapshot checking), `snap_win` (auto-checks snapshot on exit), `fake_user`, `image_testing`.
- Marker `@pytest.mark.win_params(dict)` passes kwargs to `StepWindow.__init__`.

## Ruff Configuration

- `skip-magic-trailing-comma = true`: Ruff collapses lines with trailing commas.
- `__init__.py` files: `F401` (unused imports) suppressed — they re-export the public API.
