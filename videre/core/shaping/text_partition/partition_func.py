from functools import lru_cache

from bidi.algorithm import (
    explicit_embed_and_overrides as _bidi_explicit_embed_and_overrides,
)
from bidi.algorithm import get_base_level as _bidi_get_base_level
from bidi.algorithm import get_embedding_levels as _bidi_get_embedding_levels
from bidi.algorithm import get_empty_storage as _bidi_get_empty_storage
from bidi.algorithm import resolve_implicit_levels as _bidi_resolve_implicit_levels
from bidi.algorithm import resolve_neutral_types as _bidi_resolve_neutral_types
from bidi.algorithm import resolve_weak_types as _bidi_resolve_weak_types
from uniseg.linebreak import line_break as _line_break
from uniseg.wordbreak import words as _word_segments

from videre.core.shaping.text_partition.partition_repr import (
    BidiRun,
    PerFont,
    TextLine,
    TextScript,
    Word,
)
from videre.core.shaping.utils import load_freetype_face
from videre.fonts.provider import FontProvider
from videre.fonts.unicode_utils import NEUTRAL_SCRIPTS, get_character

# Line_Break (UAX#14) classes used to classify uniseg word-segmentation tokens
# without enumerating scripts. See https://www.unicode.org/reports/tr14/.
_LB_BREAKABLE = frozenset({"ID", "H2", "H3", "JL", "JV", "JT", "SA"})
"""Characters that should reach the shaper as a single run: CJK ideographs
(ID), Hangul syllables (H2/H3) and conjoining jamo (JL/JV/JT), and SE-Asian
scripts requiring complex shaping (SA: Thai/Khmer/Lao/Myanmar/Tai Tham/...).
Tokens whose every character is in this set become non-atomic Words and
consecutive ones are coalesced into a single Word so HarfBuzz can position
vowels/marks against their consonant and font lookup runs once per run."""

_LB_TRAILING = frozenset({"EX", "IS", "CL", "CP", "BA", "NS", "IN", "HY"})
"""Punctuation that sticks to the preceding word when adjacent: ! ? (EX),
, . ; : (IS), close brackets (CL/CP), break-after such as soft hyphen (BA),
non-starters like Japanese small kana (NS), inseparables like ... (IN),
hyphen-minus (HY)."""

_LB_LEADING = frozenset({"OP"})
"""Open brackets ( [ { «: prepended to the following word."""

_LB_AMBIGUOUS = frozenset({"QU"})
"""Quotation marks (straight and typographic): direction is decided by the
adjacent whitespace - leading if there is a separator on the left and not on
the right (opening quote), trailing otherwise (closing quote)."""

_LB_WHITESPACE = frozenset({"SP", "BK", "CR", "LF", "NL", "ZW"})
"""Whitespace and mandatory-break characters; tokens made entirely of these
are dropped before classification."""

_BIDI_CONTROL_CHARS = frozenset(
    {
        chr(0x200C),  # ZWNJ - Zero Width Non-Joiner
        chr(0x200D),  # ZWJ - Zero Width Joiner
    }
)
"""Joiner characters that UAX#9's X9 rule strips before resolving
levels. They must be filtered out of a line before `_split_by_bidi`,
otherwise `len(levels) != len(text)`. The other X9-removed characters
(explicit embedding marks LRE/RLE/PDF/LRO/RLO and isolate marks
LRI/RLI/FSI/PDI) are filtered upstream by `Unicode.printable`, which
treats them as non-printable since they have no visual representation.

ZWNJ / ZWJ are NOT filtered by `Unicode.printable` because they affect
cursive shaping in Arabic / Indic scripts; consumers may legitimately
want to keep them in source text and route them to HarfBuzz. The bidi
pipeline simply drops them before resolution, which means their
contribution to shaping is currently lost — a separate ZWJ-aware
pipeline would have to keep them and inject a level inherited from the
neighbour."""


