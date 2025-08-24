import videre


def test_rendered_button_sizes(fake_win):
    b1 = videre.Button("")
    bs = videre.Button(" ")
    b2 = videre.Button("hello")
    b3 = videre.Button("Hello")
    br = videre.Radio(None)
    bc = videre.Checkbox()
    fake_win.controls = [
        videre.Column(
            [b1, bs, b2, b3, br, bc], horizontal_alignment=videre.Alignment.CENTER
        )
    ]
    fake_win.render()
    print()
    print("b:empty", b1.rendered_height)
    print("b:space", bs.rendered_height)
    print("b:hello", b2.rendered_height)
    print("b:Hello", b3.rendered_height)
    print("radio", br.rendered_height)
    print("checkbox", bc.rendered_height)
    print("standard", fake_win.fonts.font_height)
    fake_win.check()
