import pytest

import videre
from videre.core.clipboard import Clipboard


def test_value(fake_win):
    ti = videre.TextInput()
    fake_win.controls = [ti]

    fake_win.check("value_empty")
    assert ti.value == ""

    ti.value = "test"
    fake_win.check("value_test")
    assert ti.value == "test"


def test_cursor(fake_win):
    fake_user = fake_win.user
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


def test_cursor_move_by_keyboard(fake_win):
    fake_user = fake_win.user
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
    assert ti._text._rendered is not None

    caret_pos = ti._text._rendered.visual_state(5).pixel
    fake_user.click_at(ti.global_x + caret_pos.x, ti.global_y + 1)
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


def test_cursor_mouse_on_empty(fake_win):
    fake_user = fake_win.user
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


def test_cursor_move_by_mouse(fake_win):
    fake_user = fake_win.user
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
    assert fake_win.backend.cursor_is_default()

    rendered = ti._text._rendered
    assert rendered is not None

    def x_for_pos(pos: int) -> int:
        return ti.global_x + rendered.visual_state(pos).pixel.x

    # Click
    x = x_for_pos(5)
    y = ti.global_y + 5
    fake_user.click_at(x, y)
    fake_win.check("cursor_5")
    assert ti._get_cursor() == 5
    # Even a click will trigger selection,
    # since "mouse down" event will set a new selection
    # ("mouse up" event does not cancel the selection)
    assert ti._get_selection() == (5, 5)

    # Another click
    x = x_for_pos(4)
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
    x = x_for_pos(2)
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_2")
    assert ti._get_cursor() == 2
    assert ti._get_selection() == (2, 4)

    # Check mouse cursor
    # Mouse motion should have triggered a mouse enter,
    # to cursor should have changed
    assert not fake_win.backend.cursor_is_default()

    # Mouse down move left again
    x = x_for_pos(1)
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_1")
    assert ti._get_cursor() == 1
    assert ti._get_selection() == (1, 4)

    # Mouse down move left
    x = x_for_pos(0)
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_0")
    assert ti._get_cursor() == 0
    assert ti._get_selection() == (0, 4)

    # Mouse down right
    x = x_for_pos(6)
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_6")
    assert ti._get_cursor() == 6
    assert ti._get_selection() == (4, 6)

    # Mouse down right again
    x = x_for_pos(len(string)) + 5
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_select_13")
    assert ti._get_cursor() == 13
    assert ti._get_selection() == (4, 13)

    # Mouse down left again to empty selection
    x = x_for_pos(4)
    fake_user.mouse_motion(x, y, button_left=True)
    fake_win.check("cursor_4")
    assert ti._get_cursor() == 4
    assert ti._get_selection() == (4, 4)

    # Mouse exit
    fake_user.mouse_motion(placeholder.global_x, placeholder.global_y)
    fake_win.check("cursor_4")
    # Check mouse cursor
    assert fake_win.backend.cursor_is_default()


def test_keyboard_delete(fake_win):
    fake_user = fake_win.user
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


def test_keyboard_backspace(fake_win):
    fake_user = fake_win.user
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
def test_delete_selection(fake_win, key, ctrl, shift):
    fake_user = fake_win.user
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


def test_select_all(fake_win):
    fake_user = fake_win.user
    clipboard_store = {"content": ""}
    original_copy = Clipboard._copy
    original_paste = Clipboard._paste
    Clipboard._copy = staticmethod(lambda text: clipboard_store.update(content=text))
    Clipboard._paste = staticmethod(lambda: clipboard_store["content"])

    try:
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
        assert clipboard_store["content"] == string[:-1]
        assert ti._get_cursor() == len(string) - 1
        assert ti._get_selection() == (0, len(string) - 1)

        clipboard_store["content"] = "blabla"
        fake_user.keyboard_entry("v", ctrl=True)
        fake_win.render()
        assert ti.value == "blabla" + string[-1:] == "blablad"
        assert ti._get_cursor() == len("blabla")
        assert ti._get_selection() is None

        clipboard_store["content"] = "toto"
        fake_user.keyboard_entry("v", ctrl=True)
        fake_win.render()
        assert ti.value == "blablatotod"
        assert ti._get_cursor() == len("blablatoto")
        assert ti._get_selection() is None
    finally:
        Clipboard._copy = original_copy
        Clipboard._paste = original_paste


def test_select_and_text_input(fake_win):
    fake_user = fake_win.user
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


# ---------------------------------------------------------------------------
# Grapheme-cluster editing: every text-mutating / cursor operation works at
# edit-unit (grapheme) granularity, so a multi-codepoint cluster is never
# split. "é" is e + combining acute (one 2-codepoint cluster); the text
# "aéb" has edit-unit boundaries (0, 1, 3, 4).
# ---------------------------------------------------------------------------

_COMBINING = "aéb"  # a | e+combining-acute | b


def _focus_at_start(fake_win, ti):
    """Focus the input and leave the cursor at source position 0."""
    fake_win.user.click_at(ti.global_x, ti.global_y)
    fake_win.render()
    assert ti._get_cursor() == 0