@lru_cache(maxsize=1)
def get_font_provider() -> FontProvider:
    return FontProvider()


def _split_by_line(text: str) -> list[TextLine]:
    """
    Split by line.

    Recognized line terminators: \\r\\n, \\r alone, \\n alone. Each terminator
    starts a new line; consecutive terminators yield empty lines.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [TextLine(text=part) for part in normalized.split("\n")]


def _strip_bidi_controls(text: str) -> str:
    """Remove characters that UAX#9's X9 rule strips before resolving
    levels. Must be called on a line before `_split_by_bidi`, so
    `_split_by_bidi`'s output satisfies `len(levels) == len(text)`."""
    if not any(c in _BIDI_CONTROL_CHARS for c in text):
        return text
    return "".join(c for c in text if c not in _BIDI_CONTROL_CHARS)


def _split_by_bidi(text: str) -> tuple[int, list[int]]:
    """Run UAX#9 phases X1 through I2 on `text` and return the
    paragraph base level plus per-codepoint resolved embedding levels.
    Even = LTR, odd = RTL. `len(levels) == len(text)`; the caller must
    have stripped bidi control characters (via `_strip_bidi_controls`)
    beforehand.

    Levels are returned in source order / logical text order (not visual order).
    """
    if not text:
        return 0, []
    base_level = _bidi_get_base_level(text)
    storage = _bidi_get_empty_storage()
    storage["base_level"] = base_level
    storage["base_dir"] = ("L", "R")[base_level]
    _bidi_get_embedding_levels(text, storage)
    _bidi_explicit_embed_and_overrides(storage)
    _bidi_resolve_weak_types(storage)
    _bidi_resolve_neutral_types(storage, False)
    _bidi_resolve_implicit_levels(storage, False)
    levels = [c["level"] for c in storage["chars"]]
    if len(levels) != len(text):
        raise ValueError(
            f"Bidi controls present in text: len(levels)={len(levels)} "
            f"vs len(text)={len(text)}. Call _strip_bidi_controls first."
        )
    return base_level, levels


