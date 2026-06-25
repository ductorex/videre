import logging
import sys
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Self

from videre.core.drawer import Drawer, Position
from videre.core.events import KeyboardEntry, MouseButton, MouseEvent
from videre.core.position_mapping import PositionMapping
from videre.widgets.widget_utils import MouseOwnership

if TYPE_CHECKING:
    from videre.windowing.window import Window


logger = logging.getLogger(__name__)


class Widget(ABC):
    __wprops__ = ("weight",)

    __slots__ = (
        "_key",
        "_old",
        "_new",
        "_surface",
        "_old_update",
        "_transient_state",
        "_rc",
        "_parent",
        "_children_pos",
        "data",
    )

    def __init__(
        self,
        weight: int = 0,
        parent: Self | None = None,
        key: str | None = None,
        name: str | None = None,
        data: Any = None,
    ):
        super().__init__()

        new: dict = {"weight": weight}
        if self._has_wprop("name"):
            if not isinstance(name, str):
                name = ""
            new["name"] = name

        self._key: str = key or str(id(self))
        self._old = {}
        self._new = new
        self._old_update: tuple[Window, int | None, int | None] | None = None
        self._transient_state = {}
        self._surface: Drawer | None = None
        self._rc = 0
        self.data = data

        self._children_pos = PositionMapping()
        self._parent: Widget | None = None
        if parent:
            self.with_parent(parent)

    def with_parent(self, parent):
        # todo code should forbid adding same widget to many parents
        # todo note that we may need to care about child order/rank in parent
        if self._parent != parent:
            if self._parent is not None:
                self._parent.remove_child(self)
            self._parent = parent
        return self

    def get_child_position(self, child: "Widget") -> Position:
        return self._children_pos.get(child)

    def _set_child_position(self, child: "Widget", x: int, y: int):
        self._children_pos.set(child, x, y)

    def _set_child_x(self, child: "Widget", x: int):
        self._children_pos.update_x(child, x)

    def _set_child_y(self, child: "Widget", y: int):
        self._children_pos.update_y(child, y)

    def remove_child(self, child: Self):
        self._children_pos.remove(child)

    def get_lineage(self) -> list[Self]:
        ancestors = []
        widget = self
        while True:
            if widget is None:
                break
            else:
                ancestors.append(widget)
                widget = widget.parent
        return ancestors

    @property
    def name(self) -> str | None:
        return self._get_wprop("name") if self._has_wprop("name") else None

    @property
    def key(self) -> str:
        return self._key

    @property
    def x(self) -> int:
        return self._parent.get_child_position(self).x if self._parent else 0

    @property
    def y(self) -> int:
        return self._parent.get_child_position(self).y if self._parent else 0

    @property
    def weight(self) -> int:
        return self._get_wprop("weight")

    @weight.setter
    def weight(self, weight: int):
        self._set_wprop("weight", weight)

    @property
    def parent(self):
        return self._parent

    @property
    def global_x(self) -> int:
        if self._parent:
            return self._parent.global_x + self.x
        return self.x

    @property
    def global_y(self) -> int:
        if self._parent:
            return self._parent.global_y + self.y
        return self.y

    def _assert_rendered(self) -> Drawer:
        if not self._surface:
            raise RuntimeError(f"{self} not yet drawn")
        return self._surface

    def is_rendered(self) -> bool:
        return self._surface is not None

    @property
    def top(self) -> int:
        return self.y

    @property
    def left(self) -> int:
        return self.x

    @property
    def pos(self) -> tuple[int, int]:
        return self.x, self.y

    @property
    def bottom(self) -> int:
        return self.top + self._assert_rendered().get_height() - 1

    @property
    def right(self) -> int:
        return self.left + self._assert_rendered().get_width() - 1

    @property
    def rendered_width(self) -> int:
        return self._assert_rendered().get_width()

    @property
    def rendered_height(self) -> int:
        return self._assert_rendered().get_height()

    def get_root(self) -> "Widget":
        root = self
        while True:
            parent = root.parent
            if parent is None:
                return root
            else:
                root = parent

    def get_local_coordinates(self, global_x: int, global_y: int) -> tuple[int, int]:
        return global_x - self.x, global_y - self.y

    def get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        return self._get_mouse_owner(x_in_parent, y_in_parent)

    def _get_mouse_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        if (
            self.is_rendered()
            and self.left <= x_in_parent <= self.right
            and self.top <= y_in_parent <= self.bottom
        ):
            return MouseOwnership(self, x_in_parent, y_in_parent)
        return None

    def collect_matches(self, callback: Callable[["Widget"], bool]) -> list["Widget"]:
        return [self] if callback(self) else []

    def get_mouse_wheel_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        return self.get_mouse_owner(x_in_parent, y_in_parent)

    def __repr__(self):
        return f"[{type(self).__name__}][{self._key}]"

    def _debug(self, *args, **kwargs):
        debuglevel = logging.INFO
        if debuglevel >= logging.root.level:
            level_name = logging.getLevelName(debuglevel)
            print(f"{level_name}:", self, *args, **kwargs, file=sys.stderr)

    def get_window(self) -> "Window":
        assert self._old_update is not None
        return self._old_update[0]

    def _prev_scope_width(self) -> int:
        assert self._old_update is not None
        width = self._old_update[1]
        assert width is not None
        return width

    def _prev_scope_height(self) -> int:
        assert self._old_update is not None
        height = self._old_update[2]
        assert height is not None
        return height

    @classmethod
    def _has_wprop(cls, name: str) -> bool:
        for typ in cls.__mro__:
            wprops = getattr(typ, "__wprops__", ())
            if name in wprops:
                return True
        return False

    @classmethod
    def _assert_wprop(cls, name):
        assert cls._has_wprop(name), f"{cls.__name__}: unknown widget property: {name}"

    def _set_wprop(self, name: str, value: Any):
        self._assert_wprop(name)
        self._new[name] = value

    def _set_wprops(self, **kwargs):
        for name in kwargs:
            self._assert_wprop(name)
        self._new.update(kwargs)

    def _get_wprop(self, name: str) -> Any:
        self._assert_wprop(name)
        return self._new.get(name)

    def update(self):
        self._transient_state["redraw"] = True

    def has_changed(self) -> bool:
        return self._old != self._new or bool(self._transient_state)

    def flush_changes(self):
        self._old = self._new.copy()
        self._transient_state.clear()

    def render(
        self, window, width: int | None = None, height: int | None = None
    ) -> Drawer:
        new_update = (window, width, height)
        if (
            self._surface is None
            or self._old_update != new_update
            or self.has_changed()
        ):
            self._rc += 1
            self._debug("render", self._rc)
            self._surface = self.draw(*new_update)
        self._old = self._new.copy()
        self._old_update = new_update
        self._transient_state.clear()
        assert self._surface is not None
        return self._surface

    @abstractmethod
    def draw(
        self, window: "Window", width: int | None = None, height: int | None = None
    ) -> Drawer:
        raise NotImplementedError()

    def handle_mouse_wheel(self, x: int, y: int, shift: bool):
        pass

    def handle_click(self, button: MouseButton) -> "Widget | None":
        return None

    def handle_focus_in(self) -> "Widget | None":
        """Return the widget that accepts the focus (usually this widget), or None otherwise."""
        return None

    def handle_focus_out(self):
        pass

    def handle_mouse_enter(self, event: MouseEvent) -> "Widget | None":
        return None

    def handle_mouse_over(self, event: MouseEvent) -> "Widget | None":
        return None

    def handle_mouse_down(self, event: MouseEvent) -> "Widget | None":
        return None

    def handle_mouse_down_move(self, event: MouseEvent) -> "Widget | None":
        return None

    def handle_mouse_down_canceled(self, button: MouseButton) -> "Widget | None":
        return None

    def handle_mouse_up(self, event: MouseEvent) -> "Widget | None":
        return None

    def handle_mouse_exit(self) -> "Widget | None":
        return None

    def handle_text_input(self, text: str):
        pass

    def handle_keydown(self, key: KeyboardEntry) -> "Widget | None":
        return None
