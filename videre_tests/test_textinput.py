from unittest.mock import patch

import pygame.mouse
import pytest

import videre


def test_value(fake_win):
    ti = videre.TextInput()
    fake_win.controls = [ti]

    fake_win.check("value_empty")
    assert ti.value == ""

    ti.value = "test"
    fake_win.check("value_test")
    assert ti.value == "test"


def test_cursor(fake_win, fake_user):
    string = "Hello, world!"
    ti = videre.TextInput(text=string)
    placeholder = videre.Container(width=100, height=100)
    fake_win.controls = [videre.Column([ti, placeholder])]
    fake_win.check("cursor_none")

    # Click at text input start
    x = ti.global_x
    y = ti.global_y
    fake_user.click_at(x, y)
    fake_win.check("cursor_start")

    # Click out of text input
    fake_user.click(placeholder)
    fake_win.check("cursor_none")

    # Click at text input end
    x = ti.global_x + ti.rendered_width - 1
    fake_user.click_at(x, y)
    fake_win.check("cursor_end")

    # Click out of text input
    fake_user.click(placeholder)
    fake_win.check("cursor_none")


def test_cursor_move_by_keyboard(fake_win, fake_user):
    string = "Hello, world!"
    ti = videre.TextInput(text=string)
    placeholder = videre.Container(width=100, height=100)
    fake_win.controls = [
        videre.Container(
            videre.Column([ti, placeholder]),
            padding=videre.Padding.all(20),
            background_color=videre.Colors.red,
        )
    ]
    fake_win.check("cursor_none")
    assert ti._get_cursor() == len(string)

    # Click on ','
    # We have only 1 line, without wrap,
    # so line contains only 1 word embedding full string.
    word = ti._text._rendered.lines[0].elements[0]
    char = word.tasks[5]
    assert char.el == ","

    x = ti.global_x + word.x + char.x
    y = ti.global_y + 1
    fake_user.click_at(x, y)
    fake_win.check("cursor_5")
    assert ti._get_cursor() == 5

    fake_user.keyboard_entry("left")
    fake_win.check("cursor_4")
    assert ti._get_cursor() == 4

    fake_user.keyboard_entry("left")
    fake_win.check("cursor_3")
    assert ti._get_cursor() == 3

    fake_user.keyboard_entry("right")
    fake_win.check("cursor_4")
    assert ti._get_cursor() == 4

    fake_user.keyboard_entry("right")
    fake_win.check("cursor_5")
    assert ti._get_cursor() == 5

    fake_user.keyboard_entry("right")
    fake_win.check("cursor_6")
    assert ti._get_cursor() == 6

    fake_user.keyboard_entry("right")
    fake_win.check("cursor_7")
    assert ti._get_cursor() == 7

    fake_user.keyboard_entry("right", ctrl=True)
    fake_win.check("cursor_12")
    assert ti._get_cursor() == 12

    fake_user.keyboard_entry("right", ctrl=True)
    fake_win.check("cursor_13")
    assert ti._get_cursor() == 13

    fake_user.keyboard_entry("right", ctrl=True)
    fake_win.check("cursor_13")
    assert ti._get_cursor() == 13

    fake_user.keyboard_entry("right", ctrl=True)
    fake_win.check("cursor_13")
    assert ti._get_cursor() == 13

    fake_user.keyboard_entry("left", ctrl=True)
    fake_win.check("cursor_12")
    assert ti._get_cursor() == 12

    fake_user.keyboard_entry("left", ctrl=True)
    fake_win.check("cursor_7")
    assert ti._get_cursor() == 7

    fake_user.keyboard_entry("left", ctrl=True)
    fake_win.check("cursor_5")
    assert ti._get_cursor() == 5

    fake_user.keyboard_entry("left", ctrl=True)
    fake_win.check("cursor_0")
    assert ti._get_cursor() == 0

    fake_user.keyboard_entry("left", ctrl=True)
    fake_win.check("cursor_0")
    assert ti._get_cursor() == 0

    fake_user.keyboard_entry("left", ctrl=True)
    fake_win.check("cursor_0")
    assert ti._get_cursor() == 0