def _split_by_word(text: str) -> list[Word]:
    """Split into words using UAX#29 word segmentation, then classify each
    token by its UAX#14 Line_Break property.

    Pipeline:
    1. ``uniseg.wordbreak.words`` segments the text. Whitespace tokens are
       dropped but their presence is remembered as a fusion barrier on the
       next non-whitespace token *and* as the source signal for
       `Word.space_before`.
    2. Each remaining token is classified via Line_Break:
       - tokens whose every character is in ``_LB_BREAKABLE`` (CJK
         ideographs, Hangul syllables, SE-Asian SA characters) are non-atomic
         fragments and get coalesced with adjacent fragments into a single
         Word so the shaper can position marks correctly and font lookup
         runs once per run;
       - tokens whose every character is in ``_LB_TRAILING`` are stuck onto
         the previous Word - this attaches commas, closing brackets,
         hyphens, etc.;
       - tokens whose every character is in ``_LB_LEADING`` are prepended
         to the next Word;
       - tokens whose every character is in ``_LB_AMBIGUOUS`` (quotes) lean
         leading or trailing depending on which side carries a separator
         (whitespace or string boundary);
       - everything else is an atomic word.
    3. Fusion (cjk coalescence, trail-to-prev, lead-to-next) is forbidden
       across any whitespace that was in the source text. ``"a b"`` always
       yields two Words even when fusion rules would otherwise apply.
    4. ``space_before`` is set on each Word from the source: True iff a
       whitespace token was seen between this Word and the previous one
       (or the start of the input). It is the rendering signal that drives
       inter-word `space_advance` insertion. UAX#29 splits between Latin
       and CJK without any whitespace, so two consecutive words may have
       ``space_before=False`` (e.g. `"Hello世界"` → [`Hello`, `世界`]).
    """
    if not text:
        return []

    raw = list(_word_segments(text))
    n_raw = len(raw)
    # `classify_sep_before` flags whether something separator-like (string
    # boundary OR whitespace) precedes the token; quote classification needs
    # this. `ws_before` is the strict source signal: True only if a real
    # whitespace token was seen, used to set `Word.space_before`.
    parts: list[tuple[str, str, bool, bool]] = []
    classify_sep_pending = True  # string boundary counts as a separator
    ws_pending = False
    for idx, token in enumerate(raw):
        if _is_whitespace_token(token):
            classify_sep_pending = True
            ws_pending = True
            continue
        sep_right = idx == n_raw - 1 or _is_whitespace_token(raw[idx + 1])
        parts.append(
            (
                token,
                _classify_token(token, classify_sep_pending, sep_right),
                classify_sep_pending,
                ws_pending,
            )
        )
        classify_sep_pending = False
        ws_pending = False

    if not parts:
        return []

    result: list[Word] = []
    i = 0
    n = len(parts)
    while i < n:
        token, kind, sep_before, ws_before = parts[i]
        if kind == "cjk":
            chunk = [token]
            j = i + 1
            while j < n and parts[j][1] == "cjk" and not parts[j][2]:
                chunk.append(parts[j][0])
                j += 1
            result.append(
                Word(text="".join(chunk), atomic=False, space_before=ws_before)
            )
            i = j
            continue
        if kind == "trail" and result and not sep_before:
            prev = result[-1]
            result[-1] = Word(
                text=prev.text + token,
                atomic=prev.atomic,
                space_before=prev.space_before,
            )
            i += 1
            continue
        if kind == "lead":
            j = i + 1
            while j < n and parts[j][1] == "lead" and not parts[j][2]:
                j += 1
            if j < n and not parts[j][2]:
                prefix = "".join(parts[k][0] for k in range(i, j))
                next_text, next_kind, _, _ = parts[j]
                if next_kind == "cjk":
                    k = j + 1
                    chunk = [prefix + next_text]
                    while k < n and parts[k][1] == "cjk" and not parts[k][2]:
                        chunk.append(parts[k][0])
                        k += 1
                    result.append(
                        Word(text="".join(chunk), atomic=False, space_before=ws_before)
                    )
                    i = k
                else:
                    result.append(
                        Word(
                            text=prefix + next_text, atomic=True, space_before=ws_before
                        )
                    )
                    i = j + 1
                continue
            # No adjacent target: emit the lead block as a standalone atomic.
            merged = "".join(parts[k][0] for k in range(i, j))
            result.append(Word(text=merged, atomic=True, space_before=ws_before))
            i = j
            continue
        # Plain word, or trail/lead blocked by a separator: emit as atomic.
        result.append(Word(text=token, atomic=True, space_before=ws_before))
        i += 1

    return result


def _split_by_level(text: str, levels: list[int]) -> list[BidiRun]:
    """Split `text` into maximal runs of consecutive codepoints sharing
    the same bidi embedding level. `levels` must be the per-codepoint
    levels returned by `_split_by_bidi(text)` so positions align."""
    if not text:
        return []
    assert len(text) == len(levels), (
        f"len(text)={len(text)} != len(levels)={len(levels)}"
    )
    runs: list[BidiRun] = []
    chunk_start = 0
    chunk_level = levels[0]
    for i in range(1, len(text)):
        if levels[i] != chunk_level:
            runs.append(BidiRun(text=text[chunk_start:i], level=chunk_level))
            chunk_start = i
            chunk_level = levels[i]
    runs.append(BidiRun(text=text[chunk_start:], level=chunk_level))
    return runs


