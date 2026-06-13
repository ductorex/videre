"""Versioned Unicode sequence data used by the font coverage generator."""

from __future__ import annotations

import json
import os
from functools import cache
from typing import TypedDict

from videre.fonts.coverage import UNICODE_VERSION

UNICODE_SEQUENCES_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "unicode-sequences.json"
)


class UnicodeSequenceData(TypedDict):
    schema_version: int
    unicode_version: str
    ivd_version: str
    sources: dict[str, str]
    sequences: dict[str, list[str]]


@cache
def load_unicode_sequences() -> UnicodeSequenceData:
    with open(UNICODE_SEQUENCES_PATH, encoding="utf-8") as file:
        value: UnicodeSequenceData = json.load(file)
    if value["schema_version"] != 1:
        raise ValueError(
            f"Unsupported Unicode sequence schema: {value['schema_version']}"
        )
    if value["unicode_version"] != UNICODE_VERSION:
        raise ValueError(
            f"Stale Unicode sequences: {value['unicode_version']} != {UNICODE_VERSION}"
        )
    return value
