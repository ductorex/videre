import sys
from typing import Sequence

import unicodedataplus
from unicodedata import category, unidata_version


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
            cat = category(c)
            if cat == "Cc":  # control characters
                continue
            if cat == "Co":  # private use
                continue
            if cat == "Cs":  # surrogates
                continue
            if cat == "Cn":  # non-character or reserved
                continue
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

    _UNPRINTABLE = {"Cc", "Co", "Cs", "Cn"}

    @classmethod
    def printable(cls, c: str) -> bool:
        # return category(c) not in cls._UNPRINTABLE
        return category(c) not in ("Cc", "Co", "Cs", "Cn")

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
