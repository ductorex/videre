from fontTools.ttLib import TTFont

from videre.fonts.unicode_utils import Unicode


class FontUtils:
    def __init__(self, path: str, font_index=-1, allow_vid=NotImplemented):
        self._path = path
        self._font = TTFont(path, fontNumber=font_index, allowVID=allow_vid)
        # (2024/06/11) https://stackoverflow.com/a/72228817
        self.name: str = self._font["name"].getDebugName(4)
        self._unicode_map: dict = self._font.getBestCmap()
        if self._unicode_map is None:
            raise ValueError(f"Cannot find best unicode table in font: {self.name}")

    def supported(self):
        return [
            (chr(char_int), char_name)
            for char_int, char_name in self._unicode_map.items()
        ]

    def supports(self, character):
        return self._unicode_map.get(ord(character), None)

    def coverage(self) -> dict[str, list[str]]:
        blocks = {}
        for char_int in self._unicode_map.keys():
            c = chr(char_int)
            if Unicode.printable(c):
                blocks.setdefault(Unicode.block(c), []).append(c)
        return blocks
