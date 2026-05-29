"""Import every ``videre`` submodule to surface import-time errors the static
checks miss.

``ty`` and ``ruff`` never execute imports, so they cannot see failures that
depend on import order — most notably circular imports ("partially initialized
module"). Importing every module forces those to surface. Wired into
``poe check`` via the ``imports`` task.

``examples`` is intentionally excluded: demo modules may open a window on import.
"""

import enum
import importlib
import os
import pkgutil
import sys
import traceback
from typing import TextIO

import videre

failures: list[str] = []


class Ansi(enum.StrEnum):
    """SGR (Select Graphic Rendition) parameters for terminal styling.

    Each member holds the raw numeric parameter; `_style` wraps them in the
    ``ESC[…m`` envelope. Being a ``StrEnum``, members interpolate as their
    value, so several can be combined with ``;`` (e.g. bold + a color).
    """

    RESET = "0"
    BOLD = "1"
    RED = "31"
    GREEN = "32"


def _supports_color(stream: TextIO) -> bool:
    """Whether to emit ANSI styling on ``stream``.

    Honors the conventions `ruff`/`ty` and most CLI tools follow: a non-empty
    ``NO_COLOR`` disables color (https://no-color.org/), a non-empty
    ``FORCE_COLOR`` forces it on even when output is redirected, and otherwise
    color is emitted only on a real TTY. ``NO_COLOR`` wins if both are set.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return stream.isatty()


def _style(text: str, *codes: Ansi, stream: TextIO) -> str:
    """Wrap ``text`` in the given SGR ``codes`` (joined with ``;``) plus a
    reset, but only when ``stream`` supports color."""
    if not codes or not _supports_color(stream):
        return text
    return f"\033[{';'.join(codes)}m{text}\033[{Ansi.RESET}m"


def _on_error(name: str) -> None:
    # `pkgutil.walk_packages` swallows ImportError during discovery unless an
    # onerror callback is given; record it so a cycle in a package `__init__`
    # is not silently skipped.
    failures.append(name)
    traceback.print_exc()


for module in pkgutil.walk_packages(videre.__path__, f"{videre.__name__}.", _on_error):
    try:
        importlib.import_module(module.name)
    except Exception:
        failures.append(module.name)
        traceback.print_exc()

if failures:
    header = f"\n{len(failures)} module(s) failed to import:"
    print(_style(header, Ansi.BOLD, Ansi.RED, stream=sys.stderr), file=sys.stderr)
    for name in failures:
        print(f"  - {name}", file=sys.stderr)
    sys.exit(1)

message = f"OK: all '{videre.__name__}' submodules import cleanly."
print(_style(message, Ansi.BOLD, Ansi.GREEN, stream=sys.stdout))
