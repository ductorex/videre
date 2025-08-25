"""
Main script to generate char-support.json
"""

import json
import os
from typing import Self, Sequence

from fontTools.ttLib import TTCollection
from tqdm import tqdm

from videre.fonts import FOLDER_FONT, FONT_NOTO_REGULAR, get_fonts
from videre.fonts.font_utils import FontUtils
from videre.fonts.unicode_utils import Unicode


class CharFontPriority:
    __slots__ = ("rank", "cov")

    def __init__(
        self,
        name: str,
        character: str,
        block_to_cov: dict[str, list[str]],
        font_to_rank: dict[str, int],
    ):
        self.rank: int = font_to_rank.get(name)
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
            # both has rank
            return self.rank < other.rank


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


def generate_char_cov(priority_fonts: Sequence[str] = (FONT_NOTO_REGULAR.name,)):
    font_to_rank = {name: order for order, name in enumerate(priority_fonts)}
    font_to_block_to_cov: dict[str, dict[str, list[str]]] = {}

    fonts = _load_fonts()
    char_to_fonts = {}
    for font in fonts:
        block_to_covlen: dict[str, int] = {}
        coverage = font.coverage()
        font_to_block_to_cov[font.name] = coverage
        for block, covered_chars in coverage.items():
            for c in covered_chars:
                char_to_fonts.setdefault(c, []).append(font.name)
            block_to_covlen[block] = len(covered_chars)
    nb_unicode = len(list(Unicode.characters()))
    nb_covered = len(char_to_fonts)
    print("Characters:", nb_unicode)
    print("Covered:", nb_covered, f"({round(nb_covered * 100 / nb_unicode, 2)} %)")

    char_to_font: dict[str, str] = {}
    selected_fonts = set()
    for c, names in tqdm(char_to_fonts.items()):
        if len(names) == 1:
            (selected_name,) = names
        else:
            selected_name = sorted(
                names,
                key=lambda name: CharFontPriority(
                    name, c, font_to_block_to_cov[name], font_to_rank
                ),
            )[0]
        char_to_font[c] = selected_name
        selected_fonts.add(selected_name)

    print(f"Selected fonts: {len(selected_fonts)} / {len(fonts)}")
    selected_fonts = sorted(selected_fonts)
    selected_indices = {name: i for i, name in enumerate(selected_fonts)}
    assert len(selected_fonts) == len(selected_indices)
    char_to_indice = {c: selected_indices[name] for c, name in char_to_font.items()}
    output = {"fonts": selected_fonts, "characters": char_to_indice}
    with open(os.path.join(FOLDER_FONT, "char-support.json"), "w") as file:
        json.dump(output, file)


def main():
    # check_characters_coverage("☐☑✅✓✔🗸🗹")
    generate_char_cov()


if __name__ == "__main__":
    main()
