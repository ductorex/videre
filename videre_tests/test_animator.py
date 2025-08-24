import time
from types import SimpleNamespace

import videre


def test_animator_display(snap_win):
    text = videre.Text("Frame 0")
    animator = videre.Animator(text, fps=60)
    snap_win.controls = [animator]


def test_animator_frame_callback(fake_win):
    data = SimpleNamespace(frames=[], control_refs=[])

    def on_frame(control, frame_rank):
        data.frames.append(frame_rank)
        data.control_refs.append(control)

    text = videre.Text("Test")
    animator = videre.Animator(text, on_frame=on_frame, fps=60)
    fake_win.controls = [animator]

    assert animator.frame_rank == 0
    assert len(data.frames) == 0

    # Initial render
    fake_win.render()

    # Simulate frame updates by calling render() multiple times
    # This will trigger _check_fps and potentially increment frames
    for _ in range(10):
        time.sleep(0.01)
        fake_win.render()

    # At least one frame should have been processed
    assert animator.frame_rank >= 1
    assert len(data.frames) >= 1
    assert all(control is text for control in data.control_refs)


def test_animator_control_property(fake_win):
    text1 = videre.Text("Control 1")
    text2 = videre.Text("Control 2")

    animator = videre.Animator(text1, fps=30)
    fake_win.controls = [animator]
    fake_win.render()

    assert animator.control is text1

    # Change control
    animator.control = text2
    fake_win.render()

    assert animator.control is text2


def test_animator_fps_bounds(fake_win):
    text = videre.Text("Test")

    # Test negative fps
    animator1 = videre.Animator(text, fps=-10)
    assert animator1._fps == 0

    # Test very high fps (should be clamped to WINDOW_FPS)
    animator2 = videre.Animator(text, fps=1000)
    # Should be clamped to WINDOW_FPS (typically 60)
    assert animator2._fps <= 60

    # Test normal fps
    animator3 = videre.Animator(text, fps=30)
    assert animator3._fps == 30


def test_animator_on_frame_change(fake_win):
    data = SimpleNamespace(callback1_calls=0, callback2_calls=0)

    def callback1(control, frame_rank):
        data.callback1_calls += 1

    def callback2(control, frame_rank):
        data.callback2_calls += 1

    text = videre.Text("Test")
    animator = videre.Animator(text, on_frame=callback1, fps=60)
    fake_win.controls = [animator]
    fake_win.render()

    # Force a frame update
    time.sleep(0.1)
    fake_win.render()

    assert data.callback1_calls > 1
    assert data.callback2_calls == 0

    # Change callback
    animator.on_frame = callback2
    fake_win.render()

    # Force another frame update
    time.sleep(0.1)
    fake_win.render()

    assert data.callback1_calls > 1
    assert data.callback2_calls > 1


def test_animator_no_callback(fake_win):
    text = videre.Text("Test")
    animator = videre.Animator(text, on_frame=None, fps=60)
    fake_win.controls = [animator]

    # Should not crash without callback
    fake_win.render()

    time.sleep(0.1)
    fake_win.render()


