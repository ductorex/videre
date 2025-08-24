import logging
import sys
from abc import abstractmethod
from typing import Any, Callable, Self

from videre.core.constants import MouseButton
from videre.core.events import KeyboardEntry, MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.core.position_mapping import Position, PositionMapping
from videre.core.pygame_utils import Surface

logger = logging.getLogger(__name__)


class Widget:
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
    )

    def __init__(
        self,
        weight: int = 0,
        parent: Self | None = None,
        key: str | None = None,
        name: str | None = None,
    ):
        super().__init__()

        new: dict = {"weight": weight}
        if self._has_wprop("name"):
            if not isinstance(name, str):
                name = ""
            new["name"] = name

        self._key = key or id(self)
        self._old = {}
        self._new = new
        self._old_update = ()
        self._transient_state = {}
        self._surface: Surface | None = None
        self._rc = 0

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

    def _assert_rendered(self):
        if not self._surface:
            raise RuntimeError(f"{self} not yet drawn")

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
        self._assert_rendered()
        return self.top + self._surface.get_height() - 1

    @property
    def right(self) -> int:
        self._assert_rendered()
        return self.left + self._surface.get_width() - 1

    @property
    def rendered_width(self) -> int:
        self._assert_rendered()
        return self._surface.get_width()

    @property
    def rendered_height(self) -> int:
        self._assert_rendered()
        return self._surface.get_height()

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
            self._surface
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

    def get_window(self):
        from videre.windowing.window import Window

        window: Window = self._old_update[0]
        return window

    def _prev_scope_width(self) -> int:
        return self._old_update[1]

    def _prev_scope_height(self) -> int:
        return self._old_update[2]

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

    def render(self, window, width: int = None, height: int = None) -> Surface:
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
        return self._surface

    @abstractmethod
    def draw(self, window, width: int = None, height: int = None) -> Surface:
        raise NotImplementedError()

    def handle_mouse_wheel(self, x: int, y: int, shift: bool):
        pass

    def handle_click(self, button: MouseButton):
        pass

    def handle_focus_in(self) -> bool | Self:
        """Return True if this widget accepts the focus, False otherwise."""
        return False

    def handle_focus_out(self):
        pass

    def handle_mouse_enter(self, event: MouseEvent):
        pass

    def handle_mouse_over(self, event: MouseEvent):
        pass

    def handle_mouse_down(self, event: MouseEvent):
        pass

    def handle_mouse_down_move(self, event: MouseEvent):
        pass

    def handle_mouse_down_canceled(self, button: MouseButton):
        pass

    def handle_mouse_up(self, event: MouseEvent):
        pass

    def handle_mouse_exit(self):
        pass

    def handle_text_input(self, text: str):
        pass

    def handle_keydown(self, key: KeyboardEntry):
        pass
