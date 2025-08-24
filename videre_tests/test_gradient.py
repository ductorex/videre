import pygame
import pytest

from videre.colors import Colors
from videre.gradient import Gradient


def test_gradient_single_color():
    gradient = Gradient(Colors.red)
    surface = gradient.generate(100, 100)
    assert surface.get_width() == 100
    assert surface.get_height() == 100
    # Check that the entire surface is red
    for x in range(100):
        for y in range(100):
            assert surface.get_at((x, y)) == Colors.red


def test_gradient_horizontal():
    gradient = Gradient(Colors.red, Colors.blue, vertical=False)
    surface = gradient.generate(100, 50)
    assert surface.get_width() == 100
    assert surface.get_height() == 50
    # Check colors at extremities
    assert surface.get_at((0, 0)) == Colors.red
    assert surface.get_at((99, 0)) == Colors.blue


def test_gradient_vertical():
    gradient = Gradient(Colors.red, Colors.blue, vertical=True)
    surface = gradient.generate(50, 100)
    assert surface.get_width() == 50
    assert surface.get_height() == 100
    # Check colors at extremities
    assert surface.get_at((0, 0)) == Colors.red
    assert surface.get_at((0, 99)) == Colors.blue


def test_gradient_multiple_colors():
    gradient = Gradient(Colors.red, Colors.green, Colors.blue)
    surface = gradient.generate(101, 50)
    assert surface.get_width() == 101
    assert surface.get_height() == 50
    # Check colors at transition points
    assert surface.get_at((0, 0)) == Colors.red
    assert surface.get_at((50, 0)) == Colors.green
    assert surface.get_at((100, 0)) == Colors.blue


def test_gradient_parse():
    # Test with a color
    gradient = Gradient.parse(Colors.red)
    assert isinstance(gradient, Gradient)
    assert len(gradient._colors) == 1
    assert gradient._colors[0] == Colors.red

    # Test with an existing gradient
    original_gradient = Gradient(Colors.red, Colors.blue)
    parsed_gradient = Gradient.parse(original_gradient)
    assert parsed_gradient is original_gradient

    # Test with a color string
    gradient = Gradient.parse("red")
    assert isinstance(gradient, Gradient)
    assert len(gradient._colors) == 1
    assert gradient._colors[0] == Colors.red


def test_gradient_empty():
    gradient = Gradient()
    assert len(gradient._colors) == 1
    assert gradient._colors[0] == Colors.transparent


def test_gradient_surface_reuse():
    gradient = Gradient(Colors.red, Colors.blue)
    surface1 = gradient.generate(100, 100)
    surface2 = gradient.generate(100, 100)
    # Check that surfaces are different (no shared reference)
    assert surface1 is not surface2
    # Check that surfaces have the same content
    for x in range(100):
        for y in range(100):
            assert surface1.get_at((x, y)) == surface2.get_at((x, y))


def test_gradient_edge_cases():
    # Test 1x1 surface
    gradient = Gradient(Colors.red, Colors.blue)
    surface = gradient.generate(1, 1)
    assert surface.get_width() == 1
    assert surface.get_height() == 1
    assert surface.get_at((0, 0)) == Colors.red

    # Test with very large dimensions
    surface = gradient.generate(1000, 1000)
    assert surface.get_width() == 1000
    assert surface.get_height() == 1000
    # Check start and end colors
    assert surface.get_at((0, 0)) == Colors.red
    assert surface.get_at((999, 999)) == Colors.blue


def test_gradient_color_interpolation():
    gradient = Gradient(Colors.red, Colors.blue)
    surface = gradient.generate(100, 1)

    # Check middle point interpolation
    middle_color = surface.get_at((49, 0))
    # red should go from 255 to 0, blue should go from 0 to 255
    assert Colors.red.r > middle_color.r > Colors.blue.r
    assert Colors.red.b < middle_color.b < Colors.blue.b

    # Test with transparent colors
    transparent_gradient = Gradient(Colors.transparent, Colors.red)
    surface = transparent_gradient.generate(100, 1)
    assert surface.get_at((0, 0)) == Colors.transparent
    assert surface.get_at((99, 0)) == Colors.red


def test_gradient_error_cases():
    gradient = Gradient(Colors.red, Colors.blue)

    # Test with negative dimensions
    with pytest.raises(pygame.error):
        gradient.generate(-1, 100)

    with pytest.raises(pygame.error):
        gradient.generate(100, -1)

    # zero-dimensions are supported
    surface = gradient.generate(0, 100)
    assert surface.get_width() == 0
    assert surface.get_height() == 100

    surface = gradient.generate(100, 0)
    assert surface.get_width() == 100
    assert surface.get_height() == 0


def test_gradient_similar_colors():
    # Test with very similar colors
    similar_gradient = Gradient(Colors.red, pygame.Color(255, 0, 1))
    surface = similar_gradient.generate(100, 1)

    # Check that interpolation is still working
    middle_color = surface.get_at((49, 0))
    assert middle_color.r == 255  # Red component should stay at max
    assert middle_color.g == 0  # Green component should stay at min
    assert middle_color.b in (0, 1)  # Blue component should interpolate between 0 and 1
