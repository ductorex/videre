from typing import Callable, Sequence

from videre import Alignment
from videre.core.mouse_ownership import MouseOwnership
from videre.widgets.widget import Widget


class AbstractLayout(Widget):
    __wprops__ = {"_controls"}
    __size__ = None
    __capture_mouse__ = False
    __slots__ = ()

    def __init__(self, controls: Sequence[Widget] = (), **kwargs):
        super().__init__(**kwargs)
        self._set_controls(controls)

    def _set_controls(self, controls: Sequence[Widget]):
        if self._get_wprop("_controls") == controls:
            return
        if self.__size__ is not None and len(controls) != self.__size__:
            raise RuntimeError(
                f"[{type(self).__name__}] expects exactly {self.__size__} children"
            )
        for old_control in self._controls() or ():
            old_control.with_parent(None)
        self._set_wprop("_controls", [ctrl.with_parent(self) for ctrl in controls])

    def _controls(self) -> list[Widget]:
        return self._get_wprop("_controls")

    def get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        if super().get_mouse_owner(x_in_parent, y_in_parent):
            local_x, local_y = self.get_local_coordinates(x_in_parent, y_in_parent)
            child = get_top_mouse_owner(local_x, local_y, self._controls())
            if child:
                return child
            elif self.__capture_mouse__:
                return MouseOwnership(self, x_in_parent, y_in_parent)
        return None

    def get_mouse_wheel_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        if self._get_mouse_owner(x_in_parent, y_in_parent):
            local_x, local_y = self.get_local_coordinates(x_in_parent, y_in_parent)
            return get_top_mouse_wheel_owner(local_x, local_y, self._controls())
        return None

    def collect_matches(self, callback: Callable[[Widget], bool]) -> list[Widget]:
        matches = super().collect_matches(callback)
        for control in self._controls():
            matches.extend(control.collect_matches(callback))
        return matches

    def has_changed(self) -> bool:
        return super().has_changed() or any(
            ctrl.has_changed() for ctrl in self._controls()
        )

    def flush_changes(self):
        super().flush_changes()
        for ctrl in self._controls():
            ctrl.flush_changes()

    @classmethod
    def _align_dim(
        cls, available_size: int, control_size: int, alignment: Alignment
    ) -> int:
        return max(0, cls._align_dim_free(available_size, control_size, alignment))

    @staticmethod
    def _align_dim_free(
        available_size: int, control_size: int, alignment: Alignment
    ) -> int:
        if alignment == Alignment.START:
            return 0
        elif alignment == Alignment.CENTER:
            return (available_size - control_size) // 2
        else:
            # alignment == Alignment.END
            return available_size - control_size


def get_top_mouse_owner(
    x: int, y: int, controls: Sequence[Widget]
) -> MouseOwnership | None:
    for ctrl in reversed(controls):
        owner = ctrl.get_mouse_owner(x, y)
        if owner is not None:
            return owner
    return None


def get_top_mouse_wheel_owner(
    x: int, y: int, controls: Sequence[Widget]
) -> MouseOwnership | None:
    for ctrl in reversed(controls):
        owner = ctrl.get_mouse_wheel_owner(x, y)
        if owner is not None:
            return owner
    return None
