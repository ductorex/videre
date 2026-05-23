import threading
from dataclasses import dataclass
from typing import Any, Callable, Sequence, TypeAlias

NotificationCallback: TypeAlias = Callable[[Any], None]


@dataclass(slots=True, frozen=True)
class CallbackTask:
    function: Callable
    args: tuple
    kwargs: dict

    @classmethod
    def new(cls, function, *args, **kwargs) -> "CallbackTask":
        return CallbackTask(function, args, kwargs)

    def run(self):
        self.function(*self.args, **self.kwargs)


@dataclass(slots=True, frozen=True)
class NotificationTask:
    notification: Any

    def dispatch(self, callbacks: Sequence[NotificationCallback]):
        for callback in callbacks:
            callback(self.notification)


@dataclass(slots=True, frozen=True)
class ExitTask:
    exception: Exception | None = None


VidereTask: TypeAlias = CallbackTask | NotificationTask | ExitTask


class TaskManager:
    __slots__ = ("_on_task", "_lock", "_pending_tasks")

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
