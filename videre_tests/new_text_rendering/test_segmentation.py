"""Direct tests for the textutils private segmentation helpers.

`test_text_sequence.py` and `test_wrap.py` exercise segmentation
indirectly through `split_text_to_renderable` / `shape_text` /
`render_text`. This file pins the per-helper edge cases that those
high-level paths happen not to hit (empty inputs, all-neutral text,
ambiguous quotes, lead-block + CJK fusion, multi-font runs).
"""

from videre.core.shaping.texts.textutils import (
    RenderableLine,
    _split_by_font,
    _split_by_script,
    _split_by_word,
)

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
    from videre.core.shaping.texts.textutils import RenderablePiece, RenderableText

    rt = RenderableText(
        atomic=True,
        pieces=(RenderablePiece(text="x", font_name="", font_path="", script="Latn"),),
    )
    assert RenderableLine(elements=(rt,)).is_empty() is False


# -- All-neutral text --------------------------------------------------------


def test_split_by_script_all_neutral_falls_back_to_zyyy() -> None:
    """A text made only of Common/Inherited characters has no real
    script to anchor on. The implementation rewrites the resolved
    list to ``Zyyy`` everywhere, so a single LTR run is emitted."""
    runs = _split_by_script("   ")
    assert len(runs) == 1
    assert runs[0].text == "   "
    assert runs[0].script == "Zyyy"
    assert runs[0].right_to_left is False


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
