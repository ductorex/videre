"""Tests for `videre.core.textutils.TextSequence`.

The class wraps the output of `split_text_to_renderable` and exposes it as
a flat character-indexed sequence in **logical** order (i.e. Python `str`
order). These tests pin that contract: indexing and slicing must produce
exactly what the equivalent operation on the raw input string would,
within the limits documented (printable characters only; '\\n' inserted
between lines).
"""

import pytest

from videre.core.shaping.texts.text_sequence import TextSequence
from videre.core.shaping.texts.textutils import split_text_to_renderable

# Inputs used across the round-trip / index / slice tests. All printable,
# all without '\r' so that input == reconstructed.
_TEXTS = [
    "",
    "Hello, world!",
    "Hello مرحبا world",  # mixed LTR + RTL
    "السلام عليكم",  # pure Arabic
    "你好 こんにちは 안녕",  # mixed CJK
    "café naïve résumé",  # Latin with diacritics (NFC)
    "abc\ndef\nghi",  # multi-line
    "a\nb",  # minimal multi-line
    "office affix difficult",  # ligature opportunities
    "नमस्ते",  # Devanagari conjunct
]


def _ts(text: str) -> TextSequence:
    return TextSequence(split_text_to_renderable(text))


@pytest.mark.parametrize("text", _TEXTS)
def test_str_roundtrip(text: str) -> None:
    assert str(_ts(text)) == text


@pytest.mark.parametrize("text", _TEXTS)
def test_len_matches_input(text: str) -> None:
    assert len(_ts(text)) == len(text)


@pytest.mark.parametrize("text", _TEXTS)
def test_iter_matches_input(text: str) -> None:
    assert list(_ts(text)) == list(text)


@pytest.mark.parametrize("text", _TEXTS)
def test_full_slice_equals_str(text: str) -> None:
    ts = _ts(text)
    assert ts[:] == text


@pytest.mark.parametrize("text", _TEXTS)
def test_prefix_slices_match_input(text: str) -> None:
    ts = _ts(text)
    for k in range(len(text) + 1):
        assert ts[:k] == text[:k], f"mismatch at prefix length {k}"


@pytest.mark.parametrize("text", _TEXTS)
def test_suffix_slices_match_input(text: str) -> None:
    ts = _ts(text)
    n = len(text)
    for k in range(n + 1):
        assert ts[k:] == text[k:], f"mismatch at suffix start {k}"


@pytest.mark.parametrize("text", _TEXTS)
def test_index_matches_input(text: str) -> None:
    ts = _ts(text)
    for i in range(len(text)):
        assert ts[i] == text[i], f"mismatch at index {i}"


@pytest.mark.parametrize("text", _TEXTS)
def test_negative_index_matches_input(text: str) -> None:
    ts = _ts(text)
    n = len(text)
    for i in range(1, n + 1):
        assert ts[-i] == text[-i], f"mismatch at index -{i}"


@pytest.mark.parametrize(
    "key",
    [100, -100, 17],  # 17 = exactly len("Hello مرحبا world"); past last index
)
def test_out_of_range_raises(key: int) -> None:
    ts = _ts("Hello مرحبا world")
    with pytest.raises(IndexError):
        ts[key]


def test_user_example_specific_prefix() -> None:
    """Pin the exact case raised in the design discussion: ts[:7] of
    "Hello مرحبا world" must equal "Hello م" (i.e. Hello + space +
    the first Arabic codepoint, in LOGICAL order, not visual)."""
    ts = _ts("Hello مرحبا world")
    assert ts[:7] == "Hello م"
    assert ts[6] == "م"  # م, first cp of the Arabic word logically


def test_newline_between_lines() -> None:
    ts = _ts("abc\ndef")
    assert ts[3] == "\n"
    assert ts[:4] == "abc\n"
    assert ts[4:] == "def"


def test_carriage_return_normalized() -> None:
    """`_split_by_line` normalizes '\\r\\n' and '\\r' to '\\n'; the
    sequence reflects that normalization, not the raw input."""
    ts = _ts("abc\r\ndef\rghi")
    assert str(ts) == "abc\ndef\nghi"


def test_unprintable_stripped() -> None:
    """Unprintable characters are filtered by `split_text_to_renderable`,
    so the sequence is shorter than the raw input by that count."""
    ts = _ts("ab\x00cd")  # NUL is not printable
    assert str(ts) == "abcd"
    assert len(ts) == 4


def test_repr_does_not_crash() -> None:
    """repr() on a sequence containing non-Latin-1 codepoints must not
    raise; we use it for debugging and pytest assertion messages."""
    ts = _ts("Hello مرحبا")
    r = repr(ts)
    assert r.startswith("TextSequence(")


def test_constructor_accepts_iterator() -> None:
    """`split_text_to_renderable` returns an Iterator; `TextSequence`
    must consume it (not retain a one-shot iterable)."""
    it = split_text_to_renderable("abc")
    ts = TextSequence(it)
    # Second access must still work even though the underlying iterator
    # was exhausted by __init__.
    assert str(ts) == "abc"
    assert len(ts) == 3


# Roundtrip tests with split_words=True. In this mode whitespace is
# consumed during segmentation and re-injected from `space_before` at
# iteration time. UAX#29 word boundaries without whitespace (e.g.
# `Hello世界`) must not produce a phantom space.
_SPLIT_WORDS_TEXTS = [
    "Hello, world!",
    "Hello世界",  # no whitespace between Latin and CJK
    "Hello 世界",  # explicit whitespace
    "abc def",
    "abc",  # single word
    "",  # empty
]


@pytest.mark.parametrize("text", _SPLIT_WORDS_TEXTS)
def test_str_roundtrip_split_words_true(text: str) -> None:
    """In split_words=True mode the roundtrip is preserved for the
    cases above (no multiple consecutive spaces, since split_words
    collapses them to one)."""
    ts = TextSequence(split_text_to_renderable(text, split_words=True))
    assert str(ts) == text


def test_split_words_true_no_phantom_space_at_uax29_break() -> None:
    """Direct check: `Hello世界` segmented in split_words=True must
    yield exactly the source string back, with no inserted space."""
    ts = TextSequence(split_text_to_renderable("Hello世界", split_words=True))
    assert str(ts) == "Hello世界"
    assert len(ts) == 7
