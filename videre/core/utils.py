import threading
from typing import Any, Callable, Iterable

from videre.core.events import VidereTask


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
        return str(
            {et: getattr(f, "__name__", str(f)) for et, f in self._callbacks.items()}
        )

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


class TaskManager:
    def __init__(self, on_task: Callable[[VidereTask], None]):
        self._on_task = on_task
        self._lock = threading.Lock()
        self._pending_tasks: list[VidereTask] = []

    def post_task(self, task: VidereTask):
        with self._lock:
            self._pending_tasks.append(task)

    def _flush_tasks(self) -> list[VidereTask]:
        with self._lock:
            tasks = self._pending_tasks
            self._pending_tasks = []
        return tasks

    def manage_tasks(self) -> None:
        for task in self._flush_tasks():
            self._on_task(task)

    def one_shot(self, task: VidereTask) -> None:
        self._on_task(task)
