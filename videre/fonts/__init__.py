"""
https://notofonts.github.io/
https://github.com/notofonts/notofonts.github.io

https://github.com/notofonts/noto-cjk
https://github.com/googlefonts/noto-emoji
https://www.babelstone.co.uk/Fonts/Han.html
"""

import json
import os

from fontTools.ttLib import TTFont


def _file_path(base, *path_pieces) -> str:
    path = os.path.abspath(os.path.join(base, *path_pieces))
    assert os.path.isfile(path)
    return path


def _font_paths(folder: str) -> list[str]:
    return [_file_path(folder, name) for name in os.listdir(folder)]


FOLDER_FONT = os.path.abspath(os.path.join(os.path.dirname(__file__)))
PATH_BABEL_STONE_HAN = _file_path(FOLDER_FONT, "other-ttf/BabelStoneHan.ttf")

_FOLDER_NOTO = os.path.join(FOLDER_FONT, "noto", "unhinted", "TTF")
_FOLDER_NOTO_SERIF = os.path.join(FOLDER_FONT, "noto-serif", "unhinted", "TTF")
_FOLDER_NOTO_MONO = os.path.join(FOLDER_FONT, "noto-mono", "unhinted", "TTF")

_NOTO_FONTS = _font_paths(_FOLDER_NOTO)
_NOTO_SERIF_FONTS = _font_paths(_FOLDER_NOTO_SERIF)

# TODO: NB: Mono font is not yet used. User should be able to use it if he wants.
PATH_NOTO_MONO = _file_path(_FOLDER_NOTO_MONO, "NotoSansMono-Regular.ttf")

PATH_NOTO_REGULAR = _file_path(_FOLDER_NOTO, "NotoSans-Regular.ttf")


class _FontInfo:
    __slots__ = ("name", "path")

    def __init__(self, path: str):
        with TTFont(path) as font:
            self.name = font["name"].getDebugName(4)
        self.path = path

    def __repr__(self):
        return f"({self.name})[{self.path}]"

    def to_dict(self):
        return {self.name: self.path}


FONT_BABEL_STONE = _FontInfo(PATH_BABEL_STONE_HAN)
FONT_NOTO_REGULAR = _FontInfo(PATH_NOTO_REGULAR)


def _get_fonts(paths: list[str]) -> dict[str, str]:
    output = {}
    for path in paths:
        with TTFont(path) as font:
            output[font["name"].getDebugName(4)] = path
    assert len(output) == len(paths)
    return output


def _get_noto_fonts() -> dict[str, str]:
    sans_fonts = _get_fonts(_NOTO_FONTS)
    serif_fonts = _get_fonts(_NOTO_SERIF_FONTS)
    fonts = {**sans_fonts, **serif_fonts}
    assert len(fonts) == len(sans_fonts) + len(serif_fonts)
    return fonts


def get_fonts() -> dict[str, str]:
    noto_fonts = _get_noto_fonts()
    fonts = {**noto_fonts, **FONT_BABEL_STONE.to_dict()}
    assert len(fonts) == len(noto_fonts) + 1
    return fonts


class FontProvider:
    """
    _font_name_to_path: dictionary mapping font name to font file path
    _fonts: list of font names referenced by index in `_characters`
    _characters: dictionary mapping a character to index of font in `_fonts` list.

    To get the font file path for a given character `c`:
        _font_name_to_path[_fonts[_characters[c]]]
    """

    __slots__ = ("_font_name_to_path", "_fonts", "_characters")

    @classmethod
    def _load_char_support(cls):
        # Currently unused
        with open(os.path.join(FOLDER_FONT, "char-support.json")) as file:
            char_support = json.load(file)
        fonts: list[str] = char_support["fonts"]
        characters: dict[str, int] = char_support["characters"]
        return fonts, characters

    @classmethod
    def _load_font_to_characters(cls):
        with open(os.path.join(FOLDER_FONT, "font-to-characters.json")) as file:
            font_to_characters: dict[str, str] = json.load(file)
        return cls._parse_font_to_characters(font_to_characters)

    @classmethod
    def _parse_font_to_characters(cls, font_to_characters: dict[str, str]):
        fonts: list[str] = sorted(font_to_characters.keys())
        char_to_indice: dict[str, int] = {}
        font_to_indice = {font: indice for indice, font in enumerate(fonts)}
        for font, characters in font_to_characters.items():
            indice = font_to_indice[font]
            for char in characters:
                char_to_indice[char] = indice
        return fonts, char_to_indice

    def __init__(self):
        self._font_name_to_path: dict[str, str] = get_fonts()
        self._fonts, self._characters = self._load_font_to_characters()

    def get_font_info(self, character: str) -> tuple[str, str]:
        if character in self._characters:
            name = self._fonts[self._characters[character]]
            path = self._font_name_to_path[name]
        else:
            name = FONT_NOTO_REGULAR.name
            path = FONT_NOTO_REGULAR.path
        return name, path