class TestAbstractAnimation:
    """Test AbstractAnimation functionality and edge cases"""

    def test_fps_framing_zero_fps(self):
        """Test FPS framing with zero fps"""
        from videre.widgets.abstractanimation import FPS

        fps_framing = FPS(0)
        assert fps_framing._fps == 0
        assert fps_framing._delay_ms == float("inf")

    def test_fps_framing_negative_fps(self):
        """Test FPS framing with negative fps"""
        from videre.widgets.abstractanimation import FPS

        fps_framing = FPS(-10)
        assert fps_framing._fps == 0  # Should be clamped to 0

    def test_fps_framing_very_high_fps(self):
        """Test FPS framing with fps higher than WINDOW_FPS"""
        from videre.widgets.abstractanimation import FPS

        fps_framing = FPS(1000)
        assert fps_framing._fps <= videre.WINDOW_FPS  # Should be clamped

    def test_fpr_framing_zero_frames(self):
        """Test FPR framing with zero frames"""
        from videre.widgets.abstractanimation import FPR

        fpr_framing = FPR(0)
        assert fpr_framing._nb_frames == 1  # Should be clamped to minimum 1

    def test_fpr_framing_negative_frames(self):
        """Test FPR framing with negative frames"""
        from videre.widgets.abstractanimation import FPR

        fpr_framing = FPR(-5)
        assert fpr_framing._nb_frames == 1  # Should be clamped to minimum 1

    def test_fpr_framing_needs_frame_logic(self):
        """Test FPR framing needs_frame logic"""
        from videre.widgets.abstractanimation import FPR

        fpr_framing = FPR(3)

        # First call with window frame 0
        assert fpr_framing.needs_frame(0) is False  # (0+1) % 3 = 1, not 0

        # Same window frame should return False
        assert fpr_framing.needs_frame(1) is False

        # New window frame
        assert fpr_framing.needs_frame(2) is True  # (2+1) % 3 = 0

        # Same window frame should return False again
        assert fpr_framing.needs_frame(2) is False

    def test_fpr_framing_sequence(self):
        """Test FPR framing sequence over multiple frames"""
        from videre.widgets.abstractanimation import FPR

        fpr_framing = FPR(4)  # Every 4 frames

        expected_results = [False, False, False, True, False, False, False, True]
        for i, expected in enumerate(expected_results):
            result = fpr_framing.needs_frame(i)
            assert result is expected, f"Frame {i}: expected {expected}, got {result}"

    def test_fps_framing_needs_frame_timing(self):
        """Test FPS framing timing behavior"""
        from videre.widgets.abstractanimation import FPS

        # Very low fps should rarely need frames
        fps_framing = FPS(1)  # 1 frame per second

        # Multiple quick calls should not all return True
        results = []
        for _ in range(10):
            results.append(fps_framing.needs_frame(0))
            time.sleep(0.01)  # 10ms sleep

        # Not all should be True for 1 FPS with short intervals
        assert not all(results), "1 FPS should not need frames on every quick check"

    def test_abstract_animation_frame_counting(self, fake_win):
        """Test AbstractAnimation frame counting"""
        from videre.widgets.abstractanimation import AbstractAnimation, FPS

        class TestAnimation(AbstractAnimation):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.frame_calls = 0

            def _on_frame(self):
                self.frame_calls += 1

            def draw(self, window, view_width=None, view_height=None):
                # Simple implementation for testing
                import pygame

                surface = pygame.Surface((100, 50))
                surface.fill((255, 255, 255))
                return surface

        animation = TestAnimation(framing=FPS(30))  # 30 FPS
        fake_win.controls = [animation]

        # Initial state
        assert animation._nb_frames == 0
        assert animation.frame_calls == 0

        # First render
        fake_win.render()

        # Allow some frames to process
        for _ in range(5):
            time.sleep(0.05)  # 50ms
            fake_win.render()

        # Should have processed some frames
        assert animation._nb_frames > 0
        assert animation.frame_calls > 0
        assert animation._nb_frames == animation.frame_calls

    def test_abstract_animation_default_framing(self, fake_win):
        """Test AbstractAnimation with default FPS framing"""
        from videre.widgets.abstractanimation import AbstractAnimation, FPS

        class TestAnimation(AbstractAnimation):
            def _on_frame(self):
                pass

            def draw(self, window, view_width=None, view_height=None):
                import pygame

                return pygame.Surface((50, 50))

        # No framing specified should use default FPS
        animation = TestAnimation()
        assert isinstance(animation._framing, FPS)

        fake_win.controls = [animation]
        fake_win.render()  # Should not crash

    def test_abstract_animation_custom_framing(self, fake_win):
        """Test AbstractAnimation with custom FPR framing"""
        from videre.widgets.abstractanimation import AbstractAnimation, FPR

        class TestAnimation(AbstractAnimation):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.frame_calls = 0

            def _on_frame(self):
                self.frame_calls += 1

            def draw(self, window, view_width=None, view_height=None):
                import pygame

                return pygame.Surface((50, 50))

        # Use FPR framing - every 2 window frames
        animation = TestAnimation(framing=FPR(2))
        fake_win.controls = [animation]

        # Process multiple renders
        for i in range(6):
            fake_win.render()

        # With FPR(2), should have some frames but not one per render
        assert animation.frame_calls > 0
        assert animation.frame_calls < 6  # Should be less than total renders

        # Specifically, with 6 renders and FPR(2), should have 3 frames
        assert animation.frame_calls == animation._nb_frames == 3
