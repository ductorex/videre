import pytest

from videre import Colors, Container, Gradient


@pytest.mark.parametrize("vertical", [False, True])
def test_gradient(vertical, fake_win):
    fake_win.controls = [
        Container(
            background_color=Gradient(
                Colors.red, Colors.green, Colors.blue, vertical=vertical
            )
        )
    ]
    fake_win.check()


def test_background(fake_win):
    fake_win.controls = [Container(background_color="yellow")]
    fake_win.check()
