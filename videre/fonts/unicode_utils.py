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
            if category(c) not in UNPRINTABLE:
                yield c

    @classmethod
    def printable(cls, c: str) -> bool:
        """
        2024/06/09
        https://stackoverflow.com/a/68992289
        """
        return category(c) not in UNPRINTABLE

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
