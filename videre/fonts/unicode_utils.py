import sys
from typing import Sequence
from unicodedata import category, unidata_version

import unicodedataplus  # ty: ignore
from fontTools.unicodedata import script as get_script

Cc = "Cc"  # control characters
Co = "Co"  # private use
Cs = "Cs"  # surrogates
Cn = "Cn"  # non-character or reserved
UNPRINTABLE = (Cc, Co, Cs, Cn)

# UAX#9 explicit bidi formatters: invisible directional marks that
# affect bidi resolution but have no visual representation. Treated as
# non-printable so they are stripped from text before shaping / bidi
# resolution. ZWNJ (U+200C) and ZWJ (U+200D) are NOT listed here even
# though they are also stripped by UAX#9's X9 rule: they affect cursive
# shaping in Arabic / Indic scripts, so consumers may legitimately want
# to keep them in source text and route them to the shaper.
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


class Unicode:
    VERSION = unidata_version

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
        return category(c) not in UNPRINTABLE and c not in _BIDI_FORMATTERS

    @classmethod
    def block(cls, c: str) -> str:
        return unicodedataplus.block(c)

    @classmethod
    def blocks(cls) -> dict[str, Sequence[str]]:
        blocks = {}
        for c in cls.characters():
            blocks.setdefault(cls.block(c), []).append(c)
        return blocks


_COMMON_SCRIPT = "Zyyy"
_INHERITED_SCRIPT = "Zinh"


def _get_characters_for_script(*scripts: str) -> frozenset[str]:
    return frozenset(c for c in Unicode.characters() if get_script(c) in scripts)


NEUTRAL_CHARACTERS: frozenset[str] = _get_characters_for_script(
    _COMMON_SCRIPT, _INHERITED_SCRIPT
)
