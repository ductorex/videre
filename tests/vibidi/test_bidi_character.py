"""Conformance test against Unicode's BidiCharacterTest.txt.

The data file (fetched for the same Unicode version as `unicodedataplus`, see
`data/BidiCharacterTest.txt`) is large; if it is absent the test is skipped.

Every conformance case is exercised, including explicit embeddings, overrides,
isolates and X9-removed characters. For each line we check the resolved
paragraph level, per-character embedding levels and L2 visual order.

vibidi deliberately omits L1 (videre resets trailing whitespace itself when it
consumes wrap gaps), but the data's levels and ordering DO include L1. So the
test applies L1 here, at the boundary, before comparing -- the exact division of
labour agreed for the pipeline.
"""

import os

import pytest

from videre.core import unicode_props
from videre.core.vibidi.vibidi import RtlPolicy, _l2_order, vibidi

_DATA = os.path.join(os.path.dirname(__file__), "data", "BidiCharacterTest.txt")
_POLICY = {
    "0": RtlPolicy.LEFT_TO_RIGHT,
    "1": RtlPolicy.RIGHT_TO_LEFT,
    "2": RtlPolicy.INFER,
}
_L1_RESET = {"WS", "FSI", "LRI", "RLI", "PDI"}


def _apply_l1(text: str, levels: list[int | None], base: int) -> list[int | None]:
    """UAX#9 L1 on a single line: S/B, and trailing whitespace, go to `base`.

    Uses the original bidi classes, as L1 mandates. vibidi skips this rule; we
    reproduce it here only to match the conformance data's expected values.
    """
    out = list(levels)
    trailing = True  # at end-of-line a whitespace/isolate run is resettable
    for i in range(len(text) - 1, -1, -1):
        if out[i] is None:
            continue
        cls = unicode_props.bidirectional(text[i])
        if cls in ("S", "B"):
            out[i] = base
            trailing = True
        elif cls in _L1_RESET:
            if trailing:
                out[i] = base
        else:
            trailing = False
    return out


def _load_cases() -> list[tuple[int, str, RtlPolicy, int, list[int | None], list[int]]]:
    if not os.path.exists(_DATA):
        return []
    cases = []
    with open(_DATA, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            cps, direction, plevel, levels_s, order_s = line.split(";")
            text = "".join(chr(int(h, 16)) for h in cps.split())
            level_toks = levels_s.split()
            cases.append(
                (
                    lineno,
                    text,
                    _POLICY[direction],
                    int(plevel),
                    [None if t == "x" else int(t) for t in level_toks],
                    [int(t) for t in order_s.split()] if order_s else [],
                )
            )
    return cases


@pytest.mark.skipif(not os.path.exists(_DATA), reason=f"{_DATA} not present")
def test_bidi_character_conformance() -> None:
    cases = _load_cases()
    assert cases, f"{_DATA} present but parsed to no cases"
    failures = []
    for lineno, text, policy, exp_para, exp_levels, exp_order in cases:
        vt = vibidi(text, policy)
        base = 1 if vt.base_is_rtl else 0
        levels = _apply_l1(
            text,
            [
                None if position._removed else position._level
                for position in vt.logical_positions
            ],
            base,
        )
        active_indices = [
            index for index, level in enumerate(levels) if level is not None
        ]
        active_levels = [level for level in levels if level is not None]
        order = [active_indices[index] for index in _l2_order(active_levels, base)]
        if (base, levels, order) != (exp_para, exp_levels, exp_order):
            cps = " ".join(f"{ord(c):04X}" for c in text)
            failures.append(
                f"line {lineno} [{cps}] pol={policy.value}\n"
                f"   para  exp {exp_para} got {base}\n"
                f"   level exp {exp_levels} got {levels}\n"
                f"   order exp {exp_order} got {order}"
            )
    assert not failures, (
        f"{len(failures)}/{len(cases)} conformance cases failed:\n"
        + "\n".join(failures[:15])
        + (f"\n... and {len(failures) - 15} more" if len(failures) > 15 else "")
    )


@pytest.mark.skipif(not os.path.exists(_DATA), reason=f"{_DATA} not present")
def test_data_file_matches_unicodedata_version() -> None:
    """The conformance data must be the same Unicode version as `unicodedataplus`,
    else we'd be checking vibidi against the wrong expected values."""
    with open(_DATA, encoding="utf-8") as fh:
        header = fh.readline()
    version = header.split("-", 1)[1].rsplit(".txt", 1)[0].strip()
    assert version == unicode_props.UNICODE_VERSION
