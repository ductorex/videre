from unittest.mock import patch

from tests.common import TrackerWidget

# --- Default mouse over (synthetic MOUSEMOTION) ---


def test_window_default_mouse_over_no(fake_win):
    """In headless mode, get_focused() returns False: no synthetic mouse motion."""
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()
    assert fake_win._event_manager._motion is None


def test_window_default_mouse_over(fake_win):
    """When get_focused() returns True, a synthetic MOUSEMOTION is created."""
    tracker = TrackerWidget()
    fake_win.controls = [tracker]
    fake_win.render()

    with patch("pygame.mouse.get_focused", return_value=True):
        fake_win.render()

    assert fake_win._event_manager._motion is tracker