def _split_by_script(text: str) -> list[TextScript]:
    """Split by Unicode script (UAX#24).

    NB: Common (Zyyy) and Inherited (Zinh) characters are recast to the
    previous character's script, or the next one's if they appear at the
    start of the text. If the text contains only neutrals, everything is
    treated as Common.

    Direction is intentionally not computed here — see `TextScript`.
    """
    if not text:
        return []

    resolved = [get_character(c).script for c in text]

    last_real: str | None = None
    for i, sc in enumerate(resolved):
        if sc not in NEUTRAL_SCRIPTS:
            last_real = sc
        elif last_real is not None:
            resolved[i] = last_real

    if resolved[0] in NEUTRAL_SCRIPTS:
        first_real = next((sc for sc in resolved if sc not in NEUTRAL_SCRIPTS), None)
        if first_real is not None:
            for i in range(len(resolved)):
                if resolved[i] in NEUTRAL_SCRIPTS:
                    resolved[i] = first_real
                else:
                    break
        else:
            resolved = ["Zyyy"] * len(resolved)

    result: list[TextScript] = []
    chars: list[str] = [text[0]]
    current_script = resolved[0]
    for c, sc in zip(text[1:], resolved[1:]):
        if sc == current_script:
            chars.append(c)
        else:
            result.append(TextScript(text="".join(chars), script=current_script))
            current_script = sc
            chars = [c]
    result.append(TextScript(text="".join(chars), script=current_script))
    return result


def _shaping_script(text: str) -> str:
    """Script to hand HarfBuzz for `text`, derived from its real content.

    `_split_by_script` recasts neutral characters (punctuation, spaces) to
    a neighbour's script so they stay grouped for font routing. But the
    script also selects HarfBuzz's shaping engine, and a piece made only of
    neutrals routed to a font for a *different* script — e.g. a lone `(`
    recast to "Arab" yet rendered with the Latin font — would trigger that
    script's complex fallback shaper on a font without those tables, making
    HarfBuzz probe hundreds of absent glyphs (every Arabic letter and
    presentation form). Anchoring on the first non-neutral character
    (Common when there is none) keeps the engine consistent with what the
    piece actually contains. Mirrored-bracket bidi behavior is unaffected:
    it keys off the run direction, not the script.
    """
    for c in text:
        if not get_character(c).script_is_neutral:
            return get_character(c).script
    return "Zyyy"  # Common: HarfBuzz default shaper, no complex fallback


def _is_whitespace_token(token: str) -> bool:
    return all(_line_break(c) in _LB_WHITESPACE for c in token)


def _classify_token(token: str, sep_left: bool, sep_right: bool) -> str:
    classes = {_line_break(c) for c in token}
    if classes <= _LB_BREAKABLE:
        return "cjk"
    if classes <= _LB_TRAILING:
        return "trail"
    if classes <= _LB_LEADING:
        return "lead"
    if classes <= _LB_AMBIGUOUS:
        return "lead" if sep_left and not sep_right else "trail"
    return "word"


def _split_by_font(text: str, script: str) -> list[PerFont]:
    """Split by font, using FontProvider.get_font_info per character.

    Within a run of a given Unicode script, neutral characters (Common /
    Inherited per fontTools.unicodedata.script) keep the current font when
    that font can render them (cmap lookup). Otherwise we switch to the
    font FontProvider would pick. This avoids fragmenting e.g. an Arabic
    run on every ASCII space (the Arabic font has the space glyph), while
    still routing emojis or rare symbols to a dedicated font when the
    surrounding font has no glyph for them.

    The font of the run is anchored on the first non-neutral character;
    if every character is neutral, the first character's font is used.
    """
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
        else:
            c_name, c_path = provider.get_font_info(c)
            if c_name == name:
                chars.append(c)
            else:
                if chars:
                    result.append(
                        PerFont(text="".join(chars), font_name=name, font_path=path)
                    )
                name, path = c_name, c_path
                chars = [c]
    if chars:
        result.append(PerFont(text="".join(chars), font_name=name, font_path=path))
    return result


def _font_supports(font_path: str, c: str) -> bool:
    """Whether `font_path` has a glyph for codepoint `c` (cmap lookup)."""
    return load_freetype_face(font_path).get_char_index(ord(c)) != 0