def test_grapheme_backspace_removes_whole_cluster(fake_win):
    fake_user = fake_win.user
    ti = videre.TextInput(text=_COMBINING)
    fake_win.controls = [ti]
    fake_win.render()
    _focus_at_start(fake_win, ti)
    ti._set_cursor_to_pos(len(_COMBINING))  # source position 4 (end)
    fake_win.render()

    fake_user.keyboard_entry("backspace")
    fake_win.render()
    assert ti.value == "aé"  # removed 'b'
    assert ti._get_cursor() == 3

    fake_user.keyboard_entry("backspace")
    fake_win.render()
    assert ti.value == "a"  # removed the whole 2-codepoint cluster, not half
    assert ti._get_cursor() == 1


def test_grapheme_delete_removes_whole_cluster(fake_win):
    fake_user = fake_win.user
    ti = videre.TextInput(text=_COMBINING)
    fake_win.controls = [ti]
    fake_win.render()
    _focus_at_start(fake_win, ti)
    ti._set_cursor_to_pos(1)  # right after 'a', at the cluster's left edge
    fake_win.render()

    fake_user.keyboard_entry("delete")
    fake_win.render()
    assert ti.value == "ab"  # the whole cluster is gone
    assert ti._get_cursor() == 1


def test_grapheme_backspace_from_inside_cluster(fake_win):
    fake_user = fake_win.user
    ti = videre.TextInput(text=_COMBINING)
    fake_win.controls = [ti]
    fake_win.render()
    _focus_at_start(fake_win, ti)
    ti._set_cursor_to_pos(2)  # between 'e' and its combining mark
    fake_win.render()

    fake_user.keyboard_entry("backspace")
    fake_win.render()
    assert ti.value == "ab"  # whole cluster removed, never a lone half
    assert ti._get_cursor() == 1


def test_grapheme_arrows_skip_whole_cluster(fake_win):
    fake_user = fake_win.user
    ti = videre.TextInput(text=_COMBINING)
    fake_win.controls = [ti]
    fake_win.render()
    _focus_at_start(fake_win, ti)

    fake_user.keyboard_entry("right")  # past 'a'
    fake_win.render()
    assert ti._get_cursor() == 1
    fake_user.keyboard_entry("right")  # over the 2-codepoint cluster in one press
    fake_win.render()
    assert ti._get_cursor() == 3
    fake_user.keyboard_entry("right")  # past 'b'
    fake_win.render()
    assert ti._get_cursor() == 4

    fake_user.keyboard_entry("left")
    fake_win.render()
    assert ti._get_cursor() == 3
    fake_user.keyboard_entry("left")  # back over the whole cluster in one press
    fake_win.render()
    assert ti._get_cursor() == 1
    fake_user.keyboard_entry("left")
    fake_win.render()
    assert ti._get_cursor() == 0


def test_grapheme_shift_selection_deletes_whole_clusters(fake_win):
    fake_user = fake_win.user
    ti = videre.TextInput(text=_COMBINING)
    fake_win.controls = [ti]
    fake_win.render()
    _focus_at_start(fake_win, ti)

    fake_user.keyboard_entry("right", shift=True)  # select 'a'
    fake_win.render()
    fake_user.keyboard_entry("right", shift=True)  # extend over the whole cluster
    fake_win.render()
    fake_user.keyboard_entry("backspace")
    fake_win.render()
    assert ti.value == "b"  # both whole clusters removed
    assert ti._get_cursor() == 0


def test_grapheme_copy_copies_whole_cluster(fake_win):
    fake_user = fake_win.user
    clipboard_store = {"content": ""}
    original_copy = Clipboard._copy
    original_paste = Clipboard._paste
    Clipboard._copy = staticmethod(lambda text: clipboard_store.update(content=text))
    Clipboard._paste = staticmethod(lambda: clipboard_store["content"])
    try:
        ti = videre.TextInput(text=_COMBINING)
        fake_win.controls = [ti]
        fake_win.render()
        _focus_at_start(fake_win, ti)

        fake_user.keyboard_entry("right", shift=True)  # select 'a'
        fake_win.render()
        fake_user.keyboard_entry("right", shift=True)  # select the whole cluster too
        fake_win.render()
        fake_user.keyboard_entry("c", ctrl=True)
        fake_win.render()
        # The whole cluster lands on the clipboard, not a dangling "ae".
        assert clipboard_store["content"] == "aé"
    finally:
        Clipboard._copy = original_copy
        Clipboard._paste = original_paste


def test_grapheme_text_input_inserts_on_a_boundary(fake_win):
    fake_user = fake_win.user
    ti = videre.TextInput(text="é")  # a single combining cluster
    fake_win.controls = [ti]
    fake_win.render()
    _focus_at_start(fake_win, ti)

    fake_user.text_input("x")
    fake_win.render()
    assert ti.value == "xé"  # inserted before the cluster, not inside it
    assert ti._get_cursor() == 1  # cursor on a boundary
