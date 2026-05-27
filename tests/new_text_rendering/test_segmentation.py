"""Direct tests for the textutils private segmentation helpers.

`test_wrap.py` exercises segmentation
indirectly through `split_text_to_renderable` / `shape_text` /
`render_text`. This file pins the per-helper edge cases that those
high-level paths happen not to hit (empty inputs, all-neutral text,
ambiguous quotes, lead-block + CJK fusion, multi-font runs).
"""

import pytest

from videre.core.shaping.textutils import (
    BidiRun,
    RenderableLine,
    RenderablePiece,
    RenderableText,
    _split_by_bidi,
    _split_by_font,
    _split_by_level,
    _split_by_script,
    _split_by_word,
    _strip_bidi_controls,
    split_text_to_renderable,
)

ARAB_ALEF = chr(0x0623)  # Arabic letter Alef with Hamza Above
ARAB_BA = chr(0x0628)  # Arabic letter Ba
ARAB_JEEM = chr(0x062C)  # Arabic letter Jeem
ARAB_WORD = ARAB_ALEF + ARAB_BA + ARAB_JEEM  # 3-codepoint Arabic chunk
LRE = chr(0x202A)  # Left-to-Right Embedding (invisible)
RLE = chr(0x202B)  # Right-to-Left Embedding (invisible)
PDF = chr(0x202C)  # Pop Directional Format (invisible)
ZWNJ = chr(0x200C)  # Zero Width Non-Joiner (invisible)

LDQ = "“"
RDQ = "”"
CJK_ZHONG = "中"
CJK_WEN = "文"


# -- Empty inputs ------------------------------------------------------------


def test_split_by_script_empty_returns_empty() -> None:
    assert _split_by_script("") == []


def test_split_by_word_empty_returns_empty() -> None:
    assert _split_by_word("") == []


def test_split_by_word_spaces_only_returns_empty() -> None:
    """Non-empty input made only of UAX#14 SP/BK/CR/LF/NL/ZW tokens
    produces no Words: each whitespace token is dropped during the
    classification pass and `parts` ends up empty. (Tabs are class
    BA — break-after — so they're treated as ordinary atomic words,
    not whitespace.)"""
    assert _split_by_word("   ") == []
    assert _split_by_word("\n\n") == []


def test_split_by_font_empty_returns_empty() -> None:
    assert _split_by_font("", "Latn") == []


def test_renderable_line_is_empty() -> None:
    assert RenderableLine(elements=()).is_empty() is True


def test_renderable_line_non_empty() -> None:
    """Sanity check on the non-empty branch (a one-element line)."""

    rt = RenderableText(
        atomic=True,
        pieces=(RenderablePiece(text="x", font_name="", font_path="", script="Latn"),),
    )
    assert RenderableLine(elements=(rt,)).is_empty() is False


# -- All-neutral text --------------------------------------------------------


def test_split_by_script_all_neutral_falls_back_to_zyyy() -> None:
    """A text made only of Common/Inherited characters has no real
    script to anchor on. The implementation rewrites the resolved
    list to ``Zyyy`` everywhere, so a single Common-script run is
    emitted. Direction is no longer carried by `TextScript` (it now
    comes from bidi resolution on the parent line)."""
    runs = _split_by_script("   ")
    assert len(runs) == 1
    assert runs[0].text == "   "
    assert runs[0].script == "Zyyy"


def test_split_by_script_leading_neutrals_inherit_next_script() -> None:
    """Neutrals at the start of the text don't have a previous script
    to inherit from; the implementation looks ahead for the first
    real script and assigns it back to those leading neutrals."""
    runs = _split_by_script("   abc")
    # Whole text gets one Latn run because spaces+abc share script after fix-up.
    assert len(runs) == 1
    assert runs[0].text == "   abc"
    assert runs[0].script == "Latn"


# -- Lead / trail / cjk fusion ----------------------------------------------


def test_lead_block_around_cjk_is_one_atomic_word() -> None:
    """`((中文))` — opening parens are LEAD, CJK is BREAKABLE,
    closing parens are TRAILING. The fusion should produce a single
    Word with the parens absorbed into the CJK chunk."""
    words = _split_by_word("((" + CJK_ZHONG + CJK_WEN + "))")
    assert len(words) == 1
    assert words[0].text == "((" + CJK_ZHONG + CJK_WEN + "))"
    assert words[0].atomic is False  # CJK chunk stays non-atomic


