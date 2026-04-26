import threading
import time
from types import SimpleNamespace

import pytest
import videre


def test_window_change_background(fake_win):
    fake_win.check("white")
    fake_win.background = "red"
    fake_win.check("red")


def test_window_notify(fake_win, fake_user):
    data = SimpleNamespace(notifications=[], send_called=0, cb_called=0)

    def send_notification(*args):
        data.send_called += 1
        fake_win.notify("Test Notification")

    button = videre.Button("Send Notification", on_click=send_notification)
    fake_win.controls = [button]

    def callback(notification):
        data.cb_called += 1
        assert notification == "Test Notification"
        data.notifications.append(notification)

    fake_win.set_notification_callback(callback)

    fake_win.render()
    assert data.send_called == 0
    assert data.cb_called == 0
    assert len(data.notifications) == 0

    fake_user.click(button)
    # First render will handle click
    fake_win.render()
    assert data.send_called == 1
    assert data.cb_called == 0
    # Then second render will process the notification
    fake_win.render()
    assert data.send_called == 1
    assert data.cb_called == 1
    assert len(data.notifications) == 1
    assert data.notifications[0] == "Test Notification"


def test_window_run(fake_user):
    from videre.windowing.window import Window

    win = Window("Test Window", width=200, height=200, hide=True)

    def stop_window():
        time.sleep(0.5)
        fake_user.quit()

    thread = threading.Thread(target=stop_window)
    thread.start()

    assert win.nb_frames == 0
    win.run()
    assert win.nb_frames > 0

    # Cannot run again
    with pytest.raises(RuntimeError, match="Window has already run. Cannot run again."):
        win.run()
