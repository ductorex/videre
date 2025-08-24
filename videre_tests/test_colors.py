import pygame
import pytest

from videre.colors import Colors, parse_color, stringify_color


def test_parse_color():
    with pytest.raises(ValueError, match="Color tuple/list must have 3 or 4 values"):
        assert parse_color([])
    with pytest.raises(ValueError, match="Color tuple/list must have 3 or 4 values"):
        assert parse_color((1, 2))
    with pytest.raises(ValueError, match="Unsupported color definition: int"):
        assert parse_color(1)
    with pytest.raises(ValueError, match="Unknown color name: batman"):
        assert parse_color("batman")
    with pytest.raises(
        ValueError, match="Too long color hex \(at most 8 digits expected\)"
    ):
        assert parse_color("#abcdef01c")
    with pytest.raises(ValueError, match="Expected a non-empty string color"):
        parse_color("")

    assert parse_color((1, 2, 3)) == pygame.Color(1, 2, 3)
    assert parse_color([1, 2, 3]) == pygame.Color(1, 2, 3)

    assert parse_color((1, 2, 3, 227)) == pygame.Color(1, 2, 3, 227)
    assert parse_color([1, 2, 3, 227]) == pygame.Color(1, 2, 3, 227)

    color = pygame.Color(4, 5, 7, 11)
    assert parse_color(color) is color

    assert parse_color("green") == Colors.green

    assert parse_color("#2bffea") == pygame.Color(0x2B, 0xFF, 0xEA)
    assert parse_color("#2bffeadc") == pygame.Color(0x2B, 0xFF, 0xEA, 0xDC)
    assert parse_color("#2bffe") == pygame.Color(0x2, 0xBF, 0xFE)
    assert parse_color("#12c") == pygame.Color(0, 0x1, 0x2C)
    assert parse_color("#c") == pygame.Color(0, 0, 0xC)

    assert parse_color(None) == Colors.transparent


def test_stringify_color():
    assert stringify_color(pygame.Color(0, 0, 0, 0)) == "transparent"
    assert stringify_color(pygame.Color(0, 0, 0, 255)) == "black"
    assert stringify_color(pygame.Color(255, 255, 255, 255)) == "white"
    assert stringify_color(pygame.Color(255, 255, 255)) == "white"
    assert stringify_color(pygame.Color(255, 255, 254)) == "#fffffe"
    assert stringify_color(pygame.Color(255, 0xA4, 0xB9)) == "#ffa4b9"