def test_orphan_lead_block_emits_alone() -> None:
    """A LEAD block with nothing usable to its right (whitespace
    follows) emits as a standalone atomic word."""
    words = _split_by_word("hello ((")
    assert [w.text for w in words] == ["hello", "(("]
    assert all(w.atomic for w in words)


def test_lead_block_followed_by_word() -> None:
    """A LEAD followed by a regular word merges into one atomic word."""
    words = _split_by_word("(hello)")
    assert len(words) == 1
    assert words[0].text == "(hello)"
    assert words[0].atomic is True


def test_trail_chain_sticks_to_previous_word() -> None:
    """Multiple TRAILING tokens in a row all glue onto the preceding
    word: `hello!?,` is one atomic word."""
    words = _split_by_word("hello!?,")
    assert len(words) == 1
    assert words[0].text == "hello!?,"
    assert words[0].atomic is True


def test_typographic_opening_quote_attaches_to_next() -> None:
    """A typographic opening quote at the start of the string is
    classified as `lead` (the string boundary counts as a separator
    on the left, no separator on the right) and attaches to the next
    word."""
    words = _split_by_word(LDQ + "hello" + RDQ)
    assert len(words) == 1
    assert words[0].text == LDQ + "hello" + RDQ
    assert words[0].atomic is True


def test_straight_quotes_attach_around_word() -> None:
    """Straight quotes have the same QU class; same fusion behavior."""
    words = _split_by_word('"hello"')
    assert len(words) == 1
    assert words[0].text == '"hello"'
    assert words[0].atomic is True


def test_quote_at_word_boundary_acts_as_trailing() -> None:
    """A quote with whitespace on its right behaves as `trail` —
    it sticks to the previous word, not the next."""
    words = _split_by_word("hi" + RDQ + " bye")
    # "hi" + RDQ collapses into one trail-fused word; "bye" is its own.
    assert [w.text for w in words] == ["hi" + RDQ, "bye"]


def test_cjk_words_dont_fuse_across_whitespace() -> None:
    """The CJK coalescer must respect source whitespace: `中 文`
    yields two separate Words (with the second carrying
    `space_before=True`)."""
    words = _split_by_word(CJK_ZHONG + " " + CJK_WEN)
    assert len(words) == 2
    assert words[0].text == CJK_ZHONG
    assert words[1].text == CJK_WEN
    assert words[0].space_before is False
    assert words[1].space_before is True


# -- _split_by_font ----------------------------------------------------------


def test_split_by_font_all_neutral_text_uses_first_char_font() -> None:
    """When every character is neutral, the implementation falls back
    to the font picked for `text[0]` (no real-script anchor exists)."""
    pieces = _split_by_font("   ", "Zyyy")
    assert len(pieces) == 1
    assert pieces[0].text == "   "
    # Don't pin the exact font name (depends on FontProvider config),
    # only the contract that one piece is emitted.
    assert pieces[0].font_name


def test_split_by_font_emoji_in_latin_text_splits_pieces() -> None:
    """An emoji embedded in Latin text routes to a different font
    than the surrounding letters, so the run splits into multiple
    pieces (Latin / emoji / Latin)."""
    text = "ab\U0001f600cd"  # 😀
    pieces = _split_by_font(text, "Latn")
    # Should be at least 2 pieces (Latin + emoji); often 3 if the
    # provider keeps the same font for both Latin halves.
    assert len(pieces) >= 2
    assert "".join(p.text for p in pieces) == text
    fonts = {p.font_name for p in pieces}
    assert len(fonts) >= 2  # at least one font change happened


# -- _strip_bidi_controls ---------------------------------------------------


def test_strip_bidi_controls_pure_text_is_unchanged() -> None:
    """Common case: no bidi controls in the input. The function
    short-circuits and returns the same string."""
    text = "hello world " + ARAB_WORD
    assert _strip_bidi_controls(text) is text


def test_strip_bidi_controls_removes_zwnj() -> None:
    """Zero-width non-joiner is class BN; X9 drops it during bidi
    resolution. Stripping it upstream keeps the level alignment
    invariant in `_split_by_bidi`; the cost is that cursive shaping
    won't see the explicit non-join request."""
    text = f"a{ZWNJ}b"
    assert _strip_bidi_controls(text) == "ab"


def test_strip_bidi_controls_leaves_lre_rle_pdf_alone() -> None:
    """Explicit embedding/isolate marks (LRE/RLE/PDF/...) are NOT
    handled here — they are filtered upstream by `Unicode.printable`
    since they have no visual representation. `_strip_bidi_controls`
    is only responsible for the two joiners that `Unicode.printable`
    keeps (because they affect cursive shaping)."""
    text = f"hi{LRE}there{PDF}"
    # `_strip_bidi_controls` passes them through untouched.
    assert _strip_bidi_controls(text) == text


