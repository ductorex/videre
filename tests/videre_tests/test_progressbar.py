from videre import Column, ProgressBar


def test_progressbar(fake_win):
    fake_win.controls = [
        Column(
            [
                ProgressBar(),
                ProgressBar(),
                ProgressBar(0.1),
                ProgressBar(0.5),
                ProgressBar(0.8),
                ProgressBar(0.9),
                ProgressBar(1),
            ]
        )
    ]
    fake_win.check()
