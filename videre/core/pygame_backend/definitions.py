from dataclasses import dataclass

import pygame.event

Surface = pygame.Surface
Rect = pygame.Rect
Event = pygame.event.Event
PygameColor = pygame.Color


@dataclass(slots=True, frozen=True)
class PygameRendered:
    surface: Surface
