"""Scaled rendering end-to-end, via the real dpi_aware path (platform plumbing
monkeypatched): the window is logical 320×240, the screen and snapshot are
device-sized. Text rasterizes at native glyph size (device pixels, never
resampled); every other Drawer command — borders, paddings, spacing,
backgrounds — is scaled by the renderer at paint time. Widget code and wprops
stay logical: these scenes are written exactly like 100% ones.

Two scales on purpose: ×2 (every logical pixel maps to a whole device pixel)
and ×1.5 (fractional: edge scaling, flush anchoring and stroke thickening all
actually round something). Note ×1.5 does NOT separate half-up from ceil — on
integer sizes their fracs are 0 or .5, where both round up. The scales that
do (frac .25: ×1.25, ×1.75) are covered by the crop/blit matrix
(test_drawer_crop) and the window-size test (test_dpi), which compare
renders to each other instead of to a stored snapshot — a snapshot per
exotic scale would be maintenance without extra detection power.
"""

import pytest

import videre
import videre.core.pygame_backend.backend as pygame_backend


@pytest.fixture
def forced_scale_2x(monkeypatch):
    monkeypatch.setattr(pygame_backend, "declare_dpi_awareness", lambda: True)
    monkeypatch.setattr(pygame_backend, "system_scale_factor", lambda: 2.0)


@pytest.fixture
def forced_scale_1_5x(monkeypatch):
    monkeypatch.setattr(pygame_backend, "declare_dpi_awareness", lambda: True)
    monkeypatch.setattr(pygame_backend, "system_scale_factor", lambda: 1.5)


def _text_scene(fake_win):
    fake_win.controls = [videre.Text("Hello DPI 123")]
    fake_win.check()


def _chrome_scene(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Button("Click me"),
                videre.Container(
                    videre.Text("Boxed"),
                    border=videre.Border.all(2, videre.Colors.blue),
                    padding=videre.Padding.all(6),
                    width=120,
                    background_color=videre.Colors.yellow,
                ),
            ],
            space=4,
            expand_horizontal=False,
        )
    ]
    fake_win.check()


def _textinput_scene(fake_win):
    # Exercises the text facade round-trip: the click lands in logical
    # coordinates, the hit-test runs on device glyphs behind the facade, and
    # the caret paints back at the right logical spot on the device screen.
    ti = videre.TextInput(text="Hello DPI")
    fake_win.controls = [ti]
    fake_win.render()
    fake_win.user.click_at(ti.global_x, ti.global_y)
    fake_win.check()


@pytest.mark.win_params(dict(dpi_aware=True))
def test_text_scale_factor_2x(forced_scale_2x, fake_win):
    _text_scene(fake_win)


@pytest.mark.win_params(dict(dpi_aware=True))
def test_chrome_scale_factor_2x(forced_scale_2x, fake_win):
    _chrome_scene(fake_win)


@pytest.mark.win_params(dict(dpi_aware=True))
def test_textinput_scale_factor_2x(forced_scale_2x, fake_win):
    _textinput_scene(fake_win)


@pytest.mark.win_params(dict(dpi_aware=True))
def test_text_scale_factor_1_5x(forced_scale_1_5x, fake_win):
    _text_scene(fake_win)


@pytest.mark.win_params(dict(dpi_aware=True))
def test_chrome_scale_factor_1_5x(forced_scale_1_5x, fake_win):
    _chrome_scene(fake_win)


@pytest.mark.win_params(dict(dpi_aware=True))
def test_textinput_scale_factor_1_5x(forced_scale_1_5x, fake_win):
    _textinput_scene(fake_win)
