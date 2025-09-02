from typing import Callable, Self, Sequence, TypeAlias

from videre import Style, StyleDef
from videre.core.constants import Alignment
from videre.core.events import MouseEvent
from videre.core.sides.border import Border
from videre.layouts.column import Column
from videre.layouts.divutils.div import Div
from videre.widgets.abstract_button import AbstractButton
from videre.widgets.text import Text
from videre.widgets.widget import Widget

OnChangeType: TypeAlias = Callable[[Widget], Widget]
ActionFunction: TypeAlias = Callable[[], None]


class _Action(Div):
    __slots__ = ("_action", "_text", "_menu")
    __wprops__ = {}

    def __init__(
        self,
        menu: "ContextButton",
        text: str,
        action: ActionFunction | None = None,
        width: int | None = None,
    ):
        self._menu = menu
        self._action = action
        self._text = text
        super().__init__(
            Text(text),
            on_click=self._execute,
            style=StyleDef(
                default=Style(
                    width=width, border=Border(), horizontal_alignment=Alignment.START
                )
            ),
        )

    def _execute(self, *args):
        if self._action:
            self._action()
        self._menu._close_context()


class ContextButton(AbstractButton):
    __slots__ = ("_context",)
    __wprops__ = {"actions"}

    def __init__(
        self,
        text: str,
        actions: Sequence[str | tuple[str, ActionFunction]] = (),
        **kwargs,
    ):
        kwargs.pop("on_click", None)
        super().__init__(text, **kwargs)
        self._context: Widget | None = None
        self.actions = actions

    @property
    def actions(self) -> Sequence[tuple[str, ActionFunction | None]]:
        return list(self._get_wprop("actions"))

    @actions.setter
    def actions(
        self, actions: Sequence[str | tuple[str, ActionFunction | None]]
    ) -> None:
        self._set_wprop(
            "actions",
            [
                (action, None) if isinstance(action, str) else action
                for action in actions
            ],
        )

    def handle_mouse_down(self, event: MouseEvent):
        if event.button_left:
            super().handle_mouse_down(event)
            if self._context:
                self._close_context()
            else:
                self._open_context()

    def handle_focus_in(self) -> Self:
        return self

    def handle_focus_out(self):
        self._close_context()

    def _open_context(self):
        actions = self.actions
        if not self.disabled and actions:
            width = self._compute_width(self.get_window())
            self._context = Column(
                [_Action(self, name, callback, width) for name, callback in actions]
            )
            self.get_window().set_context(self, self._context, y=-1)

    def _close_context(self):
        if self._context:
            self.get_window().clear_context()
            self._context = None

    def _compute_width(self, window):
        text_width = max(
            (
                Text(action[0]).render(window, None, None).get_width()
                for action in self.actions
            ),
            default=0,
        )
        padding = Div.__style__.default.padding
        return padding.left + text_width + padding.right