def test_unicode_printable_rejects_explicit_bidi_formatters() -> None:
    """Sanity check that LRE/RLE/PDF/LRO/RLO/LRI/RLI/FSI/PDI are
    classified as non-printable so they get filtered before reaching
    `_split_by_bidi`."""
    from videre.fonts.unicode_utils import Unicode

    for c in (LRE, RLE, PDF):
        assert not Unicode.printable(c), f"{c!r} should be non-printable"


def test_unicode_printable_keeps_zwnj_and_zwj() -> None:
    """ZWNJ / ZWJ remain printable because they affect cursive
    shaping (Arabic, Indic). The bidi pipeline strips them later,
    inside `_split_by_bidi`, only to keep level alignment."""
    from videre.fonts.unicode_utils import Unicode

    assert Unicode.printable(ZWNJ)
    assert Unicode.printable(chr(0x200D))  # ZWJ


# -- _split_by_bidi ---------------------------------------------------------


def test_split_by_bidi_empty_returns_zero_base_and_empty_levels() -> None:
    base, levels = _split_by_bidi("")
    assert base == 0
    assert levels == []


def test_split_by_bidi_pure_ltr_all_zero() -> None:
    base, levels = _split_by_bidi("hello")
    assert base == 0
    assert levels == [0, 0, 0, 0, 0]


def test_split_by_bidi_pure_rtl_all_one_with_base_one() -> None:
    base, levels = _split_by_bidi(ARAB_WORD)
    assert base == 1
    assert levels == [1, 1, 1]


def test_split_by_bidi_mixed_ltr_context_assigns_rtl_level_one() -> None:
    """LTR paragraph base, with an RTL chunk inserted: the RTL chunk
    gets level 1, everything else stays at level 0."""
    text = "abc " + ARAB_WORD + " def"
    base, levels = _split_by_bidi(text)
    assert base == 0
    # 'a', 'b', 'c', ' ' = 0; 3 Arabic chars = 1; ' ', 'd', 'e', 'f' = 0.
    assert levels == [0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0]


def test_split_by_bidi_mixed_rtl_context_lifts_ltr_to_level_two() -> None:
    """RTL paragraph base with LTR inserted: the LTR chunk goes to
    level 2 (one above the base), demonstrating the recursive
    nature of UAX#9 levels."""
    text = ARAB_WORD + " Paris " + ARAB_WORD
    base, levels = _split_by_bidi(text)
    assert base == 1
    # 3 Arabic = 1; ' ' = 1 (neutral in RTL context); 'P','a','r','i','s' = 2;
    # ' ' = 1; 3 Arabic = 1.
    assert levels == [1, 1, 1, 1, 2, 2, 2, 2, 2, 1, 1, 1, 1]


def test_split_by_bidi_neutrals_inherit_paragraph_direction() -> None:
    """The colon and the slash in the 'turc ottoman' example are
    neutrals. UAX#9 assigns them the paragraph direction (LTR here),
    not the direction of the adjacent RTL run."""
    text = "fr : " + ARAB_WORD + " / en"
    base, levels = _split_by_bidi(text)
    assert base == 0
    # 'f','r',' ',':',' ' = 0 (5 chars); 3 Arabic = 1; ' ','/',' ','e','n' = 0
    # (5 chars).
    assert len(levels) == len(text)
    assert levels[:5] == [0] * 5
    assert levels[5:8] == [1, 1, 1]
    assert levels[8:] == [0] * 5


def test_split_by_bidi_raises_on_bidi_control_chars() -> None:
    """If the caller forgot to call `_strip_bidi_controls` first, the
    X9-removed characters create a length mismatch that the function
    refuses to paper over silently."""
    with pytest.raises(ValueError, match="Bidi controls present"):
        _split_by_bidi(f"hi{LRE}there{PDF}")


# -- _split_by_level --------------------------------------------------------


def test_split_by_level_empty_returns_empty() -> None:
    assert _split_by_level("", []) == []


def test_split_by_level_single_level_yields_one_run() -> None:
    runs = _split_by_level("hello", [0, 0, 0, 0, 0])
    assert runs == [BidiRun(text="hello", level=0)]


def test_split_by_level_alternating_levels_yields_distinct_runs() -> None:
    """Two adjacent LTR/RTL chunks: one run per level."""
    text = "ab" + ARAB_WORD
    runs = _split_by_level(text, [0, 0, 1, 1, 1])
    assert runs == [BidiRun(text="ab", level=0), BidiRun(text=ARAB_WORD, level=1)]


