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
    import filedial

    assert videre.Dialog.select_directory is filedial.select_directory
    assert videre.Dialog.select_file_to_open is filedial.select_file_to_open
    assert videre.Dialog.select_file_to_save is filedial.select_file_to_save
    # Except this function
    assert videre.Dialog.select_many_files is not filedial.select_many_files_to_open
