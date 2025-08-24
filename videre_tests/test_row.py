import pytest

import videre


@pytest.mark.parametrize(
    "alignment", [videre.Alignment.START, videre.Alignment.CENTER, videre.Alignment.END]
)
def test_row(alignment, fake_win):
    fake_win.controls = [
        videre.Row(
            [
                videre.Container(
                    width=50, height=100, background_color=videre.Colors.red
                ),
                videre.Container(
                    width=60, height=50, background_color=videre.Colors.green
                ),
                videre.Container(
                    width=70, height=80, background_color=videre.Colors.blue
                ),
            ],
            vertical_alignment=alignment,
        )
    ]
    fake_win.check()


class TestRowLayout:
    """Test Row layout edge cases and weight distribution"""

    def test_row_with_zero_weight_children(self, fake_win):
        """Test row layout with all children having zero weight"""
        items = [
            videre.Text("Item 1", weight=0),
            videre.Text("Item 2", weight=0),
            videre.Text("Item 3", weight=0),
        ]
        row = videre.Row(items)
        fake_win.controls = [row]
        fake_win.render()

        # Should handle gracefully without division by zero
        assert row.rendered_width > 0
        # All items should be rendered
        for item in items:
            assert item.rendered_width > 0

    def test_row_weight_distribution_edge_cases(self, fake_win):
        """Test row layout weight distribution in edge cases"""
        items = [
            videre.Container(weight=1),
            videre.Text("B", weight=0),
            videre.Container(weight=2),
        ]
        row = videre.Row(items)
        fake_win.controls = [row]
        fake_win.render()

        # Zero weight item should still get some minimum space
        assert items[0].rendered_width > 0
        assert items[1].rendered_width > 0
        assert items[2].rendered_width > 0

        # Weighted items should get proportional space
        # Item C (weight=2) should get more space than item A (weight=1)
        assert items[2].rendered_width >= 2 * items[0].rendered_width

    def test_row_single_child_zero_weight(self, fake_win):
        """Test row with single child having zero weight"""
        item = videre.Text("Single item", weight=0)
        row = videre.Row([item])
        fake_win.controls = [row]
        fake_win.render()

        # Should render without issues
        assert row.rendered_width > 0
        assert item.rendered_width > 0

    def test_row_empty_children_list(self, fake_win):
        """Test row with empty children list"""
        row = videre.Row([])
        fake_win.controls = [row]
        fake_win.render()

        # Should handle gracefully
        assert row.rendered_height == 0
        assert row.rendered_width == 0

    def test_row_very_large_weight_values(self, fake_win):
        """Test row with extremely large weight values"""
        items = [
            videre.Text("Weight 10000", weight=10000),
            videre.Text("Weight 20000", weight=20000),
            videre.Text("Weight 1", weight=1),
        ]
        row = videre.Row(items)
        fake_win.controls = [row]
        fake_win.render()

        # Should handle large weights without overflow issues
        assert row.rendered_width > 0
        for item in items:
            assert item.rendered_width > 0

    def test_row_vertical_alignment_edge_cases(self, fake_win):
        """Test row vertical alignment with varying child heights"""
        items = [
            videre.Container(width=20, height=10, background_color=videre.Colors.red),
            videre.Container(
                width=20, height=100, background_color=videre.Colors.green
            ),
            videre.Container(width=20, height=50, background_color=videre.Colors.blue),
        ]

        alignments = [
            videre.Alignment.START,
            videre.Alignment.CENTER,
            videre.Alignment.END,
        ]

        for alignment in alignments:
            row = videre.Row(items, vertical_alignment=alignment)
            fake_win.controls = [row]
            fake_win.check(f"vertical_alignment_{alignment}")

            # All items should be positioned within row bounds
            for item in items:
                assert item.y >= 0
                assert item.y + item.rendered_height <= row.rendered_height

    def test_row_mixed_weight_and_fixed_size_children(self, fake_win):
        """Test row with mix of weighted and fixed-size children"""
        items = [
            videre.Container(
                width=50, height=30, background_color=videre.Colors.red
            ),  # Fixed
            videre.Text("Flexible", weight=1),  # Weighted
            videre.Container(
                width=30, height=30, background_color=videre.Colors.blue
            ),  # Fixed
            videre.Text("Also flexible", weight=2),  # Weighted
        ]
        row = videre.Row(items)
        fake_win.controls = [row]
        fake_win.render()

        # Fixed-size items should keep their specified widths
        assert items[0].rendered_width == 50
        assert items[2].rendered_width == 30

        assert items[3].rendered_width > 0
        assert items[1].rendered_width > 0
        # Weighted items should share remaining space proportionally
        # Item with weight=2 should get more space than item with weight=1
        assert items[3].rendered_width >= items[1].rendered_width
