from unittest.mock import MagicMock, patch

from videre.core.clipboard import Clipboard


@patch("videre.core.clipboard.pyperclip.paste")
def test_get_clipboard_success(mock_paste):
    """Test successful clipboard retrieval"""
    mock_paste.return_value = "test clipboard content"

    result = Clipboard.get_clipboard()

    assert result == "test clipboard content"
    mock_paste.assert_called_once()


@patch("videre.core.clipboard.pyperclip.paste")
def test_get_clipboard_failure(mock_paste):
    """Test clipboard retrieval failure"""
    mock_paste.side_effect = Exception("Clipboard error")

    result = Clipboard.get_clipboard()

    assert result == ""
    mock_paste.assert_called_once()


@patch("videre.core.clipboard.pyperclip.copy")
def test_set_clipboard_success(mock_copy):
    """Test successful clipboard setting"""
    text = "text to copy"

    Clipboard.set_clipboard(text)

    mock_copy.assert_called_once_with(text)


@patch("videre.core.clipboard.pyperclip.copy")
def test_set_clipboard_failure(mock_copy):
    """Test clipboard setting failure"""
    mock_copy.side_effect = Exception("Copy error")

    # Should not raise exception
    Clipboard.set_clipboard("test text")

    mock_copy.assert_called_once_with("test text")


def test_clipboard_class_structure():
    """Test that Clipboard class has the expected structure"""
    clipboard = Clipboard()

    assert hasattr(clipboard, "get_clipboard")
    assert hasattr(clipboard, "set_clipboard")
    assert callable(clipboard.get_clipboard)
    assert callable(clipboard.set_clipboard)


@patch("videre.core.clipboard.pyperclip")
def test_clipboard_integration(mock_pyperclip):
    """Test clipboard get/set integration"""
    mock_pyperclip.paste.return_value = "initial content"
    mock_pyperclip.copy = MagicMock()

    # Get initial content
    content = Clipboard.get_clipboard()
    assert content == "initial content"

    # Set new content
    new_content = "new clipboard content"
    Clipboard.set_clipboard(new_content)

    # Verify copy was called
    mock_pyperclip.copy.assert_called_once_with(new_content)


def test_clipboard_empty_string():
    """Test clipboard operations with empty string"""
    with patch("videre.core.clipboard.pyperclip.paste") as mock_paste:
        mock_paste.return_value = ""
        result = Clipboard.get_clipboard()
        assert result == ""

    with patch("videre.core.clipboard.pyperclip.copy") as mock_copy:
        Clipboard.set_clipboard("")
        mock_copy.assert_called_once_with("")


def test_clipboard_unicode_content():
    """Test clipboard operations with unicode content"""
    unicode_text = "Hello 世界! 🌍 Ñañá"

    with patch("videre.core.clipboard.pyperclip.paste") as mock_paste:
        mock_paste.return_value = unicode_text
        result = Clipboard.get_clipboard()
        assert result == unicode_text

    with patch("videre.core.clipboard.pyperclip.copy") as mock_copy:
        Clipboard.set_clipboard(unicode_text)
        mock_copy.assert_called_once_with(unicode_text)
