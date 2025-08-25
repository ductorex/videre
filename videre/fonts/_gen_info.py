import json
import os.path
from collections import Counter

from videre.fonts import FOLDER_FONT, FONT_BABEL_STONE, FONT_NOTO_REGULAR, get_fonts
from videre.fonts._gen_char_cov import _load_fonts
from videre.fonts.font_utils import FontUtils
from videre.fonts.unicode_utils import Unicode

LEAST_FONT = FONT_BABEL_STONE.name


def get_percent(a, b, decimals=2):
    return round(a * 100 / b, decimals)


# unused
def save_fonts(fonts: dict[str, str]):
    assert not FOLDER_FONT.endswith(os.sep)
    base_path = FOLDER_FONT + os.sep
    fonts_with_relative_paths = {}
    for name, path in fonts.items():
        assert path.startswith(base_path)
        relative_path = path[len(base_path) :]
        if os.sep != "/":
            relative_path = relative_path.replace(os.sep, "/")
        fonts_with_relative_paths[name] = relative_path
    output_path = os.path.join(FOLDER_FONT, "font-to-path.json")
    with open(output_path, "w") as file:
        json.dump(fonts_with_relative_paths, file, indent=1)
    print(f"Saved paths for {len(fonts)} Noto fonts at:", output_path)


def check_font():
    fu = FontUtils(FONT_NOTO_REGULAR.path)
    support = fu.coverage()
    blocks = Unicode.blocks()
    print("Font:", fu.name)
    for block, cov in support.items():
        a = len(cov["coverage"])
        b = len(blocks[block])
        assert a <= b, (block, a, b)
        print(block, a, "/", b, get_percent(a, b), "%")


def check_unicode_coverage():
    blocks = Unicode.blocks()
    nb_chars = sum(len(chars) for chars in blocks.values())
    font_objects = _load_fonts()

    nb_supported = 0
    nb_many_supported = 0
    block_cov: dict[str, set[str]] = {}
    unsupported_blocks = []
    nb_blocks_many_supported = 0
    for block, chars in blocks.items():
        block_support_count = Counter()
        for c in chars:
            local_supported = [font.name for font in font_objects if font.supports(c)]
            block_support_count.update(local_supported)
            nb_supported += bool(local_supported)
            nb_many_supported += len(local_supported) > 1
        if block_support_count.total():
            block_support: list[tuple[str, int]] = block_support_count.most_common()
            max_count = block_support[0][1]
            most_support: list[str] = [t[0] for t in block_support if t[1] == max_count]
            block_cov[block] = set(most_support)
            if len(most_support) > 1:
                nb_blocks_many_supported += 1
                print(f"{block} ({len(chars)})")
                for name in most_support:
                    print(
                        f"\t{name} => {max_count} : {get_percent(max_count, len(chars))} %"
                    )
        else:
            unsupported_blocks.append(block)
    if unsupported_blocks:
        print()
        print("** Unsupported blocks **:")
        for block in unsupported_blocks:
            print(f"\t(x) {block} => {len(blocks[block])}")

    print()
    print(f"Unicode v{Unicode.VERSION}, {nb_chars} characters, {len(blocks)} blocks.")
    print("Fonts:", len(font_objects))
    print("Coverage:")
    print(f"Chars: {nb_supported} / {nb_chars}, multiple: {nb_many_supported}")
    print(
        f"Blocks: {len(block_cov)} / {len(blocks)}, multiple: {nb_blocks_many_supported}"
    )
    print()

    for block, block_fonts in block_cov.items():
        if len(block_fonts) > 1 and LEAST_FONT in block_fonts:
            block_fonts.remove(LEAST_FONT)
            print(f"[{block}] <removed> {LEAST_FONT}")

    mandatory_fonts: set[str] = set()
    cov = block_cov
    while True:
        new_mandatory, cov = _clean_fonts(cov, mandatory_fonts)
        if new_mandatory != mandatory_fonts:
            mandatory_fonts = new_mandatory
        else:
            break

    unique_cov = {b: next(iter(cs)) for b, cs in cov.items() if len(cs) == 1}
    multiple_cov = {b: cs for b, cs in cov.items() if len(cs) > 1}

    print()
    print(
        "Mandatory fonts:",
        len(mandatory_fonts),
        f"with {LEAST_FONT}" if LEAST_FONT in mandatory_fonts else "",
    )
    print("Blocks with multiple support:", len(multiple_cov))

    cov_count = Counter()
    for fonts in multiple_cov.values():
        cov_count.update(fonts)

    resolution = {}
    for block, fonts in multiple_cov.items():
        counts = sorted(
            ((font, cov_count[font]) for font in fonts), key=lambda c: (-c[1], c[0])
        )
        selected_font = counts[0][0]
        print(f"[{block}] selected: {selected_font}")
        resolution[block] = selected_font

    final_mapping = {**unique_cov, **resolution}
    assert len(final_mapping) == len(blocks) - len(unsupported_blocks)

    unsupported_blocks = set(unsupported_blocks)
    font_map = {fu.name: fu for fu in font_objects}

    support = {}
    for block_name, block_content in blocks.items():
        if block_name not in unsupported_blocks:
            font_name = final_mapping[block_name]
            font = font_map[font_name]
            font_cov = sorted(c for c in block_content if font.supports(c))
            support[block_name] = {"font": font_name, "coverage": "".join(font_cov)}

    with open(os.path.join(FOLDER_FONT, "block-support.json"), "w") as file:
        json.dump(support, file, indent=1)


def _clean_fonts(coverage: dict[str, list | set], old_mandatory: set[str]):
    new_mandatory = set()
    new_coverage = {}
    for block, fonts in coverage.items():
        if len(fonts) == 1:
            (font,) = fonts
            new_mandatory.add(font)
        else:
            new_coverage[block] = fonts

    mandatory = old_mandatory | new_mandatory
    out_cov = {}

    print()
    for block, fonts in new_coverage.items():
        fonts = set(fonts)
        common = fonts & mandatory
        if not common:
            print(f"[{block}] <unchanged> {len(fonts)}")
            out_cov[block] = fonts
        elif len(common) == len(fonts):
            print(f"[{block}] <mandatory> {len(fonts)}")
            out_cov[block] = fonts
        else:
            print(f"[{block}] {len(fonts)} => {len(common)}")
            out_cov[block] = common

    return new_mandatory, {**coverage, **out_cov}


def check_characters_coverage(characters: str):
    font_table = get_fonts()
    fonts = _load_fonts(font_table)
    for c in characters:
        block = Unicode.block(c)
        print(f"Checking coverage for: {block}: {c}")
        for font in fonts:
            if font.supports(c):
                print(f"\t{font.name}")
