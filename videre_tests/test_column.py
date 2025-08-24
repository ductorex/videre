import pytest

import videre


@pytest.mark.parametrize(
    "alignment", [videre.Alignment.START, videre.Alignment.CENTER, videre.Alignment.END]
)
def test_column(alignment, fake_win):
    fake_win.controls = [
        videre.Column(
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
            horizontal_alignment=alignment,
        )
    ]
    fake_win.check()


class TestColumnLayout:
    """Test Column layout edge cases and weight distribution"""

    def test_column_with_zero_weight_children(self, fake_win):
        """Test column layout with all children having zero weight"""
        items = [
            videre.Text("Item 1", weight=0),
            videre.Text("Item 2", weight=0),
            videre.Text("Item 3", weight=0),
        ]
        column = videre.Column(items)
        fake_win.controls = [column]
        fake_win.render()

        # Should handle gracefully without division by zero
        assert column.rendered_height > 0
        # All items should be rendered
        for item in items:
            assert item.rendered_height > 0

    def test_column_mixed_weight_distribution(self, fake_win):
        """Test column layout with mixed weight values including zero"""
        items = [
            videre.Text("Item 0", weight=0),
            videre.Container(weight=1),
            videre.Container(weight=2),
            videre.Text("Item 3", weight=0),
        ]
        column = videre.Column(items)
        fake_win.controls = [column]
        fake_win.render()

        # Zero weight items should still get some space
        assert items[0].rendered_height > 0
        assert items[1].rendered_height > 0
        assert items[2].rendered_height > 0
        assert items[3].rendered_height > 0

        # Weighted items should get proportional space
        # Item with weight=2 should get more space than item with weight=1
        assert items[2].rendered_height >= 2 * items[1].rendered_height

    def test_column_single_child_zero_weight(self, fake_win):
        """Test column with single child having zero weight"""
        item = videre.Text("Single item", weight=0)
        column = videre.Column([item])
        fake_win.controls = [column]
        fake_win.render()

        # Should render without issues
        assert column.rendered_height > 0
        assert item.rendered_height > 0

    def test_column_empty_children_list(self, fake_win):
        """Test column with empty children list"""
        column = videre.Column([])
        fake_win.controls = [column]
        fake_win.render()

        # Should handle gracefully
        assert column.rendered_height == 0
        assert column.rendered_width == 0

    def test_column_large_weight_values(self, fake_win):
        """Test column with very large weight values"""
        items = [
            videre.Text("Large weight 1", weight=1000),
            videre.Text("Large weight 2", weight=2000),
            videre.Text("Small weight", weight=1),
        ]
        column = videre.Column(items)
        fake_win.controls = [column]
        fake_win.render()

        # Should handle large weights without overflow issues
        assert column.rendered_height > 0
        for item in items:
            assert item.rendered_height > 0

    def test_column_horizontal_alignment_edge_cases(self, fake_win):
        """Test column horizontal alignment with varying child widths"""
        items = [
            videre.Container(width=10, height=20, background_color=videre.Colors.red),
            videre.Container(
                width=100, height=20, background_color=videre.Colors.green
            ),
            videre.Container(width=50, height=20, background_color=videre.Colors.blue),
        ]

        alignments = [
            videre.Alignment.START,
            videre.Alignment.CENTER,
            videre.Alignment.END,
        ]

        for alignment in alignments:
            column = videre.Column(items, horizontal_alignment=alignment)
            fake_win.controls = [column]
            fake_win.check(f"alignment_{alignment}")

            # All items should be positioned within column bounds
            for item in items:
                assert item.x >= 0
                assert item.x + item.rendered_width <= column.rendered_width
