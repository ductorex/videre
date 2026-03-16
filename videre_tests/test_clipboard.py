import pyperclip
import pytest

from videre.core.clipboard import Clipboard


@pytest.fixture(autouse=True)
def _restore_clipboard_backend():
    """Restore real pyperclip backend after each test."""
    original_copy = Clipboard._copy
    original_paste = Clipboard._paste
    yield
    Clipboard._copy = original_copy
    Clipboard._paste = original_paste


def test_get_clipboard_success():
    Clipboard._paste = staticmethod(lambda: "test clipboard content")
    assert Clipboard.get_clipboard() == "test clipboard content"


def test_get_clipboard_failure():
    def failing_paste():
        raise Exception("Clipboard error")

    Clipboard._paste = staticmethod(failing_paste)
    assert Clipboard.get_clipboard() == ""


def test_set_clipboard_success():
    copied = []
    Clipboard._copy = staticmethod(lambda text: copied.append(text))
    Clipboard.set_clipboard("text to copy")
    assert copied == ["text to copy"]


def test_set_clipboard_failure():
    def failing_copy(text):
        raise Exception("Copy error")

    Clipboard._copy = staticmethod(failing_copy)
    # Should not raise
    Clipboard.set_clipboard("test text")


def test_clipboard_class_structure():
    clipboard = Clipboard()
    assert hasattr(clipboard, "get_clipboard")
    assert hasattr(clipboard, "set_clipboard")
    assert callable(clipboard.get_clipboard)
    assert callable(clipboard.set_clipboard)


def test_clipboard_integration():
    store = {"content": "initial content"}
    Clipboard._paste = staticmethod(lambda: store["content"])
    Clipboard._copy = staticmethod(lambda text: store.update(content=text))

    assert Clipboard.get_clipboard() == "initial content"
    Clipboard.set_clipboard("new clipboard content")
    assert Clipboard.get_clipboard() == "new clipboard content"


def test_clipboard_empty_string():
    Clipboard._paste = staticmethod(lambda: "")
    assert Clipboard.get_clipboard() == ""

    copied = []
    Clipboard._copy = staticmethod(lambda text: copied.append(text))
    Clipboard.set_clipboard("")
    assert copied == [""]


def test_clipboard_unicode_content():
    unicode_text = "Hello 世界! 🌍 Ñañá"

    Clipboard._paste = staticmethod(lambda: unicode_text)
    assert Clipboard.get_clipboard() == unicode_text

    copied = []
    Clipboard._copy = staticmethod(lambda text: copied.append(text))
    Clipboard.set_clipboard(unicode_text)
    assert copied == [unicode_text]


def test_clipboard_default_backend():
    assert Clipboard._copy is pyperclip.copy
    assert Clipboard._paste is pyperclip.paste
