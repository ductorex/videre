import pygame
import pytest

import videre
from videre import Column, Container, ScrollView, Text
from videre.testing.utils import HD


class TestScrollViewRendering:
    """Test visual rendering of ScrollView in different configurations"""

    def test_no_scroll_needed(self, snap_win):
        """Test ScrollView when content fits entirely in view"""
        content = Text("Small content", size=20)
        scroll = ScrollView(content)
        snap_win.controls = [scroll]

    def test_horizontal_scroll_only(self, snap_win):
        """Test ScrollView with only horizontal scrollbar visible"""
        content = Text(
            "Very long text that definitely needs horizontal scrolling " * 10, size=16
        )
        scroll = ScrollView(content, vertical_scroll=False)
        snap_win.controls = [scroll]

    def test_vertical_scroll_only(self, snap_win):
        """Test ScrollView with only vertical scrollbar visible"""
        items = [Text(f"Item {i}", size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(content, horizontal_scroll=False)
        snap_win.controls = [scroll]

    def test_both_scrollbars(self, snap_win):
        """Test ScrollView with both scrollbars visible"""
        items = [
            Text(
                f"Very long item text that needs horizontal scrolling {i} " * 5, size=14
            )
            for i in range(15)
        ]
        content = Column(items)
        scroll = ScrollView(content)
        snap_win.controls = [scroll]

    @pytest.mark.parametrize("thickness", [12, 18, 24])
    def test_scroll_thickness_variants(self, snap_win, thickness):
        """Test different scrollbar thickness values"""
        content = Column(
            [Text(f"Item {i} with long text " * 3, size=14) for i in range(20)]
        )
        scroll = ScrollView(content, scroll_thickness=thickness)
        snap_win.controls = [scroll]

    @pytest.mark.parametrize("wrap_horizontal", [True, False])
    def test_wrap_horizontal(self, snap_win, wrap_horizontal):
        """Test ScrollView with horizontal wrapping enabled"""
        content = Text(
            "Long text that should wrap horizontally when wrap is enabled " * 5,
            size=14,
            wrap=videre.TextWrap.WORD,
        )
        scroll = ScrollView(
            content, wrap_horizontal=wrap_horizontal, vertical_scroll=False
        )
        snap_win.controls = [scroll]

    @pytest.mark.parametrize("wrap_vertical", [True, False])
    def test_wrap_vertical(self, snap_win, wrap_vertical):
        """Test ScrollView with vertical wrapping enabled"""
        items = [Text(f"Item {i}", size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(
            content, wrap_vertical=wrap_vertical, horizontal_scroll=False
        )
        snap_win.controls = [scroll]


class TestScrollViewInteractions:
    """Test user interactions with ScrollView scrollbars and mouse wheel"""

    def test_scrollbar_hover_states(self, fake_win, fake_user):
        """Test visual feedback when hovering over scrollbars"""
        items = [Text(f"Item {i}", size=16) for i in range(15)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.check("hover_false")

        v_scrollbar = scroll._vscrollbar
        assert v_scrollbar._hover is False

        # Simulate mouse enter on scrollbar
        hover_x = v_scrollbar.global_x + 5
        hover_y = v_scrollbar.global_y + 10
        fake_user.mouse_motion(hover_x, hover_y)

        fake_win.check("hover_true")
        assert v_scrollbar._hover is True

    def test_wheel_vertical_scroll(self, fake_win, fake_user):
        """Test vertical scrolling with mouse wheel"""
        items = [Text(f"Item {i}", size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.check("scroll_false")

        # Get initial scroll position
        initial_y = scroll._content_y

        # Simulate mouse wheel down (scroll down)
        fake_user.mouse_wheel(x=0, y=-1)
        fake_win.check("scroll_true")

        # Content should have moved up (negative direction)
        assert scroll._content_y < initial_y

    def test_wheel_horizontal_scroll_with_shift(self, fake_win, fake_user):
        """Test horizontal scrolling with Shift+mouse wheel"""
        content = Text("Very long horizontal text " * 20, size=16)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.check("scroll_false")

        initial_x = scroll._content_x

        # Simulate Shift+wheel (horizontal scroll)
        # This requires mocking the shift key state

        original_get_mods = pygame.key.get_mods
        pygame.key.get_mods = lambda: pygame.KMOD_SHIFT

        try:
            fake_user.mouse_wheel(x=0, y=-1)
            fake_win.check("scroll_true")

            # Content should have moved horizontally
            assert scroll._content_x < initial_x
        finally:
            pygame.key.get_mods = original_get_mods

    @pytest.mark.win_params(HD)
    def test_wheel_at_scroll_limits(self, fake_win, fake_user):
        """Test mouse wheel behavior at scroll boundaries"""
        items = [Text(f"Item {i}", size=16) for i in range(10)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]  # Large enough for all content
        fake_win.check()

        # When content fits in view, wheel should not scroll
        initial_y = scroll._content_y
        fake_user.mouse_wheel(x=0, y=-1)
        # Render should not change
        fake_win.check()

        # Position should not change as no scroll is needed
        assert scroll._content_y == initial_y == 0

    def test_scrollbar_click_jump(self, fake_win, fake_user):
        """Test clicking on scrollbar track to jump to position"""
        items = [Text(f"Item {i}" * 20, size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.check("jump_false")

        # Get the vertical scrollbar
        v_scrollbar = scroll._vscrollbar
        initial_y = scroll._content_y

        # Click somewhere on the scrollbar track (not on the grip)
        click_x = v_scrollbar.global_x + 5
        click_y = v_scrollbar.global_y + v_scrollbar.background.rendered_height - 2

        # Simulate mouse click
        fake_user.click_at(click_x, click_y)
        fake_win.check("jump_true")

        # Content should have jumped to new position
        assert scroll._content_y < initial_y

        # Get the horizontal scrollbar
        h_scrollbar = scroll._hscrollbar
        initial_x = scroll._content_x
        # Click somewhere on the horizontal scrollbar track
        click_x = h_scrollbar.global_x + h_scrollbar.background.rendered_width - 2
        click_y = h_scrollbar.global_y + 5
        # Simulate mouse click
        fake_user.click_at(click_x, click_y)
        fake_win.check("jump_horizontal_true")

        # Content should have jumped to new horizontal position
        assert scroll._content_x < initial_x

    def test_scrollbar_drag_interaction(self, fake_win, fake_user):
        """Test dragging scrollbar grip to scroll content"""
        items = [Text(f"Item {i}", size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.check("drag_0")

        v_scrollbar = scroll._vscrollbar

        # Test clicking and dragging the scrollbar grip
        grip_x = v_scrollbar.global_x + 5
        grip_y = v_scrollbar.global_y + 10

        # Mouse down on grip
        assert v_scrollbar._grabbed == ()
        fake_user.mouse_motion(grip_x, grip_y)
        fake_user.mouse_down(grip_x, grip_y)
        fake_win.check("drag_1")
        assert v_scrollbar._grabbed != ()

        # Drag to new position
        new_y = grip_y + 20
        fake_user.mouse_motion(grip_x, new_y, button_left=True)
        fake_win.check("drag_2")

        # Mouse up to finish drag
        fake_user.mouse_up(grip_x, new_y)
        fake_win.check("drag_3")
        assert v_scrollbar._grabbed == ()

    def test_horizontal_scrollbar_drag_interactions(self, fake_win, fake_user):
        """Test horizontal scrollbar mouse interactions"""
        content = Text("Very long horizontal text " * 20, size=16)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.check("drag_0")

        h_scrollbar = scroll._hscrollbar

        # Mouse down on horizontal scrollbar grip
        grip_x = h_scrollbar.global_x + 10
        grip_y = h_scrollbar.global_y + 5
        assert h_scrollbar._grabbed == ()
        fake_user.mouse_motion(grip_x, grip_y)
        fake_user.mouse_down(grip_x, grip_y)
        fake_win.check("drag_1")
        assert h_scrollbar._grabbed != ()

        # Dragging the horizontal scrollbar grip
        new_x = h_scrollbar.global_x + 15
        fake_user.mouse_motion(new_x, grip_y, button_left=True)
        fake_win.check("drag_2")

        # Mouse up to finish drag
        fake_user.mouse_up(new_x, grip_y)
        fake_win.check("drag_3")
        assert h_scrollbar._grabbed == ()

        # Move mouse away to test hover exit
        assert h_scrollbar._hover is True
        fake_user.mouse_motion(0, 0)
        fake_win.check("drag_4")
        assert h_scrollbar._hover is False

    def test_scrollbar_mouse_cancel_events(self, fake_win, fake_user):
        """Test scrollbar mouse cancel events"""
        items = [Text(f"Item {i}", size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.render()

        v_scrollbar = scroll._vscrollbar

        # Start a drag operation
        grip_x = v_scrollbar.global_x + 5
        grip_y = v_scrollbar.global_y + 10
        assert v_scrollbar._grabbed == ()
        fake_user.mouse_down(grip_x, grip_y)
        fake_win.render()
        assert v_scrollbar._grabbed != ()

        # Cancel the drag with mouse_down_canceled
        fake_user.mouse_up(grip_x, grip_y)
        fake_win.render()
        assert v_scrollbar._grabbed == ()


class TestScrollViewConfiguration:
    """Test ScrollView configuration and property changes"""

    def test_change_scroll_thickness(self, fake_win):
        """Test dynamically changing scrollbar thickness"""
        content = Column([Text(f"Long item {i} " * 5, size=16) for i in range(20)])
        scroll = ScrollView(content, scroll_thickness=18)
        fake_win.controls = [scroll]
        fake_win.check("thickness_18")

        assert scroll.scroll_thickness == 18
        assert scroll._hscrollbar.thickness == 18
        assert scroll._vscrollbar.thickness == 18
        # Change thickness
        scroll.scroll_thickness = 24
        fake_win.check("thickness_24")

        assert scroll.scroll_thickness == 24
        assert scroll._vscrollbar.thickness == 24
        assert scroll._hscrollbar.thickness == 24

    def test_toggle_horizontal_scroll(self, fake_win):
        """Test enabling/disabling horizontal scroll"""
        content = Text("Very long horizontal text " * 20, size=16)
        scroll = ScrollView(content, horizontal_scroll=True)
        fake_win.controls = [scroll]
        fake_win.check("horizontal_scroll_true")

        # Disable horizontal scrolling
        scroll.horizontal_scroll = False
        fake_win.check("horizontal_scroll_false")

        # Horizontal scrollbar should not be visible
        assert scroll.horizontal_scroll is False

    def test_toggle_vertical_scroll(self, fake_win):
        """Test enabling/disabling vertical scroll"""
        items = [Text(f"Item {i}", size=16) for i in range(20)]
        content = Column(items)
        scroll = ScrollView(content, vertical_scroll=True)
        fake_win.controls = [scroll]
        fake_win.check("vertical_scroll_true")

        scroll.vertical_scroll = False
        fake_win.check("vertical_scroll_false")

        assert scroll.vertical_scroll == False

    def test_change_control_content(self, fake_win):
        """Test changing the scrolled control content"""
        content1 = Text("Original content " * 5, size=16)
        scroll = ScrollView(content1)
        fake_win.controls = [scroll]
        fake_win.check("content1")
        assert scroll.control is content1

        # Change to new content
        content2 = Column([Text(f"New item {i}", size=14) for i in range(20)])
        scroll.control = content2
        fake_win.check("content2")

        assert scroll.control is content2


class TestScrollViewEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.win_params({"width": 50, "height": 50})
    def test_very_small_viewport(self, fake_win):
        """Test ScrollView with very small viewport"""
        content = Column([Text(f"Item {i}", size=16) for i in range(10)])
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.render()

        # Should handle gracefully without crashes
        assert scroll.rendered_width <= 50
        assert scroll.rendered_height <= 50

    def test_invalid_thickness_handling(self, fake_win):
        """Test handling of invalid thickness values"""
        content = Text("Test content " * 5, size=20)

        # Test with zero thickness (should work or have reasonable default)
        scroll = ScrollView(content, scroll_thickness=0)
        fake_win.controls = [scroll]

        # Should render without crashing
        fake_win.render()

        # Test negative thickness - should be handled gracefully
        scroll.scroll_thickness = -5
        fake_win.render()  # Should not crash

    def test_nested_scrollviews_mouse_wheel(self, fake_win, fake_user):
        """Test mouse wheel propagation with nested ScrollViews"""
        inner_content = Column([Text(f"Inner {i}", size=14) for i in range(10)])
        inner_scroll = ScrollView(inner_content)

        outer_content = Column(
            [
                Text("Before inner scroll", size=16),
                Container(inner_scroll, width=150, height=100),
                Text("After inner scroll", size=16),
            ]
            + [Text(f"Outer item {i}", size=14) for i in range(10)]
        )

        outer_scroll = ScrollView(outer_content)
        fake_win.controls = [outer_scroll]
        fake_win.check("default")

        # Mouse wheel should affect the appropriate scrollview based on mouse position
        original_mouse_pos = pygame.mouse.get_pos
        try:
            inner_x = inner_scroll.global_x + 1
            inner_y = inner_scroll.global_y + 1
            pygame.mouse.get_pos = lambda: (inner_x, inner_y)
            fake_user.mouse_wheel(x=0, y=-1)
            fake_win.check("scroll_inner")

            outer_x = inner_scroll.right + 2
            outer_y = outer_scroll.global_y + 1
            pygame.mouse.get_pos = lambda: (outer_x, outer_y)
            fake_user.mouse_wheel(x=0, y=-1)
            fake_win.check("scroll_outer")
        finally:
            pygame.mouse.get_pos = original_mouse_pos


class TestScrollViewAlgorithms:
    """Test internal algorithms and calculations"""

    def test_scroll_metrics_calculation(self):
        """Test _compute_scroll_metrics calculation accuracy"""
        # Test the static method directly
        from videre.layouts.scroll._h_scroll_bar import _HScrollBar

        # Case: content larger than view
        view_length = 200
        content_length = 500
        content_pos = -150  # Scrolled 150px to the right

        scroll_pos, scroll_length = _HScrollBar._compute_scroll_metrics(
            view_length, content_length, content_pos
        )

        # Verify calculations
        expected_scroll_pos = (200 * 150) / 500  # = 60
        expected_scroll_length = (200 * 200) / 500  # = 80

        assert scroll_pos == round(expected_scroll_pos)
        assert scroll_length == round(expected_scroll_length)

    def test_can_scroll_logic(self):
        """Test _can_scroll method logic"""
        from videre.layouts.scroll.scrollview import ScrollView

        # Test scroll up (direction > 0) - should work if content_pos < 0
        assert ScrollView._can_scroll(1, True, 200, 500, -100) is True
        assert ScrollView._can_scroll(1, True, 200, 500, 0) is False

        # Test scroll down (direction < 0) - should work if not at bottom
        assert ScrollView._can_scroll(-1, True, 200, 500, -100) is True
        assert ScrollView._can_scroll(-1, True, 200, 500, -300) is False  # At bottom

        # Test with scroll disabled
        assert ScrollView._can_scroll(1, False, 200, 500, -100) is False

    @pytest.mark.win_params({"width": 200, "height": 150})
    def test_content_position_bounds_correction(self, fake_win):
        """Test automatic correction of invalid content positions"""
        items = [Text(f"Item {i}", size=16) for i in range(10)]
        content = Column(items)
        scroll = ScrollView(content)
        fake_win.controls = [scroll]
        fake_win.render()

        # Manually set invalid positions
        scroll._content_x = 100  # Positive (invalid)
        scroll._content_y = 50  # Positive (invalid)
        scroll.update()

        # Re-render should correct positions
        fake_win.render()

        # Positions should be corrected to valid ranges
        assert scroll._content_x <= 0
        assert scroll._content_y <= 0
