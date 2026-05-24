from dataclasses import dataclass, field
from enum import Enum, auto, unique
from typing import Self, TypeAlias


@unique
class MouseButton(Enum):
    BUTTON_LEFT = auto()
    BUTTON_MIDDLE = auto()
    BUTTON_RIGHT = auto()
    BUTTON_WHEELDOWN = auto()
    BUTTON_WHEELUP = auto()
    BUTTON_X1 = auto()
    BUTTON_X2 = auto()


@unique
class KeyMod(Enum):
    LSHIFT = auto()
    RSHIFT = auto()
    LCTRL = auto()
    RCTRL = auto()
    RALT = auto()
    LALT = auto()
    CAPS = auto()


@unique
class Key(Enum):
    BACKSPACE = auto()
    TAB = auto()
    ENTER = auto()
    ESCAPE = auto()
    DELETE = auto()
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    HOME = auto()
    END = auto()
    PAGEUP = auto()
    PAGEDOWN = auto()
    PRINTSCREEN = auto()
    SPACE = auto()
    A = auto()
    C = auto()
    V = auto()


@dataclass(slots=True, frozen=True)
class MouseEvent:
    x: int = 0
    y: int = 0
    dx: int = 0
    dy: int = 0
    buttons: tuple[MouseButton, ...] = field(default_factory=tuple)

    @property
    def button(self) -> MouseButton:
        (button,) = self.buttons
        return button

    @property
    def button_left(self) -> bool:
        return MouseButton.BUTTON_LEFT in self.buttons

    @property
    def button_middle(self) -> bool:
        return MouseButton.BUTTON_MIDDLE in self.buttons

    @property
    def button_right(self) -> bool:
        return MouseButton.BUTTON_RIGHT in self.buttons

    def replace(self, x: int | None = None, y: int | None = None) -> Self:
        return type(self)(
            x=self.x if x is None else x,
            y=self.y if y is None else y,
            dx=self.dx,
            dy=self.dy,
            buttons=tuple(self.buttons),
        )


@dataclass(slots=True, frozen=True)
class MouseButtonDownEvent(MouseEvent):
    pass


@dataclass(slots=True, frozen=True)
class MouseButtonUpEvent(MouseEvent):
    pass


@dataclass(slots=True, frozen=True)
class MouseMotionEvent(MouseEvent):
    pass


@dataclass(slots=True, frozen=True)
class MouseWheelEvent:
    mouse_x: int
    mouse_y: int
    wheel_dx: int
    wheel_dy: int
    shift: bool


@dataclass(slots=True, frozen=True)
class KeyboardEntry:
    modifiers: frozenset[KeyMod] = field(default_factory=frozenset)
    key: Key | None = None
    unicode: str | None = None

    lshift = property(lambda self: KeyMod.LSHIFT in self.modifiers)
    rshift = property(lambda self: KeyMod.RSHIFT in self.modifiers)
    lctrl = property(lambda self: KeyMod.LCTRL in self.modifiers)
    rctrl = property(lambda self: KeyMod.RCTRL in self.modifiers)
    ralt = property(lambda self: KeyMod.RALT in self.modifiers)
    lalt = property(lambda self: KeyMod.LALT in self.modifiers)

    backspace = property(lambda self: self.key == Key.BACKSPACE)
    tab = property(lambda self: self.key == Key.TAB)
    enter = property(lambda self: self.key == Key.ENTER)
    escape = property(lambda self: self.key == Key.ESCAPE)
    delete = property(lambda self: self.key == Key.DELETE)
    up = property(lambda self: self.key == Key.UP)
    down = property(lambda self: self.key == Key.DOWN)
    left = property(lambda self: self.key == Key.LEFT)
    right = property(lambda self: self.key == Key.RIGHT)
    home = property(lambda self: self.key == Key.HOME)
    end = property(lambda self: self.key == Key.END)
    pageup = property(lambda self: self.key == Key.PAGEUP)
    pagedown = property(lambda self: self.key == Key.PAGEDOWN)
    printscreen = property(lambda self: self.key == Key.PRINTSCREEN)

    A = property(lambda self: self.key == Key.A)
    C = property(lambda self: self.key == Key.C)
    V = property(lambda self: self.key == Key.V)

    @property
    def caps(self) -> int:
        return KeyMod.CAPS in self.modifiers

    @property
    def ctrl(self) -> int:
        return KeyMod.LCTRL in self.modifiers or KeyMod.RCTRL in self.modifiers

    @property
    def alt(self) -> int:
        return KeyMod.RALT in self.modifiers or KeyMod.LALT in self.modifiers

    @property
    def shift(self) -> int:
        return KeyMod.LSHIFT in self.modifiers or KeyMod.RSHIFT in self.modifiers

    def __repr__(self):
        return " + ".join(
            key for key in ("caps", "ctrl", "alt", "shift") if getattr(self, key)
        )


@dataclass(slots=True, frozen=True)
class WindowLeaveEvent:
    pass


@dataclass(slots=True, frozen=True)
class TextInputEvent:
    text: str


@dataclass(slots=True, frozen=True)
class KeyDownEvent:
    entry: KeyboardEntry


@dataclass(slots=True, frozen=True)
class ExitEvent:
    pass


@dataclass(slots=True, frozen=True)
class WindowResizeEvent:
    width: int
    height: int


VidereEvent: TypeAlias = (
    MouseWheelEvent
    | MouseMotionEvent
    | MouseButtonDownEvent
    | MouseButtonUpEvent
    | TextInputEvent
    | KeyDownEvent
    | WindowLeaveEvent
    | ExitEvent
    | WindowResizeEvent
)
