import pygame

from videre.core.drawer import Color as DrawerColor

Surface = pygame.Surface
Event = pygame.event.Event


def to_drawer_color(c: pygame.Color) -> DrawerColor:
    return DrawerColor(c.r, c.g, c.b, c.a)


def from_drawer_color(color: DrawerColor) -> pygame.Color:
    return pygame.Color(color.r, color.g, color.b, color.a)


class PygameUtils:
    __slots__ = ()

    def __init__(self):
        # Init pygame here.
        pygame.init()

    @classmethod
    def new_surface(cls, width: int | float, height: int | float) -> Surface:
        return Surface((width, height), flags=pygame.SRCALPHA)
