import threading
from typing import Callable


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
