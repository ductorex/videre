from types import SimpleNamespace

import videre
from videre.layouts.column import Column
from videre.layouts.form import Form
from videre.widgets.submit_button import SubmitButton


def test_form_values(fake_win):
    ti = videre.TextInput(text="hello", name="username")
    cb = videre.Checkbox(name="agree")
    form = Form(Column([ti, cb]))
    fake_win.controls = [form]
    fake_win.render()

    values = form.values()
    assert values["username"] == "hello"
    assert values["agree"] is False


def test_form_values_auto_name(fake_win):
    ti1 = videre.TextInput(text="a")
    ti2 = videre.TextInput(text="b")
    form = Form(Column([ti1, ti2]))
    fake_win.controls = [form]
    fake_win.render()

    values = form.values()
    assert "TextInput" in values
    assert "TextInput1" in values
    assert set(values.values()) == {"a", "b"}


def test_submit_button(fake_win):
    fake_user = fake_win.user
    data = SimpleNamespace(submitted=None)

    def on_submit(values):
        data.submitted = values

    ti = videre.TextInput(text="world", name="field")
    submit = SubmitButton("Submit", on_submit=on_submit)
    form = Form(Column([ti, submit]))
    fake_win.controls = [form]
    fake_win.render()

    fake_user.click(submit)
    fake_win.render()

    assert data.submitted == {"field": "world"}


def test_submit_button_no_callback(fake_win):
    fake_user = fake_win.user
    submit = SubmitButton("Submit")
    form = Form(Column([videre.TextInput(text="x"), submit]))
    fake_win.controls = [form]
    fake_win.render()

    fake_user.click(submit)
    fake_win.render()  # should not raise
