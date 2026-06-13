"""
https://notofonts.github.io/
https://github.com/notofonts/notofonts.github.io

https://github.com/notofonts/noto-cjk
https://github.com/googlefonts/noto-emoji
https://www.babelstone.co.uk/Fonts/Han.html
https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project
"""

import json
import os
from functools import cache

from videre.fonts.coverage import (
    UNICODE_VERSION,
    FontCapabilities,
    requires_standalone_glyph,
    variation_pairs,
)
from videre.fonts.font_utils import FontUtils


def _file_path(base, *path_pieces) -> str:
    path = os.path.abspath(os.path.join(base, *path_pieces))
    assert os.path.isfile(path)
    return path


def _dir_path(base, *path_pieces) -> str:
    path = os.path.join(base, *path_pieces)
    assert os.path.isdir(path)
    return path


def _font_paths(folder: str) -> list[str]:
    return [_file_path(folder, name) for name in os.listdir(folder)]


FOLDER_FONT = os.path.abspath(os.path.dirname(__file__))

_PATH_BABEL_STONE_HAN = _file_path(FOLDER_FONT, "other-ttf/BabelStoneHan.ttf")
_PATH_PLANGOTHIC_P1 = _file_path(FOLDER_FONT, "plangothic", "PlangothicP1-Regular.ttf")
_PATH_PLANGOTHIC_P2 = _file_path(FOLDER_FONT, "plangothic", "PlangothicP2-Regular.ttf")
_FOLDER_NOTO = _dir_path(FOLDER_FONT, "noto", "unhinted", "TTF")
_FOLDER_NOTO_SERIF = _dir_path(FOLDER_FONT, "noto-serif", "unhinted", "TTF")
_FOLDER_NOTO_MONO = _dir_path(FOLDER_FONT, "noto-mono", "unhinted", "TTF")
_FOLDER_NOTO_CJK_LIGHT = _dir_path(FOLDER_FONT, "noto-cjk-static", "light")

_NOTO_FONTS = _font_paths(_FOLDER_NOTO)
_NOTO_SERIF_FONTS = _font_paths(_FOLDER_NOTO_SERIF)
_NOTO_CJK_LIGHT_FONTS = _font_paths(_FOLDER_NOTO_CJK_LIGHT)

# TODO: NB: User should be able to use a specific font (ncluding mono) if he wants.

PATH_NOTO_MONO = _file_path(_FOLDER_NOTO_MONO, "NotoSansMono-Regular.ttf")

FONT_BABEL_STONE = FontUtils(_PATH_BABEL_STONE_HAN)
FONT_PLANGOTHIC_P1 = FontUtils(_PATH_PLANGOTHIC_P1)
FONT_PLANGOTHIC_P2 = FontUtils(_PATH_PLANGOTHIC_P2)
FONT_NOTO_REGULAR = FontUtils(_file_path(_FOLDER_NOTO, "NotoSans-Regular.ttf"))
FONT_NOTO_MONO = FontUtils(PATH_NOTO_MONO)


def _get_fonts(paths: list[str]) -> dict[str, str]:
    output = {}
    for path in paths:
        output.update(FontUtils(path).to_dict())
    assert len(output) == len(paths)
    return output


def _get_noto_fonts() -> dict[str, str]:
    sans_fonts = _get_fonts(_NOTO_FONTS)
    serif_fonts = _get_fonts(_NOTO_SERIF_FONTS)
    cjk_light_fonts = _get_fonts(_NOTO_CJK_LIGHT_FONTS)
    fonts = {**sans_fonts, **serif_fonts, **cjk_light_fonts}
    assert len(fonts) == len(sans_fonts) + len(serif_fonts) + len(cjk_light_fonts)
    return fonts


def get_fonts() -> dict[str, str]:
    noto_fonts = _get_noto_fonts()
    extras = {
        **FONT_BABEL_STONE.to_dict(),
        **FONT_PLANGOTHIC_P1.to_dict(),
        **FONT_PLANGOTHIC_P2.to_dict(),
        **FONT_NOTO_MONO.to_dict(),
    }
    assert len(extras) == 4
    fonts = {**noto_fonts, **extras}
    assert len(fonts) == len(noto_fonts) + len(extras)
    return fonts


