"""Environment-variable feature flags for the shaped text rendering pipeline.

`Window.text_rendering()` reads these to decide between the legacy
`PygameTextRendering` and the new `ShapedTextRendering` at runtime,
so a single test session can toggle between renderers without touching
the codebase.
"""

import os


def use_shaped_rendering() -> bool:
    """True when `Window.text_rendering()` should swap in the shaped
    pipeline. Driven by the `VIDERE_USE_SHAPED_RENDERING` env var so
    a single test run can toggle between legacy and shaped without
    touching the codebase."""
    return bool(os.environ.get("VIDERE_USE_SHAPED_RENDERING"))


def use_shaped_subpixel() -> bool:
    return bool(os.environ.get("VIDERE_USE_SHAPED_SUBPIXEL"))
