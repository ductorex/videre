import videre
from videre.widgets.abstractanimation import FPR


def test_progressing(fake_win):
    print()
    fake_win.controls = [videre.Progressing(framing=FPR(1), steps=4)]
    # forward
    fake_win.check("r0")
    fake_win.check("r1")
    fake_win.check("r2")
    fake_win.check("r3")
    fake_win.check("r4")
    # backward
    fake_win.check("r5")
    fake_win.check("r6")
    fake_win.check("r7")
    fake_win.check("r8")
    # forward again
    fake_win.check("r9")
