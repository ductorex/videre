from typing import Callable, Iterable


def on_event(event_type: int):
    """
    Generate a decorator to mark a function as an event manager for given event type.
    Used on Window's event handling methods.

    :param event_type: Pygame event type.
    :return: a decorator
    """

    def decorator(function):
        function.event_type = event_type
        return function

    return decorator


class OnEvent[K]:
    __slots__ = ("_callbacks",)

    def __init__(self) -> None:
        self._callbacks: dict[K, Callable] = {}

    def __call__(self, key: K):
        assert key not in self._callbacks

        def decorator(function):
            function.key = key
            self._callbacks[key] = function
            return function

        return decorator

    def __str__(self):
        return str({et: f.__name__ for et, f in self._callbacks.items()})

    def __len__(self):
        return len(self._callbacks)

    def __getitem__(self, key) -> Callable:
        return self._callbacks[key]

    def get(self, key: K) -> Callable | None:
        return self._callbacks.get(key, None)

    def keys(self) -> Iterable[K]:
        return self._callbacks.keys()

    def items(self) -> Iterable[tuple[K, Callable]]:
        return self._callbacks.items()


class WidgetByKeyGetter:
    __slots__ = ("key",)

    def __init__(self, key: str):
        self.key = key

    def __call__(self, widget) -> bool:
        return widget.key == self.key
