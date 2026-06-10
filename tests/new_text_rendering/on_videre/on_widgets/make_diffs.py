"""Generate visual diffs between the shaped-mirror snapshots and their
`widget_tests` baselines, to *inspect* where the shaped renderer diverges.

For each snapshot that differs, writes a side-by-side composite to
`on_widgets/_diffs/<module>/<name>.png`:

    [ baseline | shaped | heatmap ]

The heatmap dims the baseline to grayscale and paints changed pixels: yellow
for small differences (|delta| <= 32, typically antialiasing) and red for large
ones (structural — wrap points, alignment, glyph metrics). The `_diffs/` folder
is git-ignored; it is a debug artifact, regenerated on demand:

    uv run python -m tests.new_text_rendering.on_videre.on_widgets.make_diffs
"""

import importlib
import pathlib
import shutil

import numpy as np
from PIL import Image, ImageDraw

_HERE = pathlib.Path(__file__).parent
_WIDGET_MODULE = importlib.import_module("tests.widget_tests")
assert _WIDGET_MODULE.__file__ is not None
_WIDGET = pathlib.Path(_WIDGET_MODULE.__file__).parent
_OUT = _HERE / "_diffs"

_AA_THRESHOLD = 32  # |delta| at/below this is treated as antialiasing (yellow)
_GAP = 8  # white separator between panels
_BAND = 16  # header strip height for labels


def _snapshots():
    # Only mirror snapshots (legacy baselines under widget_tests). Skips our own
    # `_diffs/` output and on_widgets-only snapshots that have no legacy
    # counterpart to diff against.
    return sorted(p.relative_to(_WIDGET).as_posix() for p in _WIDGET.rglob("*.png"))


def _load(path, shape):
    """Load as RGBA int array, padded with white to `shape` (H, W)."""
    canvas = np.full((*shape, 4), 255, dtype=np.uint8)
    if path.exists():
        img = np.asarray(Image.open(path).convert("RGBA"))
        canvas[: img.shape[0], : img.shape[1]] = img
    return canvas.astype(int)


def _heatmap(a, b):
    gray = (0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]) * 0.3
    out = np.stack([gray, gray, gray, np.full_like(gray, 255)], axis=-1)
    delta = np.abs(a - b).max(axis=-1)
    out[(delta > 0) & (delta <= _AA_THRESHOLD)] = [255, 255, 0, 255]  # yellow
    out[delta > _AA_THRESHOLD] = [255, 0, 0, 255]  # red
    return out.astype(np.uint8)


def _composite(rel):
    a_p, b_p = _WIDGET / rel, _HERE / rel
    a0 = np.asarray(Image.open(a_p).convert("RGBA")) if a_p.exists() else None
    b0 = np.asarray(Image.open(b_p).convert("RGBA")) if b_p.exists() else None
    h = max(x.shape[0] for x in (a0, b0) if x is not None)
    w = max(x.shape[1] for x in (a0, b0) if x is not None)
    a, b = _load(a_p, (h, w)), _load(b_p, (h, w))

    delta = np.abs(a - b).max(axis=-1)
    n_diff = int(np.count_nonzero(delta > 0))
    if n_diff == 0:
        return None, 0.0

    panels = [a.astype(np.uint8), b.astype(np.uint8), _heatmap(a, b)]
    labels = ["baseline", "shaped", "diff"]
    cw = 3 * w + 2 * _GAP
    canvas = Image.new("RGBA", (cw, h + _BAND), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    for i, (panel, label) in enumerate(zip(panels, labels)):
        x = i * (w + _GAP)
        draw.text((x + 2, 3), label, fill=(0, 0, 0, 255))
        canvas.paste(Image.fromarray(panel), (x, _BAND))
    return canvas, 100 * n_diff / delta.size


def main():
    if _OUT.exists():
        shutil.rmtree(_OUT)
    rows = []
    for rel in _snapshots():
        canvas, pct = _composite(rel)
        if canvas is None:
            continue
        dest = _OUT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(dest)
        rows.append((pct, rel))
    rows.sort(reverse=True)
    print(f"{len(rows)} diffs ecrits dans {_OUT}\n")
    for pct, rel in rows:
        print(f"{pct:6.2f}%  {rel}")


if __name__ == "__main__":
    main()
