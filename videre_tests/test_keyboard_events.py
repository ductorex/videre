import pygame

from videre.core.constants import MouseButton
from videre.core.events import KeyboardEntry, MouseEvent


class TestKeyboardEntry:
    """Test keyboard event handling and modifier properties"""

    def test_modifier_properties_lshift_rctrl_lalt(self):
        """Test keyboard modifier properties with left shift, right ctrl, left alt"""
        mock_event = pygame.event.Event(
            pygame.KEYDOWN,
            {
                "mod": pygame.KMOD_LSHIFT | pygame.KMOD_RCTRL | pygame.KMOD_LALT,
                "key": pygame.K_a,
                "unicode": "a",
            },
        )

        entry = KeyboardEntry(mock_event)

        # Test individual modifier properties
        assert entry.lshift > 0
        assert entry.rshift == 0
        assert entry.lctrl == 0
        assert entry.rctrl > 0
        assert entry.lalt > 0
        assert entry.ralt == 0

        # Test combined properties
        assert entry.shift > 0
        assert entry.ctrl > 0
        assert entry.alt > 0
        assert entry.caps == 0

    def test_modifier_properties_rshift_lctrl_ralt_caps(self):
        """Test keyboard modifier properties with right shift, left ctrl, right alt, caps"""
        mock_event = pygame.event.Event(
            pygame.KEYDOWN,
            {
                "mod": pygame.KMOD_RSHIFT
                | pygame.KMOD_LCTRL
                | pygame.KMOD_RALT
                | pygame.KMOD_CAPS,
                "key": pygame.K_b,
                "unicode": "B",
            },
        )

        entry = KeyboardEntry(mock_event)

        # Test individual modifier properties
        assert entry.lshift == 0
        assert entry.rshift > 0
        assert entry.lctrl > 0
        assert entry.rctrl == 0
        assert entry.lalt == 0
        assert entry.ralt > 0

        # Test combined properties
        assert entry.shift > 0
        assert entry.ctrl > 0
        assert entry.alt > 0
        assert entry.caps > 0

    def test_special_keys(self):
        """Test special keys"""
        navigation_keys = [
            (pygame.K_UP, "up"),
            (pygame.K_DOWN, "down"),
            (pygame.K_LEFT, "left"),
            (pygame.K_RIGHT, "right"),
            (pygame.K_HOME, "home"),
            (pygame.K_END, "end"),
            (pygame.K_PAGEUP, "pageup"),
            (pygame.K_PAGEDOWN, "pagedown"),
            (pygame.K_BACKSPACE, "backspace"),
            (pygame.K_DELETE, "delete"),
            (pygame.K_TAB, "tab"),
            (pygame.K_RETURN, "enter"),
            (pygame.K_ESCAPE, "escape"),
            (pygame.K_PRINTSCREEN, "printscreen"),
            (pygame.K_a, "a"),
            (pygame.K_c, "c"),
            (pygame.K_v, "v"),
        ]

        various_prop_names = [prop_name for _, prop_name in navigation_keys]

        for key_code, prop_name in navigation_keys:
            mock_event = pygame.event.Event(
                pygame.KEYUP, {"mod": 0, "key": key_code, "unicode": ""}
            )

            entry = KeyboardEntry(mock_event)
            assert getattr(entry, prop_name) is True
            for other_prop in various_prop_names:
                if other_prop != prop_name:
                    assert getattr(entry, other_prop) is False

    def test_keyboard_entry_repr_no_modifiers(self):
        """Test KeyboardEntry string representation with no modifiers"""
        mock_event = pygame.event.Event(
            pygame.KEYDOWN, {"mod": 0, "key": pygame.K_a, "unicode": "a"}
        )

        entry = KeyboardEntry(mock_event)
        assert repr(entry) == ""

    def test_keyboard_entry_repr_with_modifiers(self):
        """Test KeyboardEntry string representation with modifiers"""
        mock_event = pygame.event.Event(
            pygame.KEYDOWN,
            {
                "mod": pygame.KMOD_CTRL | pygame.KMOD_SHIFT,
                "key": pygame.K_c,
                "unicode": "C",
            },
        )

        entry = KeyboardEntry(mock_event)
        repr_str = repr(entry)
        # Should contain both ctrl and shift, order may vary
        assert "ctrl" in repr_str
        assert "shift" in repr_str
        assert " + " in repr_str


