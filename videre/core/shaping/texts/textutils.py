from dataclasses import dataclass
from functools import lru_cache
from typing import Iterator

from fontTools.unicodedata import script as _script_of
from fontTools.unicodedata import script_horizontal_direction as _script_h_dir
from uniseg.linebreak import line_break as _line_break
from uniseg.wordbreak import words as _word_segments

from videre.fonts.provider import FontProvider
from videre.fonts.unicode_utils import NEUTRAL_CHARACTERS, Unicode

_NEUTRAL_SCRIPTS = ("Zyyy", "Zinh")  # Common, Inherited - inherit from neighbor

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


@lru_cache(maxsize=1)
def get_font_provider() -> FontProvider:
    return FontProvider()


@dataclass(slots=True, frozen=True)
class TextLine:
    text: str


@dataclass(slots=True, frozen=True)
class TextScript:
    text: str
    script: str  # ISO 15924 code, available from fontTools.unicodedata
    right_to_left: bool = False
    """
    NB: We assume right_to_left depends on script.
    Example: arabic is always right_to_left.
    Text is kept as it-is: we assume given text is already
    in relevant order.
    Example: "تلود" 
    => script=<arabic script>, right_to_left=True, text as-is
    """


@dataclass(slots=True, frozen=True)
class Word:
    text: str
    atomic: bool
    """
    True when the consumer should keep the whole text on a single line if
    possible: scripts with explicit word separators (Latin, Cyrillic, Arabic,
    Hebrew, etc.) where the segmentation already isolated linguistic words.
    False when the consumer may break between two grapheme clusters within
    the text: runs of CJK ideographs, Hangul syllables, and SE-Asian
    scripts (Thai, Khmer, Lao, Myanmar). The whole run is coalesced into a
    single Word so HarfBuzz receives the full context for shaping (vowel
    positioning, contextual forms, ligatures) and font lookup runs once per
    run; the consumer must call grapheme-cluster segmentation to find legal
    break positions.
    """
    space_before: bool = False
    """
    True when the source had at least one whitespace token immediately
    before this word. Drives the inter-word `space_advance` insertion in
    rendering and wrapping: two adjacent words with no source whitespace
    between them (e.g. `Hello` and `世界` in `"Hello世界"` — UAX#29 word
    boundaries do not require a separator) must render flush. Always False
    on the first Word of a line.
    """


@dataclass(slots=True, frozen=True)
class PerFont:
    text: str
    font_name: str
    font_path: str


@dataclass(slots=True, frozen=True)
class RenderablePiece:
    text: str
    font_name: str
    font_path: str
    script: str
    right_to_left: bool = False


@dataclass(slots=True, frozen=True)
class RenderableText:
    atomic: bool
    """
    If False, characters can be dispatched to multiple lines if first line is not wide enough.
    If True and text is split by words, then characters must be rendered in same line if possible.
    If not possible, go to next line. If next whole line is still not enough, word is rendered
    as-is in whole line, and visually truncated by available width.
    """
    pieces: tuple[RenderablePiece, ...]
    space_before: bool = False
    """
    True when the source had whitespace immediately before this element.
    Mirrors `Word.space_before`; the rendering / wrap layers use it to
    insert an inter-word advance only when a real whitespace existed in the
    source. Always False on the first element of a line and always False
    when `split_words=False` (in that mode each line is a single Word and
    whitespace is preserved inside the piece text).
    """


@dataclass(slots=True, frozen=True)
class RenderableLine:
    elements: tuple[RenderableText, ...]

    def is_empty(self) -> bool:
        return not self.elements


