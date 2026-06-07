"""Tests for StepWindow error paths."""

import pytest

from videre.testing.step_window import StepWindow


def test_run_raises_in_step_mode():
    with StepWindow() as win:
        with pytest.raises(RuntimeError, match=r"Cannot run\(\) on a step window"):
            win.run()


def test_render_outside_step_mode():
    win = StepWindow()
    with pytest.raises(RuntimeError, match="step-mode"):
        win.render()


def test_screenshot_outside_step_mode():
    win = StepWindow()
    with pytest.raises(RuntimeError, match="step-mode"):
        win.screenshot()


def test_enter_after_close():
    win = StepWindow()

    with win:
        pass

    with pytest.raises(RuntimeError, match="already run"):
        with win:
            pass
