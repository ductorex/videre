"""Conformance test against Unicode's BidiCharacterTest.txt.

The data file (fetched for the same Unicode version as `unicodedata`, see
`data/BidiCharacterTest.txt`) is large; if it is absent the test is skipped.

We exercise only the subset vibidi targets: lines with NO explicit formatting
character (embeddings, overrides and isolates). vibidi assumes flat text --
videre strips these upstream -- and isolates in particular are NOT removed by
rule X9, so they aren't flagged 'x' in the data; we filter them by bidi class.
For every remaining line we check the resolved paragraph level, the
per-character embedding levels and the L2 visual order.

vibidi deliberately omits L1 (videre resets trailing whitespace itself when it
consumes wrap gaps), but the data's levels and ordering DO include L1. So the
test applies L1 here, at the boundary, before comparing -- the exact division of
labour agreed for the pipeline.
"""

import os
import unicodedata

import pytest

from videre.core.vibidi.vibidi import RtlPolicy, _l2_order, vibidi

_DATA = os.path.join(os.path.dirname(__file__), "data", "BidiCharacterTest.txt")
_POLICY = {
    "0": RtlPolicy.LEFT_TO_RIGHT,
    "1": RtlPolicy.RIGHT_TO_LEFT,
    "2": RtlPolicy.INFER,
}
_L1_RESET = {"WS", "FSI", "LRI", "RLI", "PDI"}
# Explicit formatting characters (X9-removed embeddings/overrides + the isolates,
# which X9 keeps but vibidi's flat-text core does not model). Lines using any of
# these are filtered out: they are out of scope and stripped by videre upstream.
_OUT_OF_SCOPE = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI", "BN"}


def _apply_l1(text: str, levels: list[int], base: int) -> list[int]:
    """UAX#9 L1 on a single line: S/B, and trailing whitespace, go to `base`.

    Uses the original bidi classes, as L1 mandates. vibidi skips this rule; we
    reproduce it here only to match the conformance data's expected values.
    """
    out = list(levels)
    trailing = True  # at end-of-line a whitespace/isolate run is resettable
    for i in range(len(text) - 1, -1, -1):
        cls = unicodedata.bidirectional(text[i])
        if cls in ("S", "B"):
            out[i] = base
            trailing = True
        elif cls in _L1_RESET:
            if trailing:
                out[i] = base
        else:
            trailing = False
    return out


def _load_cases() -> list[tuple[int, str, RtlPolicy, int, list[int], list[int]]]:
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
            if any(unicodedata.bidirectional(c) in _OUT_OF_SCOPE for c in text):
                continue  # explicit formatters / isolates: out of flat-text scope
            level_toks = levels_s.split()
            cases.append(
                (
                    lineno,
                    text,
                    _POLICY[direction],
                    int(plevel),
                    [int(t) for t in level_toks],
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
        levels = _apply_l1(text, [p._level for p in vt.logical_positions], base)
        order = _l2_order(levels, base)
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
    """The conformance data must be the same Unicode version as `unicodedata`,
    else we'd be checking vibidi against the wrong expected values."""
    with open(_DATA, encoding="utf-8") as fh:
        header = fh.readline()
    version = header.split("-", 1)[1].rsplit(".txt", 1)[0].strip()
    assert version == unicodedata.unidata_version
