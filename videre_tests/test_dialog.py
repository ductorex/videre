from unittest.mock import patch

import videre


def test_dialog_has_methods():
    """Test that Dialog class has the expected methods"""
    dialog = videre.Dialog()

    assert hasattr(dialog, "select_directory")
    assert hasattr(dialog, "select_file_to_open")
    assert hasattr(dialog, "select_many_files")
    assert hasattr(dialog, "select_file_to_save")


@patch("videre.Dialog.select_directory")
def test_dialog_select_directory(mock_select_directory):
    """Test directory selection dialog"""
    mock_select_directory.return_value = "/test/directory"

    result = videre.Dialog.select_directory()

    assert result == "/test/directory"
    mock_select_directory.assert_called_once()


@patch("videre.Dialog.select_file_to_open")
def test_dialog_select_file_to_open(mock_select_file):
    """Test file open dialog"""
    mock_select_file.return_value = "/test/file.txt"

    result = videre.Dialog.select_file_to_open()

    assert result == "/test/file.txt"
    mock_select_file.assert_called_once()


@patch("videre.Dialog.select_many_files")
def test_dialog_select_many_files(mock_select_files):
    """Test multiple files selection dialog"""
    mock_select_files.return_value = ["/test/file1.txt", "/test/file2.txt"]

    result = videre.Dialog.select_many_files()

    assert result == ["/test/file1.txt", "/test/file2.txt"]
    mock_select_files.assert_called_once()


@patch("videre.Dialog.select_file_to_save")
def test_dialog_select_file_to_save(mock_select_file):
    """Test file save dialog"""
    mock_select_file.return_value = "/test/save_file.txt"

    result = videre.Dialog.select_file_to_save()

    assert result == "/test/save_file.txt"
    mock_select_file.assert_called_once()


def test_dialog_methods_are_references():
    """Test that Dialog methods are proper references to tk_utils functions"""
    import filedial

    assert videre.Dialog.select_directory is filedial.select_directory
    assert videre.Dialog.select_file_to_open is filedial.select_file_to_open
    assert videre.Dialog.select_many_files is filedial.select_many_files_to_open
    assert videre.Dialog.select_file_to_save is filedial.select_file_to_save
