import videre


def test_radio(fake_win, fake_user):
    radio1 = videre.Radio(value="one")
    radio2 = videre.Radio(value="two")
    radio3 = videre.Radio(value="three")
    text = videre.Text("none")

    def on_change(group: videre.RadioGroup):
        text.text = group.value

    group = videre.RadioGroup(
        videre.Column([radio1, radio2, radio3, text]), on_change=on_change
    )

    fake_win.controls = [group]
    fake_win.render()
    assert text.text == "none"

    fake_user.click(radio1)
    fake_win.render()
    assert text.text == "one"

    fake_user.click(radio2)
    fake_win.render()
    assert text.text == "two"

    fake_user.click(radio3)
    fake_win.render()
    assert text.text == "three"

    # Click again on the same radio
    # Should not change the text,
    # since we can't deselect in this radio group
    fake_user.click(radio3)
    fake_win.render()
    assert text.text == "three"

    # Manually set radiogroup value
    group.value = "one"
    fake_win.render()
    assert text.text == "one"

    group.value = "three"
    fake_win.render()
    assert text.text == "three"

    fake_win.check()


def test_radio_initial_checked(fake_win):
    radio1 = videre.Radio(value="one")
    radio2 = videre.Radio(value="two")
    radio3 = videre.Radio(value="three")

    group = videre.RadioGroup(videre.Column([radio1, radio2, radio3]), value="two")

    fake_win.controls = [group]
    fake_win.render()

    assert radio1._get_checked() is False
    assert radio2._get_checked() is True  # Should be checked
    assert radio3._get_checked() is False


def test_radio_deselect(fake_win, fake_user):
    radio1 = videre.Radio(value="one")
    radio2 = videre.Radio(value="two")
    radio3 = videre.Radio(value="three")

    group = videre.RadioGroup(
        videre.Column([radio1, radio2, radio3]), value="two", can_deselect=True
    )

    fake_win.controls = [group]
    fake_win.render()

    assert radio1._get_checked() is False
    assert radio2._get_checked() is True  # Should be checked
    assert radio3._get_checked() is False

    # Click the checked radio to deselect it
    fake_user.click(radio2)
    fake_win.render()

    assert radio1._get_checked() is False
    assert radio2._get_checked() is False  # Should be unchecked now
    assert radio3._get_checked() is False


def test_radio_outside_group(fake_win, fake_user):
    radio = videre.Radio(value="test")
    fake_win.controls = [radio]
    fake_win.render()
    assert not radio._get_checked()  # Initially unchecked

    # Nothing should happen when clicking a radio outside a group
    fake_user.click(radio)
    fake_win.render()

    assert not radio._get_checked()  # Radio should not be checked
    assert radio._get_radio_group(None) is None
