import contextlib
from unittest.mock import patch

import videre
from videre.core.pygame_backend.backend import PygameRenderer
from videre.testing.step_window import StepWindow


@contextlib.contextmanager
def _count_screen_paints():
    """Count how many times the *screen* (root) is actually repainted.

    `render_drawer` owns the frame skip: it is called every frame but
    early-returns when the root drawer is unchanged (same identity). We count
    only the calls that get past that skip — the frames that truly repaint.
    """
    real = PygameRenderer.render_drawer
    counter = {"screen": 0}

    def counting(self, drawer):
        if drawer is not self._last_drawer:  # not skipped -> a real repaint
            counter["screen"] += 1
        return real(self, drawer)

    with patch.object(PygameRenderer, "render_drawer", counting):
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


def test_resize_reflows_to_new_window_size():
    with StepWindow(width=640, height=480) as win:
        win.controls = [videre.Text("hello")]
        win.render()
        assert win._layout.render(win, win.width, win.height).get_width() == 640

        # A different-size resize must rebuild the root drawer at the new size,
        # so the content reflows to fill the window (regression guard: passing no
        # size to `render` once froze this at the initial size).
        win.user.resize(800, 600)
        win.render()
        root = win._layout.render(win, win.width, win.height)
        assert (root.get_width(), root.get_height()) == (800, 600)
