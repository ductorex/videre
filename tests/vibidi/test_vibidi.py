"""Unit tests for the pure-Python bidi core in `videre.core.vibidi`.

These pin the behaviour of each UAX#9 phase the module implements (P, X1-X10,
W, N0, N1/N2, I) plus the L2 reordering, on small hand-checked cases. The
exhaustive conformance run against Unicode's BidiCharacterTest.txt lives in
`test_bidi_character.py`; this file is the readable, fast first line of defence.
"""

from videre.core import unicode_props
from videre.core.vibidi.vibidi import _BRACKETS_FILE, RtlPolicy, vibidi

HEB = "אבג"  # three Hebrew letters, strong R, logical order aleph/bet/gimel
ARB = "عربي"  # four Arabic letters, strong AL (become R via W3)


def _levels(text, policy=RtlPolicy.INFER):
    return [p._level for p in vibidi(text, policy).logical_positions]


def _rtl(text, policy=RtlPolicy.INFER):
    return [p.is_rtl for p in vibidi(text, policy).logical_positions]


def _visual(text, policy=RtlPolicy.INFER, start=0, end=None):
    vt = vibidi(text, policy)
    return [p.logical for p in vt.reorder(start, len(text) if end is None else end)]


def _standard_levels(text, policy=RtlPolicy.INFER):
    return [
        None if p._removed else p._level for p in vibidi(text, policy).logical_positions
    ]


# --- base direction (P2/P3 + policy) ---------------------------------------


def test_base_inferred_from_first_strong():
    assert vibidi("abc").base_is_rtl is False
    assert vibidi(HEB).base_is_rtl is True
    # leading numbers / neutrals are not strong; the Hebrew letter decides
    assert vibidi("12, " + HEB).base_is_rtl is True


def test_policy_overrides_inference():
    assert vibidi("abc", RtlPolicy.RIGHT_TO_LEFT).base_is_rtl is True
    assert vibidi(HEB, RtlPolicy.LEFT_TO_RIGHT).base_is_rtl is False


# --- pure runs --------------------------------------------------------------


def test_ltr_is_identity():
    assert _levels("abc") == [0, 0, 0]
    assert _visual("abc") == [0, 1, 2]
    assert not any(_rtl("abc"))


def test_rtl_pure_reverses():
    assert _levels(HEB) == [1, 1, 1]
    assert _visual(HEB) == [2, 1, 0]
    assert all(_rtl(HEB))


def test_arabic_letters_resolve_to_rtl():  # W3: AL -> R
    assert _levels(ARB) == [1, 1, 1, 1]
    assert all(_rtl(ARB))


# --- mixed directions -------------------------------------------------------


def test_ltr_with_rtl_island():
    text = "abc " + HEB
    assert _levels(text) == [0, 0, 0, 0, 1, 1, 1]
    # the Hebrew run is reversed in place; the latin part stays put
    assert _visual(text) == [0, 1, 2, 3, 6, 5, 4]


def test_rtl_with_ltr_island():
    text = HEB + " abc"
    # base RTL; "abc" is an LTR island raised to level 2
    assert _levels(text) == [1, 1, 1, 1, 2, 2, 2]
    # visual: latin reads L->R on the left, Hebrew R->L on the right
    assert _visual(text) == [4, 5, 6, 3, 2, 1, 0]


# --- numbers (W2, W7, I) ----------------------------------------------------


def test_european_number_after_latin_stays_ltr():  # W7: EN -> L after L
    assert _levels("abc123") == [0, 0, 0, 0, 0, 0]
    assert _visual("abc123") == [0, 1, 2, 3, 4, 5]


def test_european_number_in_rtl_raises_two_levels():  # I2 on EN
    text = HEB + " 123"
    assert _levels(text) == [1, 1, 1, 1, 2, 2, 2]


def test_arabic_number_becomes_arabic():  # W2: EN -> AN after AL
    text = ARB[0] + "1"  # one Arabic letter then a European digit
    # AL->R (W3), EN->AN (W2); base RTL: R at level 1, AN at level 2
    assert _levels(text) == [1, 2]


