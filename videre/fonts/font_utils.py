from fontTools.ttLib import TTFont
from videre.fonts.unicode_utils import Unicode


class FontUtils:
    __slots__ = ("_path", "_font", "_unicode_map", "_name")

    def __init__(self, path: str, font_index=-1, allow_vid=NotImplemented):
        self._path = path
        self._font = TTFont(path, fontNumber=font_index, allowVID=allow_vid)
        # (2024/06/11) https://stackoverflow.com/a/72228817
        debug_name = self._font["name"].getDebugName(4)
        if debug_name is None:
            raise ValueError(f"Cannot get name for font: {path}")
        unicode_map = self._font.getBestCmap()
        if unicode_map is None:
            raise ValueError(f"Cannot find best unicode table in font: {debug_name}")
        self._unicode_map: dict = unicode_map
        self._name: str = debug_name

    @property
    def name(self) -> str:
        return self._name

    def coverage(self) -> dict[str, list[str]]:
        blocks = {}
        for char_int in self._unicode_map.keys():
            c = chr(char_int)
            if Unicode.printable(c):
                blocks.setdefault(Unicode.block(c), []).append(c)
        return blocks
