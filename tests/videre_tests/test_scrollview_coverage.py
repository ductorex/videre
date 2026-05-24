"""Tests for ScrollView edge cases: mouse wheel variants, default_bottom, scroll up."""

from videre import Column, ScrollView, Text


def _make_scrollable(fake_win, fake_user, **scroll_kwargs):
    """Create a ScrollView with enough content to require scrolling."""
    items = [Text(f"Item {i}", size=16) for i in range(30)]
    content = Column(items)
    scroll = ScrollView(content, **scroll_kwargs)
    fake_win.controls = [scroll]
    fake_win.render()
    return scroll


# --- handle_mouse_wheel edge cases ---


def test_mouse_wheel_no_delta(fake_win):
    fake_user = fake_win.user
    """handle_mouse_wheel(0, 0, shift) returns early (line 154)."""
    scroll = _make_scrollable(fake_win, fake_user)
    initial_y = scroll._content_y

    fake_user.mouse_wheel(x=0, y=0)
    fake_win.render()

    assert scroll._content_y == initial_y


def test_mouse_wheel_both_x_and_y(fake_win):
    fake_user = fake_win.user
    """handle_mouse_wheel(x, y) with both non-zero (line 158)."""
    content = Text("Very long horizontal text " * 20, size=16)
    items = [content] + [Text(f"Item {i}", size=16) for i in range(30)]
    scroll = ScrollView(Column(items))
    fake_win.controls = [scroll]
    fake_win.render()

    initial_x = scroll._content_x
    initial_y = scroll._content_y

    # Wheel with both x and y
    fake_user.mouse_wheel(x=-1, y=-1)
    fake_win.render()

    # At least one axis should have moved
    moved = scroll._content_x != initial_x or scroll._content_y != initial_y
    assert moved


def test_mouse_wheel_x_only(fake_win):
    fake_user = fake_win.user
    """handle_mouse_wheel(x, 0) with only x non-zero (line 160)."""
    content = Text("Very long horizontal text " * 30, size=16)
    scroll = ScrollView(content)
    fake_win.controls = [scroll]
    fake_win.render()

    initial_x = scroll._content_x

    # Wheel with only x
    fake_user.mouse_wheel(x=-1, y=0)
    fake_win.render()

    assert scroll._content_x < initial_x


# --- scroll up (line 289) ---


def test_scroll_up_after_down(fake_win):
    fake_user = fake_win.user
    """Scroll down then back up (step > 0, line 289)."""
    scroll = _make_scrollable(fake_win, fake_user)
    assert scroll._content_y == 0

    # Scroll down
    fake_user.mouse_wheel(x=0, y=-1)
    fake_win.render()
    assert scroll._content_y < 0

    down_pos = scroll._content_y

    # Scroll back up
    fake_user.mouse_wheel(x=0, y=1)
    fake_win.render()

    assert scroll._content_y > down_pos


# --- default_bottom (lines 131, 239-249) ---


def test_default_bottom(fake_win):
    fake_user = fake_win.user
    """ScrollView with default_bottom=True scrolls to bottom automatically."""
    scroll = _make_scrollable(fake_win, fake_user, default_bottom=True)

    # With default_bottom, content should be at the bottom
    content_h = scroll._ctrl.rendered_height
    view_h = scroll.rendered_height
    expected_y = view_h - content_h
    assert scroll._content_y == expected_y


def test_default_bottom_canceled_by_scroll(fake_win):
    fake_user = fake_win.user
    """Scrolling up cancels default_bottom."""
    scroll = _make_scrollable(fake_win, fake_user, default_bottom=True)
    assert scroll.default_bottom is True

    # Scroll up (away from bottom)
    fake_user.mouse_wheel(x=0, y=1)
    fake_win.render()

    assert scroll.default_bottom is False


# --- get_mouse_wheel_owner returning self (line 149) ---


def test_mouse_wheel_owner_is_scrollview(fake_win):
    fake_user = fake_win.user
    """When ScrollView has no child ScrollView, it claims wheel ownership itself."""
    scroll = _make_scrollable(fake_win, fake_user)
    # The scroll is rendered, mouse at (0,0) is inside it
    owner = scroll.get_mouse_wheel_owner(5, 5)
    assert owner is not None
    assert owner.widget is scroll