def test_split_by_level_three_runs_alternating() -> None:
    text = "ab" + ARAB_WORD + "cd"
    runs = _split_by_level(text, [0, 0, 1, 1, 1, 0, 0])
    assert runs == [
        BidiRun(text="ab", level=0),
        BidiRun(text=ARAB_WORD, level=1),
        BidiRun(text="cd", level=0),
    ]


def test_split_by_level_asserts_len_mismatch() -> None:
    with pytest.raises(AssertionError):
        _split_by_level("ab", [0])


# -- split_text_to_renderable: bidi propagation -----------------------------


def _collect_pieces(text: str, split_words: bool = True) -> list:
    """Flatten a `split_text_to_renderable` result to a list of pieces."""
    return [
        piece
        for line in split_text_to_renderable(text, split_words=split_words)
        for element in line.elements
        for piece in element.pieces
    ]


def test_pipeline_pure_ltr_pieces_all_level_zero() -> None:
    pieces = _collect_pieces("hello world")
    assert all(p.bidi_level == 0 for p in pieces)
    assert all(p.right_to_left is False for p in pieces)


def test_pipeline_pure_rtl_pieces_all_level_one() -> None:
    pieces = _collect_pieces(ARAB_WORD)
    assert all(p.bidi_level == 1 for p in pieces)
    assert all(p.right_to_left is True for p in pieces)


def test_pipeline_mixed_ltr_then_rtl_then_ltr() -> None:
    """An LTR-RTL-LTR sentence yields pieces whose levels follow the
    UAX#9 resolution, not the per-script direction. In particular,
    neutrals between LTR and RTL stay at the LTR paragraph level."""
    pieces = _collect_pieces("hi " + ARAB_WORD + " bye")
    levels = [p.bidi_level for p in pieces]
    # Exactly one RTL run (level 1), surrounded by LTR (level 0).
    assert 1 in levels
    assert 0 in levels
    rtl_pieces = [p for p in pieces if p.bidi_level == 1]
    assert len(rtl_pieces) == 1
    assert rtl_pieces[0].text == ARAB_WORD


def test_pipeline_turc_ottoman_style_neutrals_stay_ltr() -> None:
    """`fr : <arabe> / en`: the colon, the slash and the surrounding
    spaces are neutrals; in an LTR paragraph they get level 0, NOT
    level 1, so they belong to LTR pieces, not the Arabic piece."""
    pieces = _collect_pieces("fr : " + ARAB_WORD + " / en")
    rtl_pieces = [p for p in pieces if p.right_to_left]
    assert len(rtl_pieces) == 1
    assert rtl_pieces[0].text == ARAB_WORD
    # The colon and slash are in LTR pieces.
    ltr_text = "".join(p.text for p in pieces if not p.right_to_left)
    assert ":" in ltr_text
    assert "/" in ltr_text


def test_pipeline_rtl_context_lifts_ltr_run_to_level_two() -> None:
    """When the paragraph base is RTL, an inserted LTR run gets
    level 2 (one above the base) — exposes that bidi levels are
    recursive, not just a boolean."""
    pieces = _collect_pieces(ARAB_WORD + " Paris " + ARAB_WORD)
    levels = sorted({p.bidi_level for p in pieces})
    assert levels == [1, 2]
    level_two = [p for p in pieces if p.bidi_level == 2]
    assert len(level_two) == 1
    assert level_two[0].text == "Paris"


def test_pipeline_space_before_preserved_across_bidi_boundary() -> None:
    """The space between `hi` and the Arabic word is real source
    whitespace; the bidi pre-segmentation must not break `space_before`
    on the Arabic Word."""
    lines = list(split_text_to_renderable("hi " + ARAB_WORD, split_words=True))
    assert len(lines) == 1
    elements = lines[0].elements
    # Two words: "hi" (no space before, first), then Arabic (space before).
    assert len(elements) == 2
    assert elements[0].pieces[0].text == "hi"
    assert elements[0].space_before is False
    assert elements[1].pieces[0].text == ARAB_WORD
    assert elements[1].space_before is True


def test_pipeline_bidi_controls_stripped_silently() -> None:
    """If the source text carries explicit bidi controls (LRE/PDF/...),
    they are filtered out before bidi resolution so positions stay
    consistent with the rendered glyphs."""
    pieces = _collect_pieces(f"hi{LRE}there{PDF}", split_words=False)
    text = "".join(p.text for p in pieces)
    assert text == "hithere"  # bidi controls gone, rest intact
