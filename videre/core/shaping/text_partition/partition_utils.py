"""Utilities to partition text by script and font."""

import unicodedata
from dataclasses import dataclass

from videre.core.text_editing import grapheme_boundaries
from videre.fonts.coverage import is_variation_selector
from videre.fonts.provider import get_font_provider
from videre.fonts.unicode_utils import NEUTRAL_SCRIPTS, get_character


@dataclass(slots=True, frozen=True)
class TextScript:
    text: str
    script: str  # ISO 15924 code


@dataclass(slots=True, frozen=True)
class PerFont:
    text: str
    font_name: str
    font_path: str


def _split_by_script(text: str) -> list[TextScript]:
    """Split by Unicode script (UAX #24).

    Common and Inherited characters take the previous real script, or the
    following one when they occur at the start. An all-neutral string remains
    Common.
    """
    if not text:
        return []

    resolved = [get_character(c).script for c in text]

    last_real: str | None = None
    for i, script in enumerate(resolved):
        if script not in NEUTRAL_SCRIPTS:
            last_real = script
        elif last_real is not None:
            resolved[i] = last_real

    if resolved[0] in NEUTRAL_SCRIPTS:
        first_real = next(
            (script for script in resolved if script not in NEUTRAL_SCRIPTS), None
        )
        if first_real is not None:
            for i, script in enumerate(resolved):
                if script not in NEUTRAL_SCRIPTS:
                    break
                resolved[i] = first_real
        else:
            resolved = ["Zyyy"] * len(resolved)

    result: list[TextScript] = []
    chars = [text[0]]
    current_script = resolved[0]
    for c, script in zip(text[1:], resolved[1:]):
        if script == current_script:
            chars.append(c)
        else:
            result.append(TextScript("".join(chars), current_script))
            current_script = script
            chars = [c]
    result.append(TextScript("".join(chars), current_script))
    return result


def _shaping_script(text: str) -> str:
    """Return the HarfBuzz script derived from the piece's real content.

    `_split_by_script` lets neutral characters inherit a neighbouring script
    for font routing. A piece containing only neutrals must still use HarfBuzz's
    Common shaper rather than a complex shaper inherited from that neighbour.
    """
    for c in text:
        character = get_character(c)
        if not character.script_is_neutral:
            return character.script
    return "Zyyy"


def _split_by_font(text: str, script: str) -> list[PerFont]:
    """Split one script run by font.

    Format and control characters stay attached to the current font even when
    they have no cmap entry: HarfBuzz needs join controls and variation
    selectors in the same shaping buffer as the characters they modify.
    Other neutral characters stay when the cmap supports them; otherwise the
    provider selects a fallback. The unused ``script`` argument remains part
    of the helper contract because callers split by script first.
    """
    del script
    if not text:
        return []
    provider = get_font_provider()

    anchor_name: str
    anchor_path: str
    for c in text:
        if not get_character(c).script_is_neutral:
            anchor_name, anchor_path = provider.get_font_info(c)
            break
    else:
        anchor_name, anchor_path = provider.get_font_info(text[0])

    result: list[PerFont] = []
    chunks: list[str] = []
    name, path = anchor_name, anchor_path
    boundaries = grapheme_boundaries(text)
    for start, end in zip(boundaries, boundaries[1:]):
        cluster = text[start:end]
        if all(_stays_with_current_font(c) for c in cluster):
            chunks.append(cluster)
            continue

        preferred = (
            name if all(get_character(c).script_is_neutral for c in cluster) else None
        )
        char_name, char_path = provider.get_font_info_for_cluster(
            cluster, preferred_font_name=preferred
        )
        if char_name == name:
            chunks.append(cluster)
            continue
        if chunks:
            result.append(PerFont("".join(chunks), name, path))
        name, path = char_name, char_path
        chunks = [cluster]

    if chunks:
        result.append(PerFont("".join(chunks), name, path))
    return result


def _is_variation_selector(c: str) -> bool:
    return is_variation_selector(c)


def _stays_with_current_font(c: str) -> bool:
    return _is_variation_selector(c) or unicodedata.category(c) in {"Cc", "Cf"}
