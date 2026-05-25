"""Import every ``videre`` submodule to surface import-time errors the static
checks miss.

``ty`` and ``ruff`` never execute imports, so they cannot see failures that
depend on import order — most notably circular imports ("partially initialized
module"). Importing every module forces those to surface. Wired into
``poe check`` via the ``imports`` task.

``examples`` is intentionally excluded: demo modules may open a window on import.
"""

import importlib
import pkgutil
import sys
import traceback
from typing import TextIO

import videre

failures: list[str] = []


def _color(text: str, code: str, stream: TextIO) -> str:
    # Emit ANSI color only on a TTY, so redirected/piped output stays plain —
    # same discipline `ruff`/`ty` apply.
    return f"\033[{code}m{text}\033[0m" if stream.isatty() else text


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
    print(_color(header, "1;31", sys.stderr), file=sys.stderr)
    for name in failures:
        print(f"  - {name}", file=sys.stderr)
    sys.exit(1)

message = f"OK: all '{videre.__name__}' submodules import cleanly."
print(_color(message, "1;32", sys.stdout))
