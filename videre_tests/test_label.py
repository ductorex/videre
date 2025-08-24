from types import SimpleNamespace

import videre
from videre.core.constants import MouseButton
from videre.core.events import MouseEvent
from videre.widgets.empty_widget import EmptyWidget


def test_label(fake_win, fake_user):
    checkbox = videre.Checkbox(key="a checkbox")
    label = videre.Label(checkbox, text="control checkbox!", height_delta=0)
    fake_win.controls = [
        videre.Row([label, videre.Container(checkbox, padding=videre.Padding(left=10))])
    ]
    fake_win.check("r0")
    assert not checkbox.checked
    assert label._for_button is checkbox
    assert label._for_key == "a checkbox"

    fake_user.click(label)
    fake_win.check("r1")
    assert checkbox.checked


def test_label_with_key(fake_win, fake_user):
    key = "my_checkbox"
    checkbox = videre.Checkbox(key=key)
    label = videre.Label(key, text="control checkbox!", height_delta=0)
    fake_win.controls = [
        videre.Row([label, videre.Container(checkbox, padding=videre.Padding(left=10))])
    ]
    fake_win.check("r0")
    assert not checkbox.checked
    assert label._for_button is None
    assert label._for_key == key

    fake_user.click(label)
    fake_win.check("r1")
    assert checkbox.checked
    assert label._for_button is checkbox


def test_label_get_button_not_found(fake_win):
    """Test label when target widget not found"""
    label = videre.Label("nonexistent_key", text="No target")

    fake_win.controls = [label]
    fake_win.render()
    assert label._for_button is None

    found_button = label._get_button()
    assert isinstance(found_button, EmptyWidget)
    assert label._for_button is found_button


def test_label_get_button_multiple_matches(fake_win):
    """Test _get_button when multiple widgets have same key"""
    button1 = videre.Button("Button 1", key="duplicate")
    button2 = videre.Button("Button 2", key="duplicate")
    label = videre.Label("duplicate", text="Ambiguous target")

    fake_win.controls = [videre.Row([button1, button2, label])]
    fake_win.render()

    found_button = label._get_button()
    assert isinstance(found_button, EmptyWidget)
    assert found_button is not button1
    assert found_button is not button2
    assert label._for_button is found_button  # Should be cached


def test_label_mouse_enter_event_propagation(fake_win):
    """Test mouse enter event propagation from label to target"""
    events = SimpleNamespace(mouse_enter_called=False, event_x=None, event_y=None)

    class TrackingButton(videre.Button):
        def handle_mouse_enter(self, event):
            events.mouse_enter_called = True
            events.event_x = event.x
            events.event_y = event.y
            return super().handle_mouse_enter(event)

    button = TrackingButton("Target", key="track_button")
    label = videre.Label("track_button", text="Track mouse enter")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # Get button position for coordinate transformation
    button_x, button_y = button.x, button.y

    # Simulate mouse enter on label
    label.handle_mouse_enter(MouseEvent(x=button_x, y=button_y))

    assert events.mouse_enter_called is True
    assert events.event_x == button_x
    assert events.event_y == button_y


def test_label_mouse_exit_event_propagation(fake_win):
    """Test mouse exit event propagation"""
    events = SimpleNamespace(mouse_exit_called=False)

    class TrackingButton(videre.Button):
        def handle_mouse_exit(self):
            events.mouse_exit_called = True
            return super().handle_mouse_exit()

    button = TrackingButton("Target", key="track_exit")
    label = videre.Label("track_exit", text="Track mouse exit")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # Simulate mouse exit on label
    label.handle_mouse_exit()

    assert events.mouse_exit_called is True


def test_label_mouse_down_event_propagation(fake_win):
    """Test mouse down event propagation"""
    events = SimpleNamespace(mouse_down_called=False, event_passed=None)

    class TrackingButton(videre.Button):
        def handle_mouse_down(self, event):
            events.mouse_down_called = True
            events.event_passed = event
            return super().handle_mouse_down(event)

    button = TrackingButton("Target", key="track_down")
    label = videre.Label("track_down", text="Track mouse down")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # Simulate mouse down on label
    mouse_event = MouseEvent(x=10, y=20)
    label.handle_mouse_down(mouse_event)

    assert events.mouse_down_called is True
    assert events.event_passed is mouse_event


def test_label_mouse_up_event_propagation(fake_win):
    """Test mouse up event propagation"""
    events = SimpleNamespace(mouse_up_called=False, event_passed=None)

    class TrackingButton(videre.Button):
        def handle_mouse_up(self, event):
            events.mouse_up_called = True
            events.event_passed = event
            return super().handle_mouse_up(event)

    button = TrackingButton("Target", key="track_up")
    label = videre.Label("track_up", text="Track mouse up")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # Simulate mouse up on label
    mouse_event = MouseEvent(x=15, y=25, buttons=[MouseButton.BUTTON_LEFT])
    label.handle_mouse_up(mouse_event)

    assert events.mouse_up_called is True
    assert events.event_passed is mouse_event


def test_label_mouse_down_canceled_propagation(fake_win):
    """Test mouse down canceled event propagation"""
    events = SimpleNamespace(canceled_called=False, button_passed=None)

    class TrackingButton(videre.Button):
        def handle_mouse_down_canceled(self, button):
            events.canceled_called = True
            events.button_passed = button
            return super().handle_mouse_down_canceled(button)

    button = TrackingButton("Target", key="track_cancel")
    label = videre.Label("track_cancel", text="Track cancel")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # Simulate mouse down canceled on label
    label.handle_mouse_down_canceled(MouseButton.BUTTON_RIGHT)

    assert events.canceled_called is True
    assert events.button_passed == MouseButton.BUTTON_RIGHT


def test_label_click_event_propagation(fake_win):
    """Test click event propagation"""
    events = SimpleNamespace(click_called=False, button_passed=None)

    class TrackingButton(videre.Button):
        def handle_click(self, button):
            events.click_called = True
            events.button_passed = button
            return super().handle_click(button)

    button = TrackingButton("Target", key="track_click")
    label = videre.Label("track_click", text="Track click")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # Simulate click on label
    label.handle_click(MouseButton.BUTTON_LEFT)

    assert events.click_called is True
    assert events.button_passed == MouseButton.BUTTON_LEFT


def test_label_caching_behavior(fake_win):
    """Test that _get_button caches the result"""
    button = videre.Button("Target", key="cache_test")
    label = videre.Label("cache_test", text="Test caching")

    fake_win.controls = [videre.Row([button, label])]
    fake_win.render()

    # First call should find and cache the button
    first_result = label._get_button()
    assert first_result is button
    assert label._for_button is button

    # Second call should return cached result
    second_result = label._get_button()
    assert second_result is button
    assert second_result is first_result
