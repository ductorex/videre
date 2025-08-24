from types import SimpleNamespace

import pytest

import videre
from videre.core.constants import Alignment
from videre.core.sides.border import Border
from videre.core.sides.padding import Padding
from videre.layouts.div import Style, StyleDef


def test_div_simple(snap_win):
    text = videre.Text("Hello Div!")
    div = videre.Div(text)
    snap_win.controls = [div]


def test_div_with_style(snap_win):
    text = videre.Text("Styled Div")
    div = videre.Div(
        text,
        style=StyleDef(
            default=Style(
                background_color=videre.Colors.lightblue,
                padding=Padding.all(0),
                border=Border.all(2, videre.Colors.darkblue),
            )
        ),
    )
    snap_win.controls = [div]


def test_div_click_handler(fake_win, fake_user):
    data = SimpleNamespace(clicked=False, div_ref=None)

    def on_click(div):
        data.clicked = True
        data.div_ref = div

    text = videre.Text("Clickable Div")
    div = videre.Div(text, on_click=on_click)
    fake_win.controls = [div]
    fake_win.render()

    assert data.clicked is False

    fake_user.click(div)
    fake_win.render()

    assert data.clicked is True
    assert data.div_ref is div


def test_div_hover_style(fake_win, fake_user):
    text = videre.Text("Hover Div")
    div = videre.Div(
        text,
        style=StyleDef(
            default=Style(background_color=videre.Colors.white),
            hover=Style(background_color=videre.Colors.lightgray),
        ),
    )
    fake_win.controls = [div]
    fake_win.check("default")

    # Simulate mouse hover
    fake_user.mouve_over(div)

    fake_win.check("hover")

    # Test that hover styling exists
    assert div._style.hover is not None
    assert div._style.hover.background_color == videre.Colors.lightgray


def test_div_alignment(snap_win):
    text = videre.Text("Aligned")
    div = videre.Div(
        text,
        style=StyleDef(
            default=Style(
                width=200,
                height=100,
                horizontal_alignment=Alignment.END,
                vertical_alignment=Alignment.END,
                border=Border.all(1, videre.Colors.black),
            )
        ),
    )
    snap_win.controls = [div]


def test_div_no_click_handler(fake_win, fake_user):
    text = videre.Text("No Handler")
    div = videre.Div(text)
    fake_win.controls = [div]
    fake_win.render()

    # Should not crash without click handler
    fake_user.click(div)
    fake_win.render()


def test_div_invalid_style():
    control = videre.Text("Hello")
    with pytest.raises(TypeError, match="Invalid style type: str"):
        videre.Div(control, style="invalid_style")


def test_style_fill_with():
    style1 = Style(width=100, height=None)
    style2 = Style(width=200, height=50, background_color=videre.Colors.red)

    assert style1.width == 100
    assert style1.height is None
    assert style1.background_color is None
    style1.fill_with(style2)
    assert style1.width == 100  # Should keep original value
    assert style1.height == 50  # Should take from other
    assert style1.background_color == videre.Colors.red  # Should take from other


def test_style_get_specific_from():
    base_style = Style(width=100, height=50, background_color=videre.Colors.white)
    specific_style = Style(width=200, height=50, background_color=videre.Colors.red)

    diff = specific_style.get_specific_from(base_style)

    assert diff.width == 200
    assert diff.height is None  # Same as base, so not included
    assert diff.background_color == videre.Colors.red
