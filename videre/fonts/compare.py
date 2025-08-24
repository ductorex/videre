import sys
import json


def main():
    path1 = sys.argv[1]
    path2 = sys.argv[2]

    with open(path1, encoding="utf-8") as f:
        data_1 = json.load(f)

    with open(path2, encoding="utf-8") as f:
        data_2 = json.load(f)

    fonts_1: list[str] = data_1["fonts"]
    fonts_2: list[str] = data_2["fonts"]
    if len(fonts_1) != len(fonts_2):
        set_fonts_1 = set(fonts_1)
        set_fonts_2 = set(fonts_2)
        only_in_fonts_1 = set_fonts_1 - set_fonts_2
        only_in_fonts_2 = set_fonts_2 - set_fonts_1
        if only_in_fonts_1:
            print("Only in left:", len(only_in_fonts_1))
            for font in sorted(only_in_fonts_1):
                print(f"\t{font}")
        if only_in_fonts_2:
            print("Only in right:", len(only_in_fonts_2))
            for font in sorted(only_in_fonts_2):
                print(f"\t{font}")
        return

    char_to_font_1: dict[str, int] = data_1["characters"]
    char_to_font_2: dict[str, int] = data_2["characters"]
    set_char_to_font_1 = set(char_to_font_1)
    set_char_to_font_2 = set(char_to_font_2)
    chars_only_in_font_1 = set_char_to_font_1 - set_char_to_font_2
    chars_only_in_font_2 = set_char_to_font_2 - set_char_to_font_1
    common_chars = set_char_to_font_1 & set_char_to_font_2
    if chars_only_in_font_1:
        print("Only in left:", len(chars_only_in_font_1))
        print("\t" + "".join(sorted(chars_only_in_font_1)))
    if chars_only_in_font_2:
        print("Only in right:", len(chars_only_in_font_2))
        print("\t" + "".join(sorted(chars_only_in_font_2)))
    nb_common = len(common_chars)
    for i, char in enumerate(common_chars):
        value_font_1 = fonts_1[char_to_font_1[char]]
        value_font_2 = fonts_2[char_to_font_2[char]]
        if value_font_1 != value_font_2:
            print(f"[{i + 1}/{nb_common}] {char}: {value_font_1} != {value_font_2}")



if __name__ == '__main__':
    main()
