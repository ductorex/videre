import functools
from dataclasses import dataclass

from videre.core.textual import unicode_props
from videre.core.textual.coverage import requires_standalone_glyph

_COMMON_SCRIPT = "Zyyy"
_INHERITED_SCRIPT = "Zinh"
NEUTRAL_SCRIPTS = (_COMMON_SCRIPT, _INHERITED_SCRIPT)


@dataclass(slots=True, frozen=True)
class Character:
    c: str
    # Unicode block: the contiguous codepoint range the character sits in,
    # e.g. "Basic Latin" = U+0000..U+007F. A block is just an address range; it
    # may mix several scripts and contain unassigned codepoints.
    block: str
    # Unicode script (UAX#24): the writing system the character belongs to
    # (Latin, Arabic, Han, Common, Inherited...). Unlike a block, one script can
    # span many blocks. Four-letter ISO 15924 code.
    script: str
    script_is_rtl: bool
    script_is_neutral: bool
    is_european_number: bool
    is_arabic_number: bool

    def requires_font_glyph(self) -> bool:
        return requires_standalone_glyph(self.c)


@functools.cache
def get_character(c: str) -> Character:
    if len(c) != 1:
        raise ValueError(f"Character {c!r} is not a single character")

    block = unicode_props.block(c)
    script = unicode_props.script(c)
    script_is_rtl = unicode_props.script_direction(script) == "RTL"
    # Number: European number (EN), arabic number (AN).
    bidirectional = unicode_props.bidirectional(c)
    is_european_number = bidirectional == "EN"
    is_arabic_number = bidirectional == "AN"
    neutral = script in NEUTRAL_SCRIPTS
    return Character(
        c,
        block=block,
        script=script,
        script_is_rtl=script_is_rtl,
        script_is_neutral=neutral,
        is_european_number=is_european_number,
        is_arabic_number=is_arabic_number,
    )
