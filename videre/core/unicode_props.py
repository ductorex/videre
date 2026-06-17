"""Single source of Unicode 16.0 properties for videre.

Every version-dependent Unicode lookup goes through this module so the whole
codebase agrees on one Unicode version. `unicodedataplus` (Unicode 16.0) is the
authority for character properties; `fontTools.unicodedata` is kept only for two
version-stable services — ISO 15924 nomenclature (`script_code`) and script
horizontal direction. Importing this module asserts the expected Unicode
version, so a dependency bump that changes it fails loudly instead of silently
mixing versions (the very drift this module exists to prevent).
"""

import unicodedataplus as _udp  # ty: ignore
from fontTools import unicodedata as _ft

EXPECTED_UNICODE_VERSION = "16.0.0"
UNICODE_VERSION = _udp.unidata_version

if UNICODE_VERSION != EXPECTED_UNICODE_VERSION:
    raise RuntimeError(
        f"unicodedataplus exposes Unicode {UNICODE_VERSION}, expected "
        f"{EXPECTED_UNICODE_VERSION}. Refresh the bundled Unicode data files "
        "(BidiBrackets.txt, BidiCharacterTest.txt) and bump "
        "EXPECTED_UNICODE_VERSION."
    )

# Character-property authority: unicodedataplus, drop-in for the stdlib
# `unicodedata` API but on Unicode 16.0 data.
category = _udp.category
bidirectional = _udp.bidirectional
decomposition = _udp.decomposition
block = _udp.block


def script(character: str) -> str:
    """ISO 15924 script code (four letters) on Unicode 16.0 data.

    `unicodedataplus.script` returns the long script *name* ("Common"); HarfBuzz
    and the font routing want the ISO *code* ("Zyyy"). `fontTools.script_code`
    is pure ISO nomenclature (independent of the Unicode version), so composing
    the two keeps the script 16.0-accurate while yielding the code shape callers
    expect. Unknown scripts fall back to "Zzzz".
    """
    return _ft.script_code(_udp.script(character), default="Zzzz")


def script_direction(script_code: str) -> str:
    """`"LTR"` or `"RTL"` for an ISO 15924 script code.

    `unicodedataplus` does not expose this; fontTools' table is current for
    Unicode 16.0 scripts (e.g. Garay -> RTL), and direction is a script
    property, not a per-character one, so it is safe to source it here.
    """
    return str(_ft.script_horizontal_direction(script_code, default="LTR"))