def test_cursor_mouse_on_empty(fake_win, fake_user):
    ti = videre.TextInput(text="", weight=1)
    placeholder = videre.Container(width=100, height=100, background_color="green")
    fake_win.controls = [
        videre.Container(
            videre.Column([ti, placeholder]),
            padding=videre.Padding.all(20),
            background_color=videre.Colors.red,
        )
    ]
    fake_win.check("cursor_none")
    assert ti._get_cursor() == 0
    assert ti._get_selection() is None

    fake_user.click(ti)
    fake_win.check("cursor_0")
    assert ti._get_cursor() == 0
    assert ti._get_selection() == (0, 0)


def test_cursor_move_by_mouse(fake_win, fake_user):
    string = "Hello, world!"
    ti = videre.TextInput(text=string)
    placeholder = videre.Container(width=100, height=100)
    fake_win.controls = [
        videre.Container(
            videre.Column([ti, placeholder]),
            padding=videre.Padding.all(20),
            background_color=videre.Colors.red,
        )
    ]
    fake_win.check("cursor_none")
    assert ti._get_cursor() == len(string)
    assert ti._get_selection() is None

    # Also check mouse cursor
    assert pygame.mouse.get_cursor() == fake_win._default_cursor

    # Get character elements in rendered text
    # We have only 1 line, without wrap,
    # so line contains only 1 word embedding full string.
    word = ti._text._rendered.lines[0].elements[0]
    h, e, l1, l2, o1, comma, space, w, o2, r, l3, d, exclamation = word.tasks
    assert comma.el == ","

    # Click
    x = ti.global_x + word.x + comma.x
    y = ti.global_y + 5
    fake_user.click_at(x, y)
    fake_win.check("cursor_5")
    assert ti._get_cursor() == 5
    # Even a click will trigger selection,
    # since "mouse down" event will set a new selection
    # ("mouse up" event does not cancel the selection)
    assert ti._get_selection() == (5, 5)

    # Another click
    x = ti.global_x + word.x + o1.x
    fake_user.click_at(x, y)
    fake_win.check("cursor_4")
    assert ti._get_cursor() == 4
    assert ti._get_selection() == (4, 4)

    # Mouse down
    fake_user.mouse_down(x, y)
    fake_win.check("cursor_4")
    assert ti._get_cursor() == 4
    assert ti._get_selection() == (4, 4)

    # Mouse down move left
    x = ti.global_x + word.x + l1.x
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_2")
    assert ti._get_cursor() == 2
    assert ti._get_selection() == (2, 4)

    # Check mouse cursor
    # Mouse motion should have triggered a mouse enter,
    # to cursor should have changed
    text_cursor = pygame.mouse.get_cursor()
    assert text_cursor != fake_win._default_cursor

    # Mouse down move left again
    x = ti.global_x + word.x + e.x
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_1")
    assert ti._get_cursor() == 1
    assert ti._get_selection() == (1, 4)

    # Mouse down move left
    x = ti.global_x + word.x + h.x
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_0")
    assert ti._get_cursor() == 0
    assert ti._get_selection() == (0, 4)

    # Mouse down right
    x = ti.global_x + word.x + space.x
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_6")
    assert ti._get_cursor() == 6
    assert ti._get_selection() == (4, 6)

    # Mouse down right again
    x = ti.global_x + word.x + word.width + 5
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_13")
    assert ti._get_cursor() == 13
    assert ti._get_selection() == (4, 13)

    # Mouse down left again to empty selection
    x = ti.global_x + word.x + o1.x
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_4")
    assert ti._get_cursor() == 4
    assert ti._get_selection() == (4, 4)

    # Mouse exit
    fake_user.mouse_motion(placeholder.global_x, placeholder.global_y)
    fake_win.check("cursor_4")
    # Check mouse cursor
    assert pygame.mouse.get_cursor() == fake_win._default_cursor


