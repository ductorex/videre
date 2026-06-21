"""Unicode and OpenType primitives used by the font-coverage pipeline."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Iterator

from fontTools import unicodedata as fonttools_unicode

from videre.core.textual import unicode_props

_EXCLUDED_CATEGORIES = frozenset({"Cc", "Cs", "Co", "Cn", "Zl", "Zp"})
_LAYOUT_OPTIONAL_SCRIPTS = frozenset(
    {"Bopo", "Hang", "Hani", "Hira", "Kana", "Kits", "Nshu", "Tang", "Yiii"}
)

# DerivedCoreProperties.txt, Unicode 16.0.0:
# Default_Ignorable_Code_Point. Keep this pinned beside unicodedataplus so the
# font metric does not accidentally count joiners, variation selectors, tags,
# or other format controls as independently renderable characters.
_DEFAULT_IGNORABLE_RANGES = (
    (0x00AD, 0x00AD),
    (0x034F, 0x034F),
    (0x061C, 0x061C),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)
_DEFAULT_IGNORABLE_STARTS = tuple(start for start, _ in _DEFAULT_IGNORABLE_RANGES)


def is_default_ignorable(character: str) -> bool:
    """Whether ``character`` has Default_Ignorable_Code_Point in Unicode 16."""
    codepoint = ord(character)
    index = bisect_right(_DEFAULT_IGNORABLE_STARTS, codepoint) - 1
    return index >= 0 and codepoint <= _DEFAULT_IGNORABLE_RANGES[index][1]


def requires_standalone_glyph(character: str) -> bool:
    """Whether the font collection should cover this codepoint on its own.

    Private-use characters are deliberately outside the profile. Default
    ignorables are preserved in source text and shaping clusters, but are
    validated as part of sequences rather than as independent glyphs.
    """
    return unicode_props.category(
        character
    ) not in _EXCLUDED_CATEGORIES and not is_default_ignorable(character)


def font_coverage_characters() -> Iterator[str]:
    for codepoint in range(0x110000):
        character = chr(codepoint)
        if requires_standalone_glyph(character):
            yield character


def is_variation_selector(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x180B <= codepoint <= 0x180D
        or codepoint == 0x180F
        or 0xFE00 <= codepoint <= 0xFE0F
        or 0xE0100 <= codepoint <= 0xE01EF
    )


def variation_pairs(text: str) -> tuple[str, ...]:
    """Return adjacent base+selector pairs found in ``text``."""
    return tuple(
        text[index - 1 : index + 1]
        for index in range(1, len(text))
        if is_variation_selector(text[index])
    )


def open_type_script_tags(character: str) -> frozenset[str]:
    """Layout tags relevant when choosing a font for a standalone codepoint.

    CJK and related logographic/syllabic scripts can render their nominal
    glyphs directly from cmap. Their variation support is ranked separately
    through cmap format 14, so GSUB/GPOS must not overturn the established
    visual font priorities for ordinary characters.
    """
    script = unicode_props.script(character)
    if script in {"Zyyy", "Zinh", "Zzzz"} or script in _LAYOUT_OPTIONAL_SCRIPTS:
        return frozenset()
    return frozenset(fonttools_unicode.ot_tags_from_script(script))


@dataclass(slots=True, frozen=True)
class FontCapabilities:
    """Compact runtime view of one font's Unicode/OpenType capabilities."""

    codepoint_ranges: tuple[tuple[int, int], ...]
    variation_sequences: frozenset[str]
    gsub_scripts: frozenset[str]
    gpos_scripts: frozenset[str]

    @classmethod
    def from_json(cls, value: dict) -> FontCapabilities:
        return cls(
            codepoint_ranges=tuple(
                (int(start), int(end)) for start, end in value["codepoint_ranges"]
            ),
            variation_sequences=frozenset(value["variation_sequences"]),
            gsub_scripts=frozenset(value["gsub_scripts"]),
            gpos_scripts=frozenset(value["gpos_scripts"]),
        )

    def supports_codepoint(self, codepoint: int) -> bool:
        ranges = self.codepoint_ranges
        index = bisect_right(ranges, (codepoint, 0x110000)) - 1
        return index >= 0 and codepoint <= ranges[index][1]

    def supports_visible_codepoints(self, text: str) -> bool:
        return all(
            self.supports_codepoint(ord(character))
            for character in text
            if requires_standalone_glyph(character)
        )

    def layout_support(self, script_tags: frozenset[str]) -> int:
        """Number of OpenType layout tables supporting the given script."""
        if not script_tags:
            return 0
        return int(bool(self.gsub_scripts & script_tags)) + int(
            bool(self.gpos_scripts & script_tags)
        )

    def advertises_variations(self, text: str) -> bool:
        pairs = variation_pairs(text)
        return not pairs or all(pair in self.variation_sequences for pair in pairs)
