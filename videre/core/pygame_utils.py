from dataclasses import dataclass

import pygame

Color = pygame.Color
Surface = pygame.Surface
Event = pygame.event.Event


class PygameUtils:
    __slots__ = ()

    def __init__(self):
        # Init pygame here.
        pygame.init()

    @classmethod
    def new_surface(cls, width: int | float, height: int | float) -> Surface:
        return Surface((width, height), flags=pygame.SRCALPHA)


@dataclass(slots=True, frozen=True)
class PygameRendered:
    surface: Surface