def test_keyboard_delete(fake_win, fake_user):
    string = "Hello, world!"
    ti = videre.TextInput(text=string)
    placeholder = videre.Container(width=100, height=100)
    fake_win.controls = [
        videre.Container(
            videre.Column([ti, placeholder]),
            padding=videre.Padding.all(20),
            background_color=videre.Colors.red,
        )
    ]
    fake_win.render()
    assert ti._get_cursor() == len(string)
    assert ti.value == string

    fake_user.click_at(ti.global_x + ti.rendered_width - 1, ti.global_y)
    fake_win.render()

    fake_user.keyboard_entry("delete")
    fake_win.render()
    assert ti.value == string
    fake_user.keyboard_entry("delete")
    fake_win.render()
    assert ti.value == string

    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("delete")
    fake_win.render()
    assert ti.value == "Hello, world"

    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("delete")
    fake_win.render()
    assert ti.value == "Hello, wold"

    fake_user.keyboard_entry("delete", ctrl=True)
    fake_win.render()
    assert ti.value == "Hello, wo"

    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("left")
    fake_win.render()
    fake_user.keyboard_entry("delete", ctrl=True)
    fake_win.render()
    assert ti.value == "Hello wo"
    fake_user.keyboard_entry("delete", ctrl=True)
    fake_win.render()
    assert ti.value == "Hello"

    fake_user.click_at(ti.global_x, ti.global_y)
    fake_win.render()
    assert ti._get_cursor() == 0

    fake_user.keyboard_entry("delete")
    fake_win.render()
    assert ti.value == "ello"

    fake_user.keyboard_entry("delete", ctrl=True)
    fake_win.render()
    assert ti.value == ""
    fake_user.keyboard_entry("delete", ctrl=True)
    fake_win.render()
    assert ti.value == ""
    fake_user.keyboard_entry("delete", ctrl=False)
    fake_win.render()
    assert ti.value == ""
    fake_user.keyboard_entry("delete", ctrl=True)
    fake_win.render()
    assert ti.value == ""


def test_keyboard_backspace(fake_win, fake_user):
    backspace = "backspace"

    string = "Hello, world!"
    ti = videre.TextInput(text=string)
    placeholder = videre.Container(width=100, height=100)
    fake_win.controls = [
        videre.Container(
            videre.Column([ti, placeholder]),
            padding=videre.Padding.all(20),
            background_color=videre.Colors.red,
        )
    ]
    fake_win.render()
    assert ti._get_cursor() == len(string)
    assert ti.value == string

    fake_user.click_at(ti.global_x, ti.global_y)
    fake_win.render()
    assert ti._get_cursor() == 0

    fake_user.keyboard_entry(backspace)
    fake_win.render()
    assert ti.value == string
    fake_user.keyboard_entry(backspace)
    fake_win.render()
    assert ti.value == string

    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry(backspace)
    fake_win.render()
    assert ti.value == "ello, world!"

    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry("right")
    fake_win.render()
    assert ti._get_cursor() == 4
    fake_user.keyboard_entry(backspace)
    fake_win.render()
    assert ti.value == "ell, world!"
    assert ti._get_cursor() == 3

    fake_user.keyboard_entry(backspace, ctrl=True)
    fake_win.render()
    assert ti.value == ", world!"

    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry("right")
    fake_win.render()
    assert ti._get_cursor() == 2
    fake_user.keyboard_entry(backspace, ctrl=True)
    fake_win.render()
    assert ti.value == "world!"
    fake_user.keyboard_entry("right", ctrl=True)
    fake_win.render()
    fake_user.keyboard_entry("right", ctrl=True)
    fake_win.render()
    fake_user.keyboard_entry(backspace, ctrl=True)
    fake_win.render()
    assert ti.value == "world"
    fake_user.keyboard_entry(backspace, ctrl=True)
    fake_win.render()
    assert ti.value == ""
    fake_user.keyboard_entry(backspace, ctrl=True)
    fake_win.render()
    assert ti.value == ""
    fake_user.keyboard_entry(backspace, ctrl=False)
    fake_win.render()
    assert ti.value == ""
    fake_user.keyboard_entry(backspace, ctrl=True)
    fake_win.render()
    assert ti.value == ""
    return