def split_text_to_renderable(
    text: str, split_words: bool = False
) -> Iterator[RenderableLine]:
    """Split text into blocks of renderable characters.

    Two modes, parameterized by ``split_words``:

    - ``split_words=True`` (used by the rendering pipeline whenever a
      width is given to enable wrapping): segmentation order is
      **line → word → script → font**. ``_split_by_word`` runs on the
      whole line (UAX#29 word boundaries are multi-script aware), so
      ``"Hello世界"`` produces two distinct Words even though no
      whitespace separates them; ``Word.space_before`` records whether
      a real source whitespace preceded each Word so the renderer can
      insert a gap only where it belongs.

    - ``split_words=False`` (default, used when no width is given):
      segmentation order is **line → script → font**, with the entire
      line wrapped into one non-atomic Word per script run. Whitespace
      stays inside the piece text and is rasterized as glyphs;
      ``space_before`` is always False in this mode and the renderer
      never inserts a virtual gap.
    """
    lines = _split_by_line(text)
    for line in lines:
        elements: list[RenderableText] = []

        # Remove unprintable characters, first.
        line_text = "".join(c for c in line.text if Unicode.printable(c))

        if split_words:
            words = _split_by_word(line_text)
        elif line_text:
            words = [Word(text=line_text, atomic=False, space_before=False)]
        else:
            words = []

        for word in words:
            # A single Word may straddle several scripts (rare: UAX#29
            # word boundaries do not always coincide with UAX#24 script
            # boundaries). Each script run inside the Word becomes one
            # or more `RenderablePiece` (one per font), and they all
            # share the parent Word's `atomic` / `space_before` flags.
            scripts = _split_by_script(word.text)
            pieces: list[RenderablePiece] = []
            for script in scripts:
                for per_font in _split_by_font(script.text, script.script):
                    pieces.append(
                        RenderablePiece(
                            text=per_font.text,
                            font_name=per_font.font_name,
                            font_path=per_font.font_path,
                            script=script.script,
                            right_to_left=script.right_to_left,
                        )
                    )
            elements.append(
                RenderableText(
                    atomic=word.atomic,
                    pieces=tuple(pieces),
                    space_before=word.space_before,
                )
            )

        yield RenderableLine(elements=tuple(elements))


def _split_by_line(text: str) -> list[TextLine]:
    """Split by line. Do not wrap on any width (this is to be done by consumer).

    Recognized line terminators: \\r\\n, \\r alone, \\n alone. Each terminator
    starts a new line; consecutive terminators yield empty lines.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [TextLine(text=part) for part in normalized.split("\n")]


def _split_by_script(text: str) -> list[TextScript]:
    """Split by Unicode script (UAX#24).

    NB: Common (Zyyy) and Inherited (Zinh) characters are recast to the
    previous character's script, or the next one's if they appear at the
    start of the text. If the text contains only neutrals, everything is
    treated as Common (LTR direction).
    """
    if not text:
        return []

    resolved = [_script_of(c) for c in text]

    last_real: str | None = None
    for i, sc in enumerate(resolved):
        if sc not in _NEUTRAL_SCRIPTS:
            last_real = sc
        elif last_real is not None:
            resolved[i] = last_real

    if resolved[0] in _NEUTRAL_SCRIPTS:
        first_real = next((sc for sc in resolved if sc not in _NEUTRAL_SCRIPTS), None)
        if first_real is not None:
            for i in range(len(resolved)):
                if resolved[i] in _NEUTRAL_SCRIPTS:
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
            result.append(
                TextScript(
                    text="".join(chars),
                    script=current_script,
                    right_to_left=_script_h_dir(current_script) == "RTL",
                )
            )
            current_script = sc
            chars = [c]
    result.append(
        TextScript(
            text="".join(chars),
            script=current_script,
            right_to_left=_script_h_dir(current_script) == "RTL",
        )
    )
    return result


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
        if c not in NEUTRAL_CHARACTERS:
            anchor_name, anchor_path = provider.get_font_info(c)
            break
    else:
        anchor_name, anchor_path = provider.get_font_info(text[0])

    result: list[PerFont] = []
    chars: list[str] = []
    name, path = anchor_name, anchor_path
    for c in text:
        if c in NEUTRAL_CHARACTERS and _font_supports(path, c):
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
    # Local import: textutils is imported by shaping.pipeline, and
    # shaping.utils is imported by shaping/__init__.py, so a top-level
    # import here would close a cycle through shaping.__init__ when
    # textutils is loaded first.
    from videre.core.shaping.utils import load_freetype_face

    return load_freetype_face(font_path).get_char_index(ord(c)) != 0
