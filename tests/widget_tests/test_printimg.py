from pathlib import Path

from videre.layouts.scroll.scrollview import ScrollView
from videre.testing.utils import IMAGE_EXAMPLE
from videre.tools import _build_image_window
from videre.widgets.picture import Picture
from videre.windowing.window import Window


def test_printimg_with_string_path():
    window = _build_image_window(IMAGE_EXAMPLE)
    assert isinstance(window, Window)
    assert window.title == IMAGE_EXAMPLE
    (scroll,) = window.controls
    assert isinstance(scroll, ScrollView)
    assert isinstance(scroll.control, Picture)


def test_printimg_with_pathlib_path():
    path = Path(IMAGE_EXAMPLE)
    window = _build_image_window(path)
    assert window.title == str(path)
    (scroll,) = window.controls
    assert isinstance(scroll, ScrollView)
    assert isinstance(scroll.control, Picture)


def test_printimg_with_non_path_source():
    window = _build_image_window(IMAGE_EXAMPLE)
    # IMAGE_EXAMPLE is a string path, so title is the path itself
    assert window.title == IMAGE_EXAMPLE

    # Test with a non-path source (integer as a placeholder)
    # This tests the else branch: title = "image"

    w = _build_image_window(None)  # ty: ignore[invalid-argument-type]
    assert w.title == "image"


def test_printimg_title_generation():
    # String path -> title is the path
    w1 = _build_image_window("/test/path.png")
    assert w1.title == "/test/path.png"

    # Path object -> title is str(path)
    path = Path("/test/path.jpg")
    w2 = _build_image_window(path)
    assert w2.title == str(path)

    # Non-path source -> title is "image"
    w3 = _build_image_window(IMAGE_EXAMPLE)
    assert w3.title == IMAGE_EXAMPLE
