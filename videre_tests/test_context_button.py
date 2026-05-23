import videre
from videre.widgets.context_button import ContextButton


def test_context_button_open_close(fake_win):
    fake_user = fake_win.user
    called = []
    actions = [
        ("Action 1", lambda: called.append(1)),
        ("Action 2", lambda: called.append(2)),
    ]
    cb = ContextButton("Menu", actions=actions)
    fake_win.controls = [cb]
    fake_win.render()

    assert cb._context is None
    assert not fake_win.has_context()

    # Click to open context menu
    fake_user.click(cb)
    fake_win.render()

    assert cb._context is not None
    assert fake_win.has_context()

    # Click again to close
    fake_user.click(cb)
    fake_win.render()

    assert cb._context is None
    assert not fake_win.has_context()


def test_context_button_execute_action(fake_win):
    fake_user = fake_win.user
    called = []
    actions = [
        ("Action 1", lambda: called.append(1)),
        ("Action 2", lambda: called.append(2)),
    ]
    cb = ContextButton("Menu", actions=actions)
    # Wrap in Column so button gets its natural height (not full window)
    fake_win.controls = [videre.Column([cb])]
    fake_win.render()

    # Open context menu
    fake_user.click(cb)
    fake_win.render()

    assert cb._context is not None

    # Find the first action
    from videre.widgets.context_button import _Action

    action_widgets = fake_win.find(_Action)
    assert len(action_widgets) == 2
    action = action_widgets[0]
    fake_user.click(action)
    fake_win.render()

    assert called == [1]
    assert cb._context is None


def test_context_button_focus_out_closes(fake_win):
    fake_user = fake_win.user
    cb = ContextButton("Menu", actions=[("Action", None)])  # ty: ignore[invalid-argument-type]
    other = videre.Button("Other")
    fake_win.controls = [videre.Column([cb, other])]
    fake_win.render()

    # Open context
    fake_user.click(cb)
    fake_win.render()
    assert cb._context is not None
    assert fake_win._event_manager._focus is cb

    # Click elsewhere to lose focus
    fake_user.click(other)
    fake_win.render()
    assert cb._context is None


def test_context_button_actions_property():
    cb = ContextButton("Menu", actions=["A", ("B", None)])  # ty: ignore[invalid-argument-type]
    assert cb.actions == [("A", None), ("B", None)]


def test_context_button_strips_on_click():
    cb = ContextButton("Menu", on_click=lambda: None)
    # on_click should be ignored (popped from kwargs)
    assert cb._context is None
