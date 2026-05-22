import pygame

from videre.core.pygame_backend.definitions import Surface
from videre.core.pygame_backend.font_factory import PygameFontFactory
from videre.core.pygame_backend.primitives import Pygame
from videre.core.pygame_backend.text_rendering import PygameTextRendering


class PygameBackend(Pygame):
    __slots__ = (
        "__default_cursor",
        "__text_cursor",
        "_title",
        "_hide",
        "_width",
        "_height",
        "_screen",
        "_fonts",
    )

    def __init__(self, width: int, height: int, title: str, hide: bool = False) -> None:
        # Init pygame here.
        pygame.init()

        self.__default_cursor = pygame.mouse.get_cursor()
        self.__text_cursor = pygame.cursors.compile(pygame.cursors.textmarker_strings)
        self._fonts = PygameFontFactory()
        self._width = width
        self._height = height
        self._title = title
        self._hide = hide
        self._screen: Surface | None = None

    def get_screen(self) -> Surface:
        assert self._screen is not None
        return self._screen

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, width: int) -> None:
        if self._screen is not None:
            assert self._screen.get_width() == width
        self._width = width

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, height: int) -> None:
        if self._screen is not None:
            assert self._screen.get_height() == height
        self._height = height

    @property
    def title(self) -> str:
        return self._title

    def set_text_cursor(self):
        pygame.mouse.set_cursor((8, 16), (0, 0), *self.__text_cursor)

    def set_default_cursor(self):
        pygame.mouse.set_cursor(*self.__default_cursor)

    def cursor_is_default(self) -> bool:
        return pygame.mouse.get_cursor() == self.__default_cursor

    def __enter__(self):
        flags = pygame.RESIZABLE
        if self._hide:
            flags |= pygame.HIDDEN
        self._screen = pygame.display.set_mode((self._width, self._height), flags=flags)
        pygame.display.set_caption(self._title)

        # Initialize keyboard repeat.
        # NB: TEXTINPUT events already handle repeat,
        # but we still need manual initialization for KEYDOWN/KEYUP events.
        # I don't know how to get default delay and interval values for TEXTINPUT,
        # so I tried here to set empiric values so that key repeat
        # is the most like textinput repeat.
        pygame.key.set_repeat(500, 35)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pygame.quit()

    def text_rendering(
        self,
        size: int,
        strong: bool = False,
        italic: bool = False,
        underline: bool = False,
        height_delta: int | None = None,
    ) -> PygameTextRendering:
        return PygameTextRendering(
            self._fonts,
            size=size,
            strong=strong,
            italic=italic,
            underline=underline,
            height_delta=height_delta,
        )
