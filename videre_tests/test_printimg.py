from pathlib import Path
from unittest.mock import MagicMock, patch

from videre.tools import printimg


@patch("videre.tools.Window")
@patch("videre.tools.ScrollView")
@patch("videre.tools.Picture")
def test_printimg_with_string_path(mock_picture, mock_scrollview, mock_window):
    """Test printimg with string path"""
    mock_window_instance = MagicMock()
    mock_scrollview_instance = MagicMock()
    mock_picture_instance = MagicMock()

    mock_window.return_value = mock_window_instance
    mock_scrollview.return_value = mock_scrollview_instance
    mock_picture.return_value = mock_picture_instance

    image_path = "/test/image.png"

    printimg(image_path)

    # Verify components were created correctly
    mock_picture.assert_called_once_with(image_path)
    mock_scrollview.assert_called_once_with(mock_picture_instance)
    mock_window.assert_called_once_with(title=image_path)

    # Verify window was configured and run
    assert mock_window_instance.controls == [mock_scrollview_instance]
    mock_window_instance.run.assert_called_once()


@patch("videre.tools.Window")
@patch("videre.tools.ScrollView")
@patch("videre.tools.Picture")
def test_printimg_with_pathlib_path(mock_picture, mock_scrollview, mock_window):
    """Test printimg with pathlib Path"""
    mock_window_instance = MagicMock()
    mock_scrollview_instance = MagicMock()
    mock_picture_instance = MagicMock()

    mock_window.return_value = mock_window_instance
    mock_scrollview.return_value = mock_scrollview_instance
    mock_picture.return_value = mock_picture_instance

    image_path = Path("/test/image.jpg")

    printimg(image_path)

    # Verify components were created correctly
    mock_picture.assert_called_once_with(image_path)
    mock_scrollview.assert_called_once_with(mock_picture_instance)
    mock_window.assert_called_once_with(title=str(image_path))

    # Verify window was configured and run
    assert mock_window_instance.controls == [mock_scrollview_instance]
    mock_window_instance.run.assert_called_once()


@patch("videre.tools.Window")
@patch("videre.tools.ScrollView")
@patch("videre.tools.Picture")
def test_printimg_with_non_path_source(mock_picture, mock_scrollview, mock_window):
    """Test printimg with non-path source (like PIL Image or other object)"""
    mock_window_instance = MagicMock()
    mock_scrollview_instance = MagicMock()
    mock_picture_instance = MagicMock()

    mock_window.return_value = mock_window_instance
    mock_scrollview.return_value = mock_scrollview_instance
    mock_picture.return_value = mock_picture_instance

    # Could be PIL Image, numpy array, or other ImageSourceType
    image_source = MagicMock()

    printimg(image_source)

    # Verify components were created correctly
    mock_picture.assert_called_once_with(image_source)
    mock_scrollview.assert_called_once_with(mock_picture_instance)
    mock_window.assert_called_once_with(title="image")

    # Verify window was configured and run
    assert mock_window_instance.controls == [mock_scrollview_instance]
    mock_window_instance.run.assert_called_once()


def test_printimg_title_generation():
    """Test title generation logic for different input types"""
    with patch("videre.tools.Window") as mock_window:
        with patch("videre.tools.ScrollView"):
            with patch("videre.tools.Picture"):
                mock_window_instance = MagicMock()
                mock_window.return_value = mock_window_instance

                # Test string path
                printimg("/test/path.png")
                mock_window.assert_called_with(title="/test/path.png")

                # Test Path object
                path = Path("/test/path.jpg")
                printimg(path)
                mock_window.assert_called_with(title=str(path))

                # Test other object type
                printimg(MagicMock())
                mock_window.assert_called_with(title="image")
