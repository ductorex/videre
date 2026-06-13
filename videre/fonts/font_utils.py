from fontTools.ttLib import TTFont

from videre.fonts.coverage import (
    FontCapabilities,
    codepoints_to_ranges,
    requires_standalone_glyph,
)
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
    __slots__ = ("_path", "_font_index", "_unicode_map", "_name", "_sized_height")

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
        self._font_index = font_index
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
    def font_index(self) -> int:
        return self._font_index

    @property
    def sized_height(self) -> int | None:
        return self._sized_height

    def to_dict(self) -> dict[str, str]:
        return {self._name: self._path}

    def supports_raw_codepoint(self, codepoint: int) -> bool:
        return codepoint in self._unicode_map

    def coverage(self) -> dict[str, list[str]]:
        blocks = {}
        for char_int in self._unicode_map.keys():
            c = chr(char_int)
            if requires_standalone_glyph(c):
                blocks.setdefault(Unicode.block(c), []).append(c)
        return blocks

    def capabilities(self) -> FontCapabilities:
        with TTFont(self._path, fontNumber=self._font_index, lazy=True) as font:
            variation_sequences = frozenset(
                chr(base) + chr(selector)
                for table in font["cmap"].tables
                if table.format == 14
                for selector, entries in table.uvsDict.items()
                for base, _glyph_name in entries
                if Unicode.requires_font_glyph(chr(base))
            )
            gsub_scripts = _layout_scripts(font, "GSUB")
            gpos_scripts = _layout_scripts(font, "GPOS")
        codepoints = (
            codepoint
            for codepoint in self._unicode_map
            if requires_standalone_glyph(chr(codepoint))
        )
        return FontCapabilities(
            codepoint_ranges=codepoints_to_ranges(codepoints),
            variation_sequences=variation_sequences,
            gsub_scripts=gsub_scripts,
            gpos_scripts=gpos_scripts,
        )


def _layout_scripts(font: TTFont, table_name: str) -> frozenset[str]:
    if table_name not in font:
        return frozenset()
    script_list = font[table_name].table.ScriptList  # ty: ignore[unresolved-attribute]
    if script_list is None:
        return frozenset()
    return frozenset(record.ScriptTag for record in script_list.ScriptRecord)
