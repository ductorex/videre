from dataclasses import dataclass

import pygame

from videre.colors import Color

Surface = pygame.Surface
Event = pygame.event.Event


class Pygame:
    __slots__ = ()

    def __init__(self):
        # Init pygame here.
        pygame.init()

    @classmethod
    def new_surface(cls, width: int | float, height: int | float) -> Surface:
        return Surface((width, height), flags=pygame.SRCALPHA)

    @classmethod
    def zero(cls) -> Surface:
        return Surface((0, 0), flags=pygame.SRCALPHA)

    @classmethod
    def new_color(cls, color: Color) -> pygame.Color:
        return pygame.Color(color.r, color.g, color.b, color.a)


@dataclass(slots=True, frozen=True)
class PygameRendered:
    surface: Surface
