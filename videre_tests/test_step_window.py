"""Tests for StepWindow error paths."""

import pytest

from videre.testing.step_window import StepWindow


def test_run_raises_in_step_mode():
    with StepWindow() as win:
        with pytest.raises(RuntimeError, match="step mode"):
            win.run()


def test_render_outside_step_mode():
    win = StepWindow()
    with pytest.raises(RuntimeError, match="step-mode"):
        win.render()


def test_screenshot_outside_step_mode():
    win = StepWindow()
    with pytest.raises(RuntimeError, match="step-mode"):
        win.screenshot()


def test_enter_after_run(fake_user):
    import threading
    import time

    win = StepWindow()

    def stop():
        time.sleep(0.3)
        fake_user.quit()

    t = threading.Thread(target=stop)
    t.start()
    win.run()
    t.join()

    with pytest.raises(RuntimeError, match="already run"):
        win.__enter__()
