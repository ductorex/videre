import pytest

from videre.colors import Colors
from videre.core.constants import Side
from videre.core.sides.border import Border
from videre.core.sides.margin import Margin
from videre.core.sides.abstract_sides import AbstractSides


def test_border_all_1():
    b1 = Border.all(1)
    b2 = Border.axis(1, 1)
    b3 = Border.sides(1, Side.TOP, Side.LEFT, Side.BOTTOM, Side.RIGHT)
    b4 = Border(top=1, left=1, bottom=1, right=1)
    assert b1 == b2 == b3 == b4
    assert b1.top == b1.bottom == b1.left == b1.right
    assert b1.top.width == 1
    assert b2.top.color == Colors.black
    assert b1.margin() == Margin.all(1)

    w, h = 100, 50
    assert b1.get_top_points(w, h) == [(0, 0), (99, 0), (99, 0), (0, 0)]
    assert b1.get_right_points(w, h) == [(99, 0), (99, 49), (99, 49), (99, 0)]
    assert b1.get_bottom_points(w, h) == [(0, 49), (99, 49), (99, 49), (0, 49)]
    assert b1.get_left_points(w, h) == [(0, 0), (0, 49), (0, 49), (0, 0)]


def test_border_all_4():
    b = Border.all(4)

    w, h = 100, 50
    assert b.get_top_points(w, h) == [(0, 0), (99, 0), (96, 3), (3, 3)]
    assert b.get_right_points(w, h) == [(99, 0), (99, 49), (96, 46), (96, 3)]
    assert b.get_bottom_points(w, h) == [(0, 49), (99, 49), (96, 46), (3, 46)]
    assert b.get_left_points(w, h) == [(0, 0), (0, 49), (3, 46), (3, 3)]


def test_border_2_v_yellow_and_hash_border_side():
    b = Border.axis(vertical=(2, Colors.yellow))
    assert b.left.width == 0
    assert b.left.color == Colors.black
    assert b.right.width == 0
    assert b.right.color == Colors.black
    assert b.left == b.right
    assert hash(b.left) == hash(b.right)

    assert b.top.width == 2
    assert b.top.color == Colors.yellow
    assert b.bottom.width == 2
    assert b.bottom.color == Colors.yellow
    assert b.top == b.bottom
    assert hash(b.top) == hash(b.bottom)

    assert b.left != b.top
    assert hash(b.left) != hash(b.top)

    w, h = 100, 50
    assert b.get_left_points(w, h) == []
    assert b.get_right_points(w, h) == []
    assert b.get_top_points(w, h) == [(0, 0), (99, 0), (99, 1), (0, 1)]
    assert b.get_bottom_points(w, h) == [(0, 49), (99, 49), (99, 48), (0, 48)]


def test_border_2_h_yellow():
    b = Border.axis(horizontal=(2, Colors.yellow))
    assert b.top.width == 0
    assert b.top.color == Colors.black
    assert b.bottom.width == 0
    assert b.bottom.color == Colors.black
    assert b.left.width == 2
    assert b.left.color == Colors.yellow
    assert b.right.width == 2
    assert b.right.color == Colors.yellow

    w, h = 100, 50
    assert b.get_top_points(w, h) == []
    assert b.get_right_points(w, h) == [(99, 0), (99, 49), (98, 49), (98, 0)]
    assert b.get_bottom_points(w, h) == []
    assert b.get_left_points(w, h) == [(0, 0), (0, 49), (1, 49), (1, 0)]


def test_border():
    b = Border(top=4, right=5, bottom=6, left=7)

    w, h = 100, 50
    assert b.get_top_points(w, h) == [(0, 0), (99, 0), (95, 3), (6, 3)]
    assert b.get_right_points(w, h) == [(99, 0), (99, 49), (95, 44), (95, 3)]
    assert b.get_bottom_points(w, h) == [(0, 49), (99, 49), (95, 44), (6, 44)]
    assert b.get_left_points(w, h) == [(0, 0), (0, 49), (6, 44), (6, 3)]


def test_border_top_0():
    b = Border(top=0, right=5, bottom=6, left=7)

    w, h = 100, 50
    assert b.get_top_points(w, h) == []
    assert b.get_right_points(w, h) == [(99, 0), (99, 49), (95, 44), (95, 0)]
    assert b.get_bottom_points(w, h) == [(0, 49), (99, 49), (95, 44), (6, 44)]
    assert b.get_left_points(w, h) == [(0, 0), (0, 49), (6, 44), (6, 0)]


def test_border_right_0():
    b = Border(top=4, right=0, bottom=6, left=7)

    w, h = 100, 50
    assert b.get_top_points(w, h) == [(0, 0), (99, 0), (99, 3), (6, 3)]
    assert b.get_right_points(w, h) == []
    assert b.get_bottom_points(w, h) == [(0, 49), (99, 49), (99, 44), (6, 44)]
    assert b.get_left_points(w, h) == [(0, 0), (0, 49), (6, 44), (6, 3)]


def test_border_bottom_0():
    b = Border(top=4, right=5, bottom=0, left=7)

    w, h = 100, 50
    assert b.get_top_points(w, h) == [(0, 0), (99, 0), (95, 3), (6, 3)]
    assert b.get_right_points(w, h) == [(99, 0), (99, 49), (95, 49), (95, 3)]
    assert b.get_bottom_points(w, h) == []
    assert b.get_left_points(w, h) == [(0, 0), (0, 49), (6, 49), (6, 3)]


def test_border_left_0():
    b = Border(top=4, right=5, bottom=6, left=0)

    w, h = 100, 50
    assert b.get_top_points(w, h) == [(0, 0), (99, 0), (95, 3), (0, 3)]
    assert b.get_right_points(w, h) == [(99, 0), (99, 49), (95, 44), (95, 3)]
    assert b.get_bottom_points(w, h) == [(0, 49), (99, 49), (95, 44), (0, 44)]
    assert b.get_left_points(w, h) == []


def test_bad_border():
    with pytest.raises(ValueError, match="Unsupported border side value: ''"):
        Border(top="")


def test_margin():
    with pytest.raises(TypeError, match="Unsupported Margin value type: str"):
        Margin(top="")

    with pytest.raises(ValueError, match="Unsupported Margin value: -1"):
        Margin(top=-1)

    assert Margin(top=10).total() == 10

    m = Margin(top=1, right=2, bottom=3, left=4)
    assert m.total() == 10


def test_abstract_side():
    sides_1 = AbstractSides(bottom="hello")
    sides_2 = AbstractSides(bottom=3.4)
    sides_3 = AbstractSides(bottom="hello")

    assert sides_1 == sides_3
    assert {sides_1, sides_2, sides_3} == {sides_1, sides_2}