class TestMouseEventButtonProperties:
    """Test MouseEvent button detection properties"""

    def test_button_left_only(self):
        """Test MouseEvent with only left button pressed"""
        event = MouseEvent(buttons=[MouseButton.BUTTON_LEFT])
        assert event.button_left is True
        assert event.button_middle is False
        assert event.button_right is False

    def test_button_middle_only(self):
        """Test MouseEvent with only middle button pressed"""
        event = MouseEvent(buttons=[MouseButton.BUTTON_MIDDLE])
        assert event.button_left is False
        assert event.button_middle is True
        assert event.button_right is False

    def test_button_right_only(self):
        """Test MouseEvent with only right button pressed"""
        event = MouseEvent(buttons=[MouseButton.BUTTON_RIGHT])
        assert event.button_left is False
        assert event.button_middle is False
        assert event.button_right is True

    def test_multiple_buttons_left_right(self):
        """Test MouseEvent with multiple buttons pressed"""
        event = MouseEvent(buttons=[MouseButton.BUTTON_LEFT, MouseButton.BUTTON_RIGHT])
        assert event.button_left is True
        assert event.button_right is True
        assert event.button_middle is False

    def test_multiple_buttons_all_three(self):
        """Test MouseEvent with all three buttons pressed"""
        event = MouseEvent(
            buttons=[
                MouseButton.BUTTON_LEFT,
                MouseButton.BUTTON_MIDDLE,
                MouseButton.BUTTON_RIGHT,
            ]
        )
        assert event.button_left is True
        assert event.button_middle is True
        assert event.button_right is True

    def test_from_mouse_motion_with_buttons(self):
        """Test MouseEvent.from_mouse_motion with various button combinations"""
        # Mock pygame event with buttons pressed
        mock_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {
                "buttons": (1, 0, 1),  # Left and right buttons pressed
                "pos": (100, 200),
                "rel": (5, -3),
            },
        )

        event = MouseEvent.from_mouse_motion(mock_event)

        assert event.x == 100
        assert event.y == 200
        assert event.dx == 5
        assert event.dy == -3
        assert event.button_left is True
        assert event.button_middle is False
        assert event.button_right is True

    def test_from_mouse_motion_no_buttons(self):
        """Test MouseEvent.from_mouse_motion with no buttons pressed"""
        mock_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {
                "buttons": (0, 0, 0),  # No buttons pressed
                "pos": (50, 75),
                "rel": (0, 0),
            },
        )

        event = MouseEvent.from_mouse_motion(mock_event)

        assert event.x == 50
        assert event.y == 75
        assert event.dx == 0
        assert event.dy == 0
        assert event.button_left is False
        assert event.button_middle is False
        assert event.button_right is False

    def test_from_mouse_motion_with_custom_coordinates(self):
        """Test MouseEvent.from_mouse_motion with custom x,y coordinates"""
        mock_event = pygame.event.Event(
            pygame.MOUSEMOTION,
            {
                "buttons": (0, 1, 0),  # Middle button pressed
                "pos": (100, 200),
                "rel": (10, -5),
            },
        )

        event = MouseEvent.from_mouse_motion(mock_event, x=300, y=400)

        # Custom coordinates should override event.pos
        assert event.x == 300
        assert event.y == 400
        assert event.dx == 10
        assert event.dy == -5
        assert event.button_left is False
        assert event.button_middle is True
        assert event.button_right is False

    def test_with_coordinates_method(self):
        """Test MouseEvent.with_coordinates method"""
        original_event = MouseEvent(
            x=10,
            y=20,
            dx=5,
            dy=-3,
            buttons=[MouseButton.BUTTON_LEFT, MouseButton.BUTTON_MIDDLE],
        )

        new_event = original_event.with_coordinates(100, 200)

        # New coordinates should be set
        assert new_event.x == 100
        assert new_event.y == 200
        # Deltas and buttons should be preserved
        assert new_event.dx == 5
        assert new_event.dy == -3
        assert new_event.button_left is True
        assert new_event.button_middle is True
        assert new_event.button_right is False

        # Original event should be unchanged
        assert original_event.x == 10
        assert original_event.y == 20
