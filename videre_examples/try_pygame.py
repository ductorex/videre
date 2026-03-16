import pygame


class PygameContext:
    __slots__ = ()

    def __enter__(self):
        pygame.init()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pygame.quit()


def main():
    with PygameContext():
        surface = pygame.display.set_mode((300, 400), flags=pygame.HIDDEN)
        assert surface.get_width() == 300
        assert surface.get_height() == 400


if __name__ == "__main__":
    main()
