"""
Main script to generate char-support.json
"""

import json
import logging
import os
from typing import Self, Sequence

from fontTools.ttLib import TTCollection
from tqdm import tqdm

from videre.fonts.font_utils import FontUtils
from videre.fonts.provider import FOLDER_FONT, FONT_NOTO_REGULAR, get_fonts
from videre.fonts.unicode_utils import Unicode

logger = logging.getLogger(__name__)


class CharFontPriority:
    __slots__ = ("rank", "cov")

    def __init__(
        self,
        name: str,
        character: str,
        block_to_cov: dict[str, list[str]],
        font_to_rank: dict[str, int],
    ):
        self.rank: int | None = font_to_rank.get(name)
        self.cov: int = len(block_to_cov[Unicode.block(character)])

    def __lt__(self, other: Self) -> bool:
        if self.rank is None and other.rank is None:
            # Neither self nor other have rank, use cov
            # The font with greater cov is first in order
            return self.cov > other.cov
        elif self.rank is None:
            # other has rank, then other < self
            return False
        elif other.rank is None:
            # self has rank, then self < other
            return True
        else:
            # both have rank
            return self.rank < other.rank


def generate_char_cov():
    char_to_font = generate_char_to_font()
    _gen_font_to_characters(char_to_font)


def generate_char_to_font(
    priority_fonts: Sequence[str] = (
        FONT_NOTO_REGULAR.name,
        # Math and Symbols 2 ranked above the CJK fonts so widget icons
        # (geometric shapes, dingbats) stay rendered as compact symbols
        # rather than being pulled into the CJK fonts' fullwidth style.
        "Noto Sans Math Regular",
        "Noto Sans Symbols 2 Regular",
        # CJK Light: aerated sans-serif rendering close to Yu Gothic UI Regular,
        # avoids both BabelStone (Mincho/serif) and Plangothic (too bold).
        # JP first matches the project's "modern Japanese" reference rendering;
        # the others fill in script-specific glyphs.
        "Noto Sans JP Light",
        "Noto Sans HK Light",
        "Noto Sans SC Light",
        "Noto Sans TC Light",
        "Noto Sans KR Light",
    ),
) -> dict[str, str]:
    font_to_rank = {name: order for order, name in enumerate(priority_fonts)}
    font_to_block_to_cov: dict[str, dict[str, list[str]]] = {}

    fonts = _load_fonts()

    char_to_fonts = {}
    for font in fonts:
        coverage = font.coverage()
        font_to_block_to_cov[font.name] = coverage
        for block, covered_chars in coverage.items():
            for c in covered_chars:
                char_to_fonts.setdefault(c, []).append(font.name)
    nb_unicode = len(list(Unicode.characters()))
    nb_covered = len(char_to_fonts)

    char_to_font: dict[str, str] = {
        c: (
            names[0]
            if len(names) == 1
            else sorted(
                names,
                key=lambda name: CharFontPriority(
                    name, c, font_to_block_to_cov[name], font_to_rank
                ),
            )[0]
        )
        for c, names in tqdm(char_to_fonts.items(), desc="Mapping char => font")
    }

    logger.info(
        f"fonts: {len(set(char_to_font.values()))} / {len(fonts)}, "
        f"characters: {nb_covered} / {nb_unicode} "
        f"({nb_covered * 100 / nb_unicode} %)"
    )
    return char_to_font


def _load_fonts(font_table: dict[str, str] | None = None) -> list[FontUtils]:
    font_table = font_table or get_fonts()
    fonts = []
    for path in font_table.values():
        if path.lower().endswith(".ttc"):
            with TTCollection(path, lazy=True) as coll:
                nb_fonts = len(coll)
            print(f"Found TTC file {os.path.basename(path)} with {nb_fonts} fonts")
            fonts.extend(FontUtils(path, font_index=i) for i in range(nb_fonts))
        else:
            fonts.append(FontUtils(path))
    return fonts


def _gen_font_to_characters(char_to_font: dict[str, str], save=True) -> dict[str, str]:
    font_to_chars = {}
    for char, font_name in char_to_font.items():
        font_to_chars.setdefault(font_name, []).append(char)
    font_to_characters = {
        font_name: "".join(chars) for font_name, chars in font_to_chars.items()
    }
    if save:
        with open(os.path.join(FOLDER_FONT, "font-to-characters.json"), "w") as file:
            json.dump(font_to_characters, file)
    return font_to_characters


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, force=True)
    generate_char_cov()
