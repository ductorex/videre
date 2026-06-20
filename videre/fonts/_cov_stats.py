import json
from collections import Counter
from pathlib import Path

from videre.core.unicode_char import get_character
from videre.fonts.coverage import (
    UNICODE_VERSION,
    FontCapabilities,
    font_coverage_characters,
    open_type_script_tags,
)
from videre.fonts.provider import (
    JSON_FONT_CAPABILITIES,
    JSON_FONT_TO_CHARACTERS,
    JSON_SEQUENCE_TO_FONT,
)

FOLDER_FONT = Path(__file__).resolve().parent
_COVERAGE_REPORT_PATH = FOLDER_FONT / "_coverage-report.json"
_MISSING = "<missing>"


def _load_json(path: Path | str) -> dict:
    with open(path, encoding="utf-8") as file:
        return json.load(file)


def _character_routes() -> dict[str, str]:
    font_to_characters: dict[str, str] = _load_json(JSON_FONT_TO_CHARACTERS)["fonts"]
    return {
        character: font_name
        for font_name, characters in font_to_characters.items()
        for character in characters
    }


def _font_capabilities() -> dict[str, FontCapabilities]:
    data = _load_json(JSON_FONT_CAPABILITIES)
    assert data["unicode_version"] == UNICODE_VERSION
    return {
        name: FontCapabilities.from_json(value) for name, value in data["fonts"].items()
    }


def _print_coverage_summary(report: dict) -> None:
    codepoints = report["codepoints"]
    print("[UNICODE COVERAGE]")
    print(f"\tUnicode: {report['unicode_version']}")
    print(
        f"\tCodepoints: {codepoints['covered']} / {codepoints['target']} "
        f"({codepoints['percent']:.6f} %)"
    )
    print(f"\tMissing: {len(codepoints['missing'])}")
    print(f"\tPrivate use included: {report['private_use_included']}")

    if codepoints["missing_by_block"]:
        print("\t[MISSING BY BLOCK]")
        for block, count in codepoints["missing_by_block"].items():
            print(f"\t\t{block}: {count}")


def _print_block_routing(character_to_font: dict[str, str]) -> None:
    block_to_routes: dict[str, Counter[str]] = {}
    for character in font_coverage_characters():
        block = get_character(character).block
        routes = block_to_routes.setdefault(block, Counter())
        routes[character_to_font.get(character, _MISSING)] += 1

    single_font_blocks: list[tuple[str, str, int]] = []
    multiple_font_blocks: list[tuple[str, Counter[str]]] = []
    incomplete_blocks: list[tuple[str, Counter[str]]] = []
    for block, routes in block_to_routes.items():
        if _MISSING in routes:
            incomplete_blocks.append((block, routes))
        elif len(routes) == 1:
            font, count = next(iter(routes.items()))
            single_font_blocks.append((block, font, count))
        else:
            multiple_font_blocks.append((block, routes))

    print(f"[FULL BLOCKS, SINGLE FONT] {len(single_font_blocks)}")
    for block, font, count in sorted(single_font_blocks):
        print(f"\t[{block}] {font}: {count} (full)")

    print(f"[FULL BLOCKS, MULTIPLE FONTS] {len(multiple_font_blocks)}")
    for block, routes in sorted(multiple_font_blocks):
        print(f"\t[{block}]")
        for font, count in sorted(routes.items(), key=lambda item: (-item[1], item[0])):
            print(f"\t\t{font}: {count}")

    print(f"[INCOMPLETE BLOCKS] {len(incomplete_blocks)}")
    for block, routes in sorted(incomplete_blocks):
        print(f"\t[{block}]")
        for font, count in sorted(routes.items(), key=lambda item: (-item[1], item[0])):
            print(f"\t\t{font}: {count}")


def _print_sequence_summary(report: dict, sequence_routes: dict[str, str]) -> None:
    print("[SEQUENCE COVERAGE]")
    for kind, values in report["sequences"].items():
        percent = (
            values["covered"] * 100 / values["target"] if values["target"] else 100
        )
        print(
            f"\t{kind}: {values['covered']} / {values['target']} "
            f"({percent:.6f} %), missing: {len(values['missing'])}"
        )

    print(f"\tRouted sequences: {len(sequence_routes)}")
    for font, count in Counter(sequence_routes.values()).most_common():
        print(f"\t\t{font}: {count}")


def _print_shaping_summary(report: dict) -> None:
    shaping = report["shaping"]
    print("[HARFBUZZ VALIDATION]")
    print(f"\tChecked codepoints: {shaping['checked']}")
    print(f"\t.notdef results: {len(shaping['missing'])}")
    print(f"\tMulti-glyph results: {len(shaping['multi_glyph'])}")


def _print_layout_routing(
    character_to_font: dict[str, str], capabilities: dict[str, FontCapabilities]
) -> None:
    support_counts: Counter[tuple[bool, bool]] = Counter()
    avoidable: Counter[tuple[str, str]] = Counter()
    unavoidable: Counter[tuple[str, str]] = Counter()

    for character, selected_name in character_to_font.items():
        script_tags = open_type_script_tags(character)
        if not script_tags:
            continue

        selected_capability = capabilities[selected_name]
        has_gsub = bool(selected_capability.gsub_scripts & script_tags)
        has_gpos = bool(selected_capability.gpos_scripts & script_tags)
        support_counts[has_gsub, has_gpos] += 1
        if has_gsub or has_gpos:
            continue

        alternatives = [
            name
            for name, capability in capabilities.items()
            if name != selected_name
            and capability.supports_codepoint(ord(character))
            and capability.layout_support(script_tags)
        ]
        key = (get_character(character).block, selected_name)
        if alternatives:
            avoidable[key] += 1
        else:
            unavoidable[key] += 1

    print("[CODEPOINTS ROUTING FOR GSUB/GPOS LAYOUTS]")
    print(f"\tGSUB + GPOS: {support_counts[True, True]}")
    print(f"\tGSUB only: {support_counts[True, False]}")
    print(f"\tGPOS only: {support_counts[False, True]}")
    print(f"\tNeither GSUB nor GPOS: {support_counts[False, False]}")
    print(
        f"\tNo layout despite a covering font advertising it: {sum(avoidable.values())}"
    )
    for (block, font), count in sorted(avoidable.items()):
        print(f"\t\t[{block}] {font}: {count}")
    print(
        f"\tNo layout and no covering font advertising it: {sum(unavoidable.values())}"
    )
    for (block, font), count in sorted(unavoidable.items()):
        print(f"\t\t[{block}] {font}: {count}")


def main() -> None:
    report = _load_json(_COVERAGE_REPORT_PATH)
    sequence_data = _load_json(JSON_SEQUENCE_TO_FONT)
    assert report["unicode_version"] == UNICODE_VERSION
    assert sequence_data["unicode_version"] == UNICODE_VERSION

    character_to_font = _character_routes()
    capabilities = _font_capabilities()

    _print_coverage_summary(report)
    _print_sequence_summary(report, sequence_data["sequences"])
    _print_shaping_summary(report)
    _print_layout_routing(character_to_font, capabilities)
    _print_block_routing(character_to_font)


if __name__ == "__main__":
    main()