class FontProvider:
    """
    _font_name_to_path: dictionary mapping font name to font file path
    _fonts: list of font names referenced by index in `_characters`
    _characters: dictionary mapping a character to index of font in `_fonts` list.

    To get the font file path for a given character `c`:
        _font_name_to_path[_fonts[_characters[c]]]
    """

    __slots__ = (
        "_font_name_to_path",
        "_fonts",
        "_characters",
        "_capabilities",
        "_sequence_to_font",
    )

    @classmethod
    def _load_font_to_characters(cls):
        with open(
            os.path.join(FOLDER_FONT, "font-to-characters.json"), encoding="utf-8"
        ) as file:
            font_to_characters: dict[str, str] = json.load(file)
        return cls._parse_font_to_characters(font_to_characters)

    @classmethod
    def _parse_font_to_characters(
        cls, font_to_characters: dict[str, str]
    ) -> tuple[list[str], dict[str, int]]:
        fonts: list[str] = sorted(font_to_characters.keys())
        char_to_indice: dict[str, int] = {}
        font_to_indice = {font: indice for indice, font in enumerate(fonts)}
        for font, characters in font_to_characters.items():
            indice = font_to_indice[font]
            for char in characters:
                char_to_indice[char] = indice
        return fonts, char_to_indice

    @classmethod
    def _load_capabilities(cls) -> dict[str, FontCapabilities]:
        path = os.path.join(FOLDER_FONT, "font-capabilities.json")
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
        if value["schema_version"] != 1:
            raise ValueError(
                f"Unsupported font capability schema: {value['schema_version']}"
            )
        if value["unicode_version"] != UNICODE_VERSION:
            raise ValueError(
                "Stale font capabilities: "
                f"{value['unicode_version']} != {UNICODE_VERSION}"
            )
        return {
            name: FontCapabilities.from_json(capability)
            for name, capability in value["fonts"].items()
        }

    @classmethod
    def _load_sequence_to_font(cls) -> dict[str, str]:
        path = os.path.join(FOLDER_FONT, "sequence-to-font.json")
        with open(path, encoding="utf-8") as file:
            value = json.load(file)
        if value["schema_version"] != 1:
            raise ValueError(
                f"Unsupported sequence routing schema: {value['schema_version']}"
            )
        if value["unicode_version"] != UNICODE_VERSION:
            raise ValueError(
                "Stale sequence routing: "
                f"{value['unicode_version']} != {UNICODE_VERSION}"
            )
        return value["sequences"]

    def __init__(self):
        self._font_name_to_path: dict[str, str] = get_fonts()
        self._fonts, self._characters = self._load_font_to_characters()
        self._capabilities = self._load_capabilities()
        self._sequence_to_font = self._load_sequence_to_font()

    def has_font_info(self, character: str) -> bool:
        return character in self._characters

    def get_font_info(self, character: str) -> tuple[str, str]:
        if character in self._characters:
            name = self._fonts[self._characters[character]]
            path = self._font_name_to_path[name]
        else:
            name = FONT_NOTO_REGULAR.name
            path = FONT_NOTO_REGULAR.path
        return name, path

    def get_font_info_for_cluster(
        self, text: str, preferred_font_name: str | None = None
    ) -> tuple[str, str]:
        """Choose one font for a complete grapheme/shaping cluster."""
        if not text:
            raise ValueError("Cannot select a font for an empty cluster")

        sequence_font = self._sequence_to_font.get(text)
        if sequence_font is not None:
            return sequence_font, self._font_name_to_path[sequence_font]

        visible = [
            character for character in text if requires_standalone_glyph(character)
        ]
        if not visible:
            if preferred_font_name is not None:
                return (
                    preferred_font_name,
                    self._font_name_to_path[preferred_font_name],
                )
            return self.get_font_info(text[0])

        pairs = variation_pairs(text)
        advertised = (
            {
                name
                for name, capability in self._capabilities.items()
                if capability.advertises_variations(text)
            }
            if pairs
            else set()
        )

        preferred = []
        if preferred_font_name is not None:
            preferred.append(preferred_font_name)
        for character in visible:
            name, _ = self.get_font_info(character)
            if name not in preferred:
                preferred.append(name)

        candidates = preferred + [
            name for name in self._capabilities if name not in preferred
        ]
        for name in candidates:
            capability = self._capabilities[name]
            if not capability.supports_visible_codepoints(text):
                continue
            if advertised and name not in advertised:
                continue
            return name, self._font_name_to_path[name]

        return self.get_font_info(visible[0])


@cache
def get_font_provider() -> FontProvider:
    """The process-wide `FontProvider` singleton (`@cache` on a no-arg func)."""
    return FontProvider()
