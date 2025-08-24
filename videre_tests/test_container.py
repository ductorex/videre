import itertools

import pytest

import videre
from videre.core.sides.padding import Padding
from videre.testing.utils import LD
from videre.widgets.empty_widget import EmptyWidget


@pytest.mark.parametrize("border_size", [1, 2, 3])
def test_simple_container(border_size, fake_win):
    fake_win.controls = [
        videre.Container(
            videre.Text("Hello World!"), border=videre.Border.all(border_size)
        )
    ]
    fake_win.check()


@pytest.mark.win_params({"background": "purple", **LD})
def test_container_square(fake_win):
    fake_win.controls = [
        videre.Container(
            videre.Text("Hello, World!"),
            background_color="pink",
            border=videre.Border.all(2, videre.Colors.blue),
            square=True,
            vertical_alignment=videre.Alignment.START,
            horizontal_alignment=videre.Alignment.CENTER,
        )
    ]
    fake_win.check()


@pytest.mark.win_params({"background": "cyan", **LD})
@pytest.mark.parametrize("expand", [False, True], ids=("expand_false", "expand_true"))
def test_container_square_col_no_width(fake_win, expand):
    fake_win.controls = [
        videre.Column(
            [
                videre.Container(
                    videre.Text("Hello, World!"),
                    background_color="pink",
                    border=videre.Border.all(2, videre.Colors.blue),
                    square=True,
                    vertical_alignment=videre.Alignment.START,
                    horizontal_alignment=videre.Alignment.CENTER,
                ),
                videre.Text("Neighbor"),
            ],
            expand_horizontal=expand,
        )
    ]
    fake_win.check()


@pytest.mark.win_params({"background": "cyan", **LD})
@pytest.mark.parametrize("expand", [False, True], ids=("expand_false", "expand_true"))
def test_container_square_row_no_height(fake_win, expand):
    fake_win.controls = [
        videre.Row(
            [
                videre.Container(
                    videre.Text("Hello, World!"),
                    background_color="pink",
                    border=videre.Border.all(2, videre.Colors.blue),
                    square=True,
                    vertical_alignment=videre.Alignment.START,
                    horizontal_alignment=videre.Alignment.CENTER,
                ),
                videre.Text("Neighbor"),
            ],
            expand_vertical=expand,
        )
    ]
    fake_win.check()


@pytest.mark.parametrize(
    "halign,valign", itertools.product(videre.Alignment, videre.Alignment)
)
def test_container_alignments(fake_win, halign, valign):
    fake_win.controls = [
        videre.Container(
            videre.Text("Hello, World!"),
            background_color="pink",
            border=videre.Border.all(2, videre.Colors.blue),
            horizontal_alignment=halign,
            vertical_alignment=valign,
        )
    ]
    fake_win.check()


@pytest.mark.parametrize("padding", [0, 10, 50])
def test_container_padding(fake_win, padding):
    fake_win.controls = [
        videre.Container(
            videre.Text("Hello, World!"),
            background_color="pink",
            border=videre.Border.all(2, videre.Colors.blue),
            padding=Padding.axis(padding),
            vertical_alignment=videre.Alignment.START,
            horizontal_alignment=videre.Alignment.CENTER,
        )
    ]
    fake_win.check()


def test_container_too_big_borders(fake_win):
    fake_win.controls = [
        videre.Container(
            videre.Text("Hello, World!"),
            background_color="yellow",
            border=videre.Border(
                top=(100, videre.Colors.red),
                left=(50, (1, 255, 2)),
                bottom=(200, videre.Colors.cyan),
                right=25,
            ),
            padding=Padding(top=385, left=100, bottom=20),
            vertical_alignment=videre.Alignment.END,
            horizontal_alignment=videre.Alignment.CENTER,
        )
    ]
    fake_win.check()


def test_container_no_control(fake_win):
    # Test that a container with no control does not crash
    control = videre.Container()
    fake_win.controls = [control]
    fake_win.check()

    assert isinstance(control.control, EmptyWidget)


def test_container_control_change(fake_win):
    # Test changing the control of a container
    container = videre.Container(videre.Text("Initial"))
    fake_win.controls = [container]
    fake_win.check("initial")

    # Change the control to a new text
    container.control = videre.Text("Changed")
    fake_win.render()
    fake_win.check("changed")

    # Change back to the initial text
    container.control = videre.Text("Initial")
    fake_win.render()
    fake_win.check("initial")
