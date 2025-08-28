from fontTools.ttLib import TTFont

from videre.fonts import FONT_NOTO_REGULAR

import pygame
import pygame.freetype


def main():
    char = "x"
    # For now, let's assume font size in Pygame is passed as points.
    size_points = 14
    pygame.init()
    pygame_font = pygame.freetype.Font(FONT_NOTO_REGULAR.path, size=size_points)
    resolution = pygame_font.resolution  # value: 72
    size_pixels = size_points * resolution / 72  # value: 14
    print("Pygame resolution", resolution)
    print("Pygame size (point?)", pygame_font.size)
    print("Pygame size (pixels?)", size_pixels)
    (metrics,) = pygame_font.get_metrics(char, size=size_points)
    if metrics:
        print(f"Advance for {char}:", metrics[4])  # value: 9.0
    else:
        print(f"No advance for {char}")
    bounds = pygame_font.get_rect(char, size=size_points)
    print("Bounds", bounds)

    with TTFont(FONT_NOTO_REGULAR.path) as font:
        units_per_em = font["head"].unitsPerEm
        print("Units per em:", units_per_em)  # value: 1000
        glyph_set = font.getGlyphSet()
        glyph = glyph_set[char]
        width_raw = glyph.width  # value: 639
        width_px = glyph.width * size_pixels / units_per_em  # value: 8.946
        print(f"TTFont advance for {char} (raw):", width_raw)
        print(f"TTFont advance for {char} (pixels):", width_px)


if __name__ == "__main__":
    main()
