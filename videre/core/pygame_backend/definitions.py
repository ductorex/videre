from dataclasses import dataclass

import pygame.event

from videre.colors import Color
from videre.core.rendering_result import Rendering

Surface = pygame.Surface
Rect = pygame.Rect
Event = pygame.event.Event
PygameColor = pygame.Color


@dataclass(frozen=True, slots=True)
class PygameRendering(Rendering):
    surface: Surface

    def get_width(self) -> int:
        return self.surface.get_width()

    def get_height(self) -> int:
        return self.surface.get_height()

    def get_at(self, position: tuple[int, int]) -> Color:
        color = self.surface.get_at(position)
        return Color(color.r, color.g, color.b, color.a)
