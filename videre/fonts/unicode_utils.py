import sys
from typing import Sequence

import unicodedataplus
from unicodedata import category, unidata_version


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
    def _printable(cls, c: str) -> bool:
        """
        2024/06/09
        https://stackoverflow.com/a/68992289
        """
        cat = category(c)
        if cat == "Cc":  # control characters
            return False
        if cat == "Co":  # private use
            return False
        if cat == "Cs":  # surrogates
            return False
        if cat == "Cn":  # non-character or reserved
            return False
        return True

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
    def blocks(cls, wrapper=set) -> dict[str, Sequence[str]]:
        blocks = {}
        for c in cls.characters():
            blocks.setdefault(cls.block(c), []).append(c)
        if wrapper is not None:
            blocks = {block: wrapper(chars) for block, chars in blocks.items()}
        return blocks
