import threading
from typing import Any, Callable


def launch_thread(function, *args, **kwargs):
    thread = threading.Thread(
        target=function, args=args, kwargs=kwargs, name=function.__name__
    )
    thread.start()
    return thread


class OnClick:
    __slots__ = ("_procedure",)

    def __init__(self, procedure: Callable[[], None] | None = None):
        self._procedure = procedure

    def __call__(self, *args, **kwargs):
        if self._procedure is not None:
            self._procedure()


class Procedure:
    __slots__ = ("_fn", "_args", "_kwargs")

    def __init__(self, fn: Callable, *args, **kwargs):
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def __call__(self, *args, **kwargs) -> Any:
        # args and kwargs are ignored
        return self._fn(*self._args, **self._kwargs)
