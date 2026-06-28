import videre
from videre.core.utils import OnEvent
from videre.widgets.widget_utils import WidgetByKeyGetter


def test_on_event_str():
    oe = OnEvent()

    @oe("click")
    def handle_click():
        pass

    assert "click" in str(oe)
    assert "handle_click" in str(oe)


def test_on_event_len():
    oe = OnEvent()

    @oe(1)
    def a():
        pass

    @oe(2)
    def b():
        pass

    assert len(oe) == 2


def test_on_event_getitem():
    oe = OnEvent()

    @oe("key")
    def handler():
        pass

    assert oe["key"] is handler


def test_on_event_keys_items():
    oe = OnEvent()

    @oe(10)
    def handler():
        pass

    assert list(oe.keys()) == [10]
    items = list(oe.items())
    assert len(items) == 1
    assert items[0][0] == 10
    assert items[0][1] is handler


def test_widget_by_key_getter(fake_win):

    button = videre.Button("Hello", key="my_key")
    fake_win.controls = [button]
    fake_win.render()

    getter = WidgetByKeyGetter("my_key")
    assert getter(button) is True

    result = fake_win.get_element_by_key("my_key")
    assert result is button

    assert fake_win.get_element_by_key("nonexistent") is None
