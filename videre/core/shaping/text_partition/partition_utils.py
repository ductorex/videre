"""Utilities to partition text by script and font."""

from dataclasses import dataclass

from videre.core.shaping.utils import load_freetype_face
from videre.fonts.provider import get_font_provider
from videre.fonts.unicode_utils import NEUTRAL_SCRIPTS, get_character

_BIDI_CONTROL_CHARS = frozenset(
    {
        chr(0x200C),  # ZWNJ - Zero Width Non-Joiner
        chr(0x200D),  # ZWJ - Zero Width Joiner
    }
)
"""Join controls currently removed before bidi resolution and shaping.

They remain printable because they affect cursive shaping. Keeping them in
the pipeline requires assigning a bidi level inherited from a neighbour; the
failing join-control regression tests cover that future work.
"""


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

    Neutral characters stay with the current font when its cmap supports them.
    Otherwise the provider selects a fallback. The unused ``script`` argument
    remains part of the helper contract because callers split by script first.
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
    chars: list[str] = []
    name, path = anchor_name, anchor_path
    for c in text:
        if get_character(c).script_is_neutral and _font_supports(path, c):
            chars.append(c)
            continue

        char_name, char_path = provider.get_font_info(c)
        if char_name == name:
            chars.append(c)
            continue
        if chars:
            result.append(PerFont("".join(chars), name, path))
        name, path = char_name, char_path
        chars = [c]

    if chars:
        result.append(PerFont("".join(chars), name, path))
    return result


def _font_supports(font_path: str, c: str) -> bool:
    """Whether ``font_path`` has a glyph for ``c``."""
    return load_freetype_face(font_path).get_char_index(ord(c)) != 0
