from typing import TypedDict

from videre.fonts._gen_char_cov import _gen_font_to_characters, generate_char_to_font
from videre.fonts.provider import FONT_NOTO_REGULAR, FontProvider


class CharSupport(TypedDict):
    fonts: list[str]
    characters: dict[str, int]


def _gen_char_support(char_to_font: dict[str, str]) -> CharSupport:
    selected_fonts = sorted(set(char_to_font.values()))
    selected_indices = {name: i for i, name in enumerate(selected_fonts)}
    assert len(selected_fonts) == len(selected_indices)
    char_to_indice = {c: selected_indices[name] for c, name in char_to_font.items()}
    return {"fonts": selected_fonts, "characters": char_to_indice}


def test_generate_char_cov():
    char_to_font = generate_char_to_font()
    char_support = _gen_char_support(char_to_font)
    font_to_characters = _gen_font_to_characters(char_to_font, save=False)

    # 149804 = 149813 (previous total) minus 9 explicit bidi formatters
    # (LRE/RLE/PDF/LRO/RLO/LRI/RLI/FSI/PDI) now treated as non-printable
    # by `Unicode.printable` since they have no visual representation.
    assert len(char_to_font) == 149804
    assert len(set(char_to_font.values())) == 167

    fonts, char_to_indice = FontProvider._parse_font_to_characters(font_to_characters)
    assert fonts
    assert char_to_indice
    assert fonts == char_support["fonts"]
    assert char_to_indice == char_support["characters"]


def test_pygame_font_cache():
    import pygame.freetype

    pygame.freetype.init()

    path = FONT_NOTO_REGULAR.path

    font_s15 = pygame.freetype.Font(path, size=15)

    font_s20 = pygame.freetype.Font(path, size=20)

    font_s15_i = pygame.freetype.Font(path, size=15)
    font_s15_i.oblique = True

    font_s15_b = pygame.freetype.Font(path, size=15)
    font_s15_b.strong = True

    assert font_s15.size == 15
    assert not font_s15.strong
    assert not font_s15.oblique

    assert font_s20.size == 20
    assert not font_s20.strong
    assert not font_s20.oblique

    assert font_s15_i.size == 15
    assert not font_s15_i.strong
    assert font_s15_i.oblique

    assert font_s15_b.size == 15
    assert font_s15_b.strong
    assert not font_s15_b.oblique

    pygame.freetype.quit()