@pytest.mark.parametrize("key", ("delete", "backspace"))
@pytest.mark.parametrize("ctrl", (False, True))
@pytest.mark.parametrize("shift", (False, True))
def test_delete_selection(fake_win, fake_user, key, ctrl, shift):
    ti = videre.TextInput(text="hello, world")

    fake_win.controls = [ti]
    fake_win.render()
    fake_user.click_at(ti.global_x, ti.global_y)
    fake_win.render()
    assert ti._get_cursor() == 0

    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry("right")
    fake_win.render()
    fake_user.keyboard_entry("right", ctrl=True, shift=True)
    fake_win.render()
    fake_user.keyboard_entry("right", ctrl=True, shift=True)
    fake_win.render()
    assert ti._get_cursor() == 6
    assert ti._get_selection() == (2, 6)

    fake_user.keyboard_entry(key, ctrl=ctrl, shift=shift)
    fake_win.render()
    assert ti.value == "he world"
    assert ti._get_cursor() == 2
    assert ti._get_selection() is None


@patch("videre.core.clipboard.pyperclip.copy")
@patch("videre.core.clipboard.pyperclip.paste")
def test_select_all(mock_paste, mock_copy, fake_win, fake_user):
    string = "hello, world"
    ti = videre.TextInput(text=string)
    fake_win.controls = [ti]
    fake_win.render()
    fake_user.click_at(ti.global_x, ti.global_y)
    fake_win.render()
    assert ti._get_cursor() == 0
    assert ti._get_selection() == (0, 0)

    fake_user.keyboard_entry("a", ctrl=True)
    fake_win.check()
    assert ti._get_cursor() == len(string)
    assert ti._get_selection() == (0, len(string))

    fake_user.keyboard_entry("left", shift=True)
    fake_win.render()
    assert ti._get_cursor() == len(string) - 1
    assert ti._get_selection() == (0, len(string) - 1)

    fake_user.keyboard_entry("c", ctrl=True)
    fake_win.render()
    mock_copy.assert_called_once_with(string[:-1])
    assert ti._get_cursor() == len(string) - 1
    assert ti._get_selection() == (0, len(string) - 1)

    mock_paste.return_value = "blabla"
    fake_user.keyboard_entry("v", ctrl=True)
    fake_win.render()
    mock_paste.assert_called_once()
    assert ti.value == "blabla" + string[-1:] == "blablad"
    assert ti._get_cursor() == len("blabla")
    assert ti._get_selection() is None

    mock_paste.return_value = "toto"
    fake_user.keyboard_entry("v", ctrl=True)
    fake_win.render()
    assert ti.value == "blablatotod"
    assert ti._get_cursor() == len("blablatoto")
    assert ti._get_selection() is None


def test_select_and_text_input(fake_win, fake_user):
    string = "hello, world"
    ti = videre.TextInput(text=string)
    fake_win.controls = [ti]
    fake_win.render()
    fake_user.click_at(ti.global_x, ti.global_y)
    fake_win.render()
    assert ti._get_cursor() == 0
    assert ti._get_selection() == (0, 0)

    fake_user.keyboard_entry("a", ctrl=True)
    fake_win.render()
    assert ti._get_cursor() == len(string)
    assert ti._get_selection() == (0, len(string))

    fake_user.keyboard_entry("left", shift=True)
    fake_win.render()
    assert ti._get_cursor() == len(string) - 1
    assert ti._get_selection() == (0, len(string) - 1)

    fake_user.text_input("lol")
    fake_win.render()
    assert ti.value == "lold"
    assert ti._get_cursor() == len("lol")
    assert ti._get_selection() is None

    fake_user.text_input("ratata")
    fake_win.render()
    assert ti.value == "lolratatad"
    assert ti._get_cursor() == len("lolratata")
    assert ti._get_selection() is None
