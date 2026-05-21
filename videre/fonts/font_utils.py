from fontTools.ttLib import TTFont

from videre.fonts.unicode_utils import Unicode


def _get_sized_height(font: TTFont, pt_size: int, dpi: int = 72) -> int:
    head = font["head"]
    hhea = font["hhea"]

    units_per_em = head.unitsPerEm  # ty: ignore[unresolved-attribute]
    ascent = hhea.ascent
    descent = hhea.descent
    line_gap = hhea.lineGap  # ty: ignore[unresolved-attribute]

    line_height_units = ascent - descent + line_gap

    pixel_size = pt_size * dpi / 72.0

    height_px = line_height_units * pixel_size / units_per_em

    return round(height_px)


class FontUtils:
    __slots__ = ("_path", "_unicode_map", "_name", "_sized_height")

    def __init__(self, path: str, size_points: int | None = None, *, font_index=-1):
        with TTFont(path, fontNumber=font_index) as font:
            # (2024/06/11) https://stackoverflow.com/a/72228817
            debug_name = font["name"].getDebugName(4)
            if debug_name is None:
                raise ValueError(f"Cannot get name for font: {path}")
            unicode_map = font.getBestCmap()
            if unicode_map is None:
                raise ValueError(
                    f"Cannot find best unicode table in font: {debug_name}"
                )
            sized_height = (
                None if size_points is None else _get_sized_height(font, size_points)
            )

        self._path = path
        self._unicode_map: dict[int, str] = unicode_map
        self._name: str = debug_name
        self._sized_height: int | None = sized_height

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> str:
        return self._path

    @property
    def sized_height(self) -> int | None:
        return self._sized_height

    def to_dict(self) -> dict[str, str]:
        return {self._name: self._path}

    def coverage(self) -> dict[str, list[str]]:
        blocks = {}
        for char_int in self._unicode_map.keys():
            c = chr(char_int)
            if Unicode.printable(c):
                blocks.setdefault(Unicode.block(c), []).append(c)
        return blocks
