import contextlib
from unittest.mock import patch

import videre
from videre.core.pygame_backend.backend import Pygame
from videre.testing.step_window import StepWindow


@contextlib.contextmanager
def _count_screen_paints():
    """Count how many times the *screen* (root, `dst is not None`) is painted.

    Sub-drawers go through `_paint_drawer(..., dst=None)` and are not counted:
    only the root repaint that `Window._refresh` triggers is.
    """
    real = Pygame._paint_drawer
    counter = {"screen": 0}

    def counting(self, drawer, dst):
        if dst is not None:
            counter["screen"] += 1
        return real(self, drawer, dst)

    with patch.object(Pygame, "_paint_drawer", counting):
        yield counter


def test_unchanged_screen_is_not_repainted():
    with _count_screen_paints() as paints, StepWindow() as win:
        win.controls = [videre.Text("hello")]

        win.render()
        assert paints["screen"] == 1  # first frame: painted
        before = win.screenshot().getvalue()

        win.render()
        assert paints["screen"] == 1  # nothing changed: skipped
        win.render()
        assert paints["screen"] == 1  # still skipped

        # The persistent buffer kept the image intact across the skipped frames.
        assert win.screenshot().getvalue() == before


def test_widget_change_repaints_screen():
    with _count_screen_paints() as paints, StepWindow() as win:
        text = videre.Text("hello")
        win.controls = [text]

        win.render()
        assert paints["screen"] == 1
        win.render()
        assert paints["screen"] == 1  # skipped

        text.text = "world"
        win.render()
        assert paints["screen"] == 2  # change picked up -> repainted


def test_same_size_buffer_swap_repaints_screen():
    with _count_screen_paints() as paints, StepWindow() as win:
        win.controls = [videre.Text("hello")]

        win.render()
        assert paints["screen"] == 1
        win.render()
        assert paints["screen"] == 1  # skipped

        # Recreate the screen buffer at the same size: the drawer keeps its
        # identity (tree still clean) but the buffer is new, so we must repaint.
        win.user.resize(win.width, win.height)
        win.render()
        assert paints["screen"] == 2
