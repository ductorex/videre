import itertools

import pytest

import videre
from videre.testing.utils import LOREM_IPSUM, SD

NB_LINES = (0, 1, 2)
WRAP = list(videre.TextWrap)
ALIGN = list(videre.TextAlign)


@pytest.mark.parametrize("nb_lines,wrap", itertools.product(NB_LINES, WRAP))
@pytest.mark.win_params({"background": videre.Colors.yellow, **SD})
def test_text(nb_lines, wrap, fake_win):
    lorem_ipsum = ("\n" * nb_lines) + LOREM_IPSUM
    fake_win.controls = [videre.Text(lorem_ipsum, wrap=wrap)]
    fake_win.check()


@pytest.mark.parametrize(
    "align,wrap",
    itertools.product([al for al in ALIGN if al != videre.TextAlign.NONE], WRAP),
)
@pytest.mark.win_params({"background": videre.Colors.yellow, **SD})
def test_text_wrap(align, wrap, fake_win):
    fake_win.controls = [videre.Text(LOREM_IPSUM, wrap=wrap, align=align)]
    fake_win.check()


@pytest.mark.win_params({"background": videre.Colors.gray, **SD})
def test_text_color(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Text("hello"),
                videre.Text("world", color="red"),
                videre.Text("how Are you?", size=30, color="#ffeeaa"),
                videre.Text("hello world", color="cyan"),
            ]
        )
    ]
    fake_win.check()


@pytest.mark.win_params(SD)
def test_text_strong(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Text("hello world 1.", size=30),
                videre.Text("hello world 2.", size=30, strong=True),
                videre.Text("hello world 3.", size=30),
            ]
        )
    ]
    fake_win.check()


@pytest.mark.win_params(SD)
def test_text_italic(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Text("hello world 1.", size=30),
                videre.Text("hello world 2.", size=30, italic=True),
                videre.Text("hello world 3.", size=30),
            ]
        )
    ]
    fake_win.check()


@pytest.mark.win_params(SD)
def test_text_underline(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Text("hello world 1_.", size=30),
                videre.Text("hello world 2_.", size=30, underline=True),
                videre.Text("hello world 3_.", size=30),
            ]
        )
    ]
    fake_win.check()


@pytest.mark.win_params(SD)
def test_text_underline_colored(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Text("hello world 1_.", size=30),
                videre.Text("hello world 2_.", size=30, underline=True, color="red"),
                videre.Text("hello world 3_.", size=30),
            ]
        )
    ]
    fake_win.check()


@pytest.mark.win_params(SD)
def test_text_styles(fake_win):
    fake_win.controls = [
        videre.Column(
            [
                videre.Text("hello world 1_.", size=30),
                videre.Text(
                    "hello world 2_. How are you ? I hope you are fine ! "
                    "Thanks ! And you ?",
                    size=30,
                    strong=True,
                    italic=True,
                    underline=True,
                ),
                videre.Text(
                    "hello world 2_. How are you ? I hope you are fine ! "
                    "Thanks ! And you ?",
                    size=30,
                    strong=True,
                    italic=True,
                    underline=True,
                    wrap=videre.TextWrap.CHAR,
                ),
                videre.Text(
                    "hello world 2_. How are you ? I hope you are fine ! "
                    "Thanks ! And you ?",
                    size=30,
                    strong=True,
                    italic=True,
                    underline=True,
                    wrap=videre.TextWrap.WORD,
                ),
                videre.Text("hello world 3_.", size=30),
            ]
        )
    ]
    fake_win.check()


def test_text_wrap_spaces(fake_win):
    """
    Test that text rendering is the same when wrapping None, characters and words,
    as long as there are no multiple spaces and no line breaks.
    """
    text = videre.Text("Hello World, how are you?\n\n\nI am fine, thanks!")
    fake_win.controls = [text]
    fake_win.check()
    text.wrap = videre.TextWrap.CHAR
    fake_win.check()
    text.wrap = videre.TextWrap.WORD
    fake_win.check()