# --- NSM (W1) ---------------------------------------------------------------


def test_nsm_inherits_previous_direction():
    text = "אְ"  # Hebrew aleph + sheva (a non-spacing mark)
    assert _levels(text) == [1, 1]
    assert all(_rtl(text))


# --- boundary neutrals removed by X9 ---------------------------------------


def test_join_controls_inherit_their_shaping_run_level():
    assert _levels("a\u200db") == [0, 0, 0]
    assert _levels("\u0646\u200c\u0645") == [1, 1, 1]
    assert _levels("\u200d\u0646") == [1, 1]


# --- explicit formatting and isolates (X1-X10) -----------------------------


def test_explicit_rtl_embedding_changes_levels_and_is_removed_by_x9():
    text = "a\u202b\u05d0\u05d1\u05d2\u202cb"

    assert _standard_levels(text) == [0, None, 1, 1, 1, None, 0]
    assert _visual(text) == [0, 4, 3, 2, 6]


def test_rtl_override_forces_latin_letters_to_reverse():
    text = "a\u202eabc\u202cz"

    assert _standard_levels(text) == [0, None, 1, 1, 1, None, 0]
    assert _visual(text) == [0, 4, 3, 2, 6]


def test_fsi_uses_its_contents_but_paragraph_inference_skips_them():
    text = "\u2068\u05d0\u05d1\u2069a"
    vt = vibidi(text)

    assert vt.base_is_rtl is False
    assert [p._level for p in vt.logical_positions] == [0, 1, 1, 0, 0]
    assert [p.logical for p in vt.reorder(0, len(text))] == [0, 2, 1, 3, 4]


def test_renderer_reorder_can_retain_x9_source_anchors():
    text = "a\u202b\u05d0\u05d1\u05d2\u202cb"
    vt = vibidi(text)

    assert [p.logical for p in vt.reorder_retaining_controls(0, len(text))] == [
        0,
        1,
        5,
        4,
        3,
        2,
        6,
    ]


# --- N0 paired brackets (the python-bidi gap / the bracket bug) -------------


def test_brackets_in_ltr_stay_ltr():
    text = "a[b]c"
    assert _levels(text) == [0, 0, 0, 0, 0]
    assert not any(_rtl(text))


def test_brackets_in_rtl_share_one_direction():
    # The bug: without N0 the two brackets collapse onto one shape. With N0 they
    # resolve to the SAME direction, so HarfBuzz mirrors them consistently.
    text = "א[a]ב"  # Hebrew, '[', latin 'a', ']', Hebrew
    rtl = _rtl(text)
    assert rtl[1] == rtl[3]  # the two brackets agree
    assert rtl[1] is True  # and take the RTL embedding direction here
    assert rtl[2] is False  # while the latin island stays LTR


# --- reorder on a sub-interval (a wrapped display line) ---------------------


def test_reorder_handles_partial_intervals():
    text = "abc " + HEB  # logical indices 0..6
    assert _visual(text, start=4, end=7) == [6, 5, 4]  # the Hebrew slice
    assert _visual(text, start=0, end=3) == [0, 1, 2]  # the latin slice


def test_visual_field_is_the_sequence_position():
    out = vibidi("abc " + HEB).reorder(0, 7)
    assert [p.visual for p in out] == list(range(len(out)))
    # and `logical` lets us map every visual slot back to a source index
    assert sorted(p.logical for p in out) == list(range(7))


def test_empty_text():
    vt = vibidi("")
    assert vt.logical_positions == ()
    assert list(vt.reorder(0, 0)) == []


# --- bundled data version guard --------------------------------------------


def test_bidibrackets_file_matches_unicodedata_version():
    """The bundled bracket table must track `unicodedataplus`: a dependency
    upgrade that bumps the bundled UCD should fail here until BidiBrackets.txt is
    refreshed."""
    header = _BRACKETS_FILE.read_text(encoding="utf-8").splitlines()[0]
    version = header.split("-", 1)[1].rsplit(".txt", 1)[0].strip()
    assert version == unicode_props.UNICODE_VERSION
