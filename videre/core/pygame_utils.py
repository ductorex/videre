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
    def new_surface(cls, width: int, height: int) -> Surface:
        return Surface((width, height), flags=pygame.SRCALPHA)
