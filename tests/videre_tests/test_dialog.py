import filedial
import pytest

import videre


def test_dialog_has_methods():
    """Test that Dialog class has the expected methods"""
    dialog = videre.Dialog()

    assert hasattr(dialog, "select_directory")
    assert hasattr(dialog, "select_file_to_open")
    assert hasattr(dialog, "select_many_files")
    assert hasattr(dialog, "select_file_to_save")


def test_dialog_methods_are_references():
    """Test that Dialog methods are proper references to tk_utils functions"""
    assert videre.Dialog.select_directory is filedial.select_directory
    assert videre.Dialog.select_file_to_open is filedial.select_file_to_open
    assert videre.Dialog.select_file_to_save is filedial.select_file_to_save
    # Except this function
    assert videre.Dialog.select_many_files is not filedial.select_many_files_to_open


# `Dialog.select_many_files` wraps `filedial.select_many_files_to_open`
# to normalize its return shape: the underlying API may yield a tuple
# (multi-select), a non-empty string (single-select fallback), or an
# empty string (cancel). The wrapper unifies all three to a tuple.


def test_select_many_files_passes_through_tuple(monkeypatch: pytest.MonkeyPatch):
    """Tuple return is passed through unchanged."""
    monkeypatch.setattr(
        filedial, "select_many_files_to_open", lambda: ("a.txt", "b.txt")
    )
    assert videre.Dialog.select_many_files() == ("a.txt", "b.txt")


def test_select_many_files_wraps_single_string(monkeypatch: pytest.MonkeyPatch):
    """A non-empty string return becomes a 1-tuple."""
    monkeypatch.setattr(filedial, "select_many_files_to_open", lambda: "single.txt")
    assert videre.Dialog.select_many_files() == ("single.txt",)


def test_select_many_files_empty_string_returns_empty_tuple(
    monkeypatch: pytest.MonkeyPatch,
):
    """Cancel (empty string) yields an empty tuple, not `("",)`."""
    monkeypatch.setattr(filedial, "select_many_files_to_open", lambda: "")
    assert videre.Dialog.select_many_files() == ()
