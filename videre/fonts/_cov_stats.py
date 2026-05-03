from videre.fonts.provider import FontProvider
from videre.fonts.unicode_utils import Unicode


def main():
    provider = FontProvider()
    unicode_blocks = Unicode.blocks()

    full_coverage: list[tuple[str, str, list[str]]] = []
    dispatched_coverage: list[tuple[str, dict[str, list[str]]]] = []

    for block, characters in unicode_blocks.items():
        font_to_chars: dict[str, list[str]] = {}
        for char in characters:
            if provider.has_font_info(char):
                name, _ = provider.get_font_info(char)
                font_to_chars.setdefault(name, []).append(char)
            else:
                font_to_chars.setdefault("<fallback>", []).append(char)
        if len(font_to_chars) == 1:
            font, chars = font_to_chars.popitem()
            assert len(chars) == len(characters)
            full_coverage.append((block, font, chars))
        else:
            dispatched_coverage.append((block, font_to_chars))

    print("[FULL COVERAGE]", len(full_coverage))
    for block, font, chars in full_coverage:
        print(f"\t[{block}] {font}: {len(chars)} (full)")
    print("[DISPATCHED COVERAGE]", len(dispatched_coverage))
    for block, font_to_chars in dispatched_coverage:
        print(f"\t[{block}]")
        for font, chars in sorted(
            font_to_chars.items(), key=lambda item: (-len(item[1]), item[0])
        ):
            print(f"\t\t{font}: {len(chars)}")


if __name__ == "__main__":
    main()
