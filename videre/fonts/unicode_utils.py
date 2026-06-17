import functools
import sys
from dataclasses import dataclass

from videre.core import unicode_props
from videre.fonts.coverage import (
    UNICODE_VERSION,
    font_coverage_characters,
    requires_standalone_glyph,
)

Cc = "Cc"  # control characters
Co = "Co"  # private use
Cs = "Cs"  # surrogates
Cn = "Cn"  # non-character or reserved
UNPRINTABLE = (Cc, Co, Cs, Cn)

# UAX#9 explicit bidi formatters have no visual representation. The legacy
# printable predicate rejects them, but the shaping pipeline preserves raw text
# and classifies these characters as editing units before bidi resolution.
# ZWNJ (U+200C) and ZWJ (U+200D) remain printable because they also affect
# cursive shaping in Arabic / Indic scripts.
_BIDI_FORMATTERS: frozenset[str] = frozenset(
    chr(c)
    for c in (
        0x202A,  # LRE - Left-to-Right Embedding
        0x202B,  # RLE - Right-to-Left Embedding
        0x202C,  # PDF - Pop Directional Format
        0x202D,  # LRO - Left-to-Right Override
        0x202E,  # RLO - Right-to-Left Override
        0x2066,  # LRI - Left-to-Right Isolate
        0x2067,  # RLI - Right-to-Left Isolate
        0x2068,  # FSI - First-Strong Isolate
        0x2069,  # PDI - Pop Directional Isolate
    )
)


_COMMON_SCRIPT = "Zyyy"
_INHERITED_SCRIPT = "Zinh"
NEUTRAL_SCRIPTS = (_COMMON_SCRIPT, _INHERITED_SCRIPT)


class Unicode:
    # Kept for the legacy printable predicate. Font coverage has its own
    # explicit Unicode 16 profile below.
    VERSION = unicode_props.UNICODE_VERSION
    FONT_COVERAGE_VERSION = UNICODE_VERSION

    @classmethod
    def characters(cls):
        """
        2024/06/09
        https://stackoverflow.com/a/68992289
        """
        for i in range(sys.maxunicode + 1):
            c = chr(i)
            if cls.printable(c):
                yield c

    @classmethod
    def printable(cls, c: str) -> bool:
        """
        2024/06/09
        https://stackoverflow.com/a/68992289
        """
        return (
            unicode_props.category(c) not in UNPRINTABLE and c not in _BIDI_FORMATTERS
        )

    @classmethod
    def font_coverage_characters(cls):
        yield from font_coverage_characters()

    @classmethod
    def requires_font_glyph(cls, c: str) -> bool:
        return requires_standalone_glyph(c)

    @classmethod
    def block(cls, c: str) -> str:
        return unicode_props.block(c)

    @classmethod
    def blocks(cls) -> dict[str, list[str]]:
        blocks = {}
        for c in cls.characters():
            blocks.setdefault(cls.block(c), []).append(c)
        return blocks


@dataclass(slots=True, frozen=True)
class Character:
    c: str
    # Four-letter script code assigned to the Unicode character
    script: str
    script_is_rtl: bool
    script_is_neutral: bool
    is_european_number: bool
    is_arabic_number: bool


@functools.cache
def get_character(c: str) -> Character:
    if len(c) != 1:
        raise ValueError(f"Character {c!r} is not a single character")

    script = unicode_props.script(c)
    script_is_rtl = unicode_props.script_direction(script) == "RTL"
    # Number: European number (EN), arabic number (AN).
    bidirectional = unicode_props.bidirectional(c)
    is_european_number = bidirectional == "EN"
    is_arabic_number = bidirectional == "AN"
    neutral = script in NEUTRAL_SCRIPTS
    return Character(
        c,
        script=script,
        script_is_rtl=script_is_rtl,
        script_is_neutral=neutral,
        is_european_number=is_european_number,
        is_arabic_number=is_arabic_number,
    )
