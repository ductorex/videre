"""Download and compact the normative Unicode sequence registries.

The generated file is checked in so ordinary builds and tests remain fully
offline. Run this script deliberately when Videre's pinned Unicode or IVD
version changes.
"""

import json
import urllib.request
from pathlib import Path

from videre.core.textual.coverage import UNICODE_VERSION
from videre.fonts._unicode_sequences import UNICODE_SEQUENCES_PATH

IVD_VERSION = "2025-07-14"

SOURCES = {
    "standardized_variation": (
        f"https://www.unicode.org/Public/{UNICODE_VERSION}/ucd/StandardizedVariants.txt"
    ),
    "emoji_variation": (
        f"https://www.unicode.org/Public/{UNICODE_VERSION}/ucd/emoji/"
        "emoji-variation-sequences.txt"
    ),
    "emoji_sequence": (
        f"https://www.unicode.org/Public/emoji/{UNICODE_VERSION[:2]}.0/"
        "emoji-sequences.txt"
    ),
    "emoji_zwj_sequence": (
        f"https://www.unicode.org/Public/emoji/{UNICODE_VERSION[:2]}.0/"
        "emoji-zwj-sequences.txt"
    ),
    "ideographic_variation": (
        f"https://www.unicode.org/ivd/data/{IVD_VERSION}/IVD_Sequences.txt"
    ),
}


def _download(url: str) -> str:
    with urllib.request.urlopen(url) as response:
        return response.read().decode("utf-8")


def _sequence_field(line: str) -> str | None:
    data = line.split("#", 1)[0].strip()
    if not data:
        return None
    return data.split(";", 1)[0].strip()


def _parse_variation_sequences(text: str) -> list[str]:
    sequences = {
        " ".join(f"{int(codepoint, 16):04X}" for codepoint in field.split())
        for line in text.splitlines()
        if (field := _sequence_field(line)) is not None
    }
    return sorted(sequences)


def _parse_emoji_sequences(text: str) -> list[str]:
    sequences: set[str] = set()
    for line in text.splitlines():
        field = _sequence_field(line)
        if field is None or ".." in field:
            continue
        codepoints = tuple(int(codepoint, 16) for codepoint in field.split())
        if len(codepoints) > 1:
            sequences.add(" ".join(f"{codepoint:04X}" for codepoint in codepoints))
    return sorted(sequences)


def main() -> None:
    downloaded = {name: _download(url) for name, url in SOURCES.items()}
    sequences = {
        "standardized_variation": _parse_variation_sequences(
            downloaded["standardized_variation"]
        ),
        "emoji_variation": _parse_variation_sequences(downloaded["emoji_variation"]),
        "ideographic_variation": _parse_variation_sequences(
            downloaded["ideographic_variation"]
        ),
        "emoji_sequence": _parse_emoji_sequences(downloaded["emoji_sequence"]),
        "emoji_zwj_sequence": _parse_emoji_sequences(downloaded["emoji_zwj_sequence"]),
    }
    output = {
        "schema_version": 1,
        "unicode_version": UNICODE_VERSION,
        "ivd_version": IVD_VERSION,
        "sources": SOURCES,
        "sequences": sequences,
    }
    path = Path(UNICODE_SEQUENCES_PATH)
    path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    for name, values in sequences.items():
        print(f"{name}: {len(values)}")
    print(path)


if __name__ == "__main__":
    main()
