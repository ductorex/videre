from enum import Enum, unique

import pygame


@unique
class MouseButton(Enum):
    BUTTON_LEFT = pygame.BUTTON_LEFT
    BUTTON_MIDDLE = pygame.BUTTON_MIDDLE
    BUTTON_RIGHT = pygame.BUTTON_RIGHT
    BUTTON_WHEELDOWN = pygame.BUTTON_WHEELDOWN
    BUTTON_WHEELUP = pygame.BUTTON_WHEELUP
    BUTTON_X1 = pygame.BUTTON_X1
    BUTTON_X2 = pygame.BUTTON_X2


@unique
class TextWrap(Enum):
    NONE = 0
    CHAR = 1
    WORD = 2
    # WORD_THEN_CHAR = 3  # todo


@unique
class TextAlign(Enum):
    NONE = 0
    LEFT = 1
    CENTER = 2
    RIGHT = 3
    JUSTIFY = 4


@unique
class Alignment(Enum):
    START = 0
    CENTER = 1
    END = 2


@unique
class Side(Enum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"


WINDOW_FPS = 60
