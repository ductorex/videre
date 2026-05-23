import logging

from videre.core.events import (
    KeyDownEvent,
    MouseButton,
    MouseButtonDownEvent,
    MouseButtonUpEvent,
    MouseEvent,
    MouseMotionEvent,
    MouseWheelEvent,
    TextInputEvent,
    VidereEvent,
    WindowLeaveEvent,
)
from videre.core.tasks import EscapeTask, VidereTask
from videre.core.utils import OnEvent
from videre.widgets.widget import Widget
from videre.windowing.event_propagator import EventPropagator
from videre.windowing.windowlayout import WindowLayout

logger = logging.getLogger(__name__)


class WindowEventManager:
    __slots__ = ("_layout", "_down", "_motion", "_focus")

    def __init__(self, layout: WindowLayout):
        self._layout = layout
        self._down: dict[MouseButton, Widget | None] = {
            button: None for button in MouseButton
        }
        self._motion: Widget | None = None
        self._focus: Widget | None = None

    def focus_out(self, widget: Widget | None = None) -> None:
        if self._focus and (widget is None or self._focus is widget):
            self._focus.handle_focus_out()
            self._focus = None

    def manage(self, event: VidereEvent) -> VidereTask | None:
        callback = self.on_event.get(type(event))
        assert callback is not None
        return callback(self, event)

    on_event = OnEvent[type[VidereEvent]]()

    @on_event(MouseWheelEvent)
    def on_mouse_wheel(self, event: MouseWheelEvent) -> None:
        owner = self._layout.get_mouse_wheel_owner(event.mouse_x, event.mouse_y)
        if owner:
            owner.widget.handle_mouse_wheel(event.wheel_dx, event.wheel_dy, event.shift)

    @on_event(MouseButtonDownEvent)
    def on_mouse_button_down(self, event: MouseButtonDownEvent) -> None:
        x, y, button = event.x, event.y, event.button
        owner = self._layout.get_mouse_owner(x, y)
        if owner:
            # Handle mouse down
            self._down[button] = owner.widget
            EventPropagator.handle_mouse_down(
                owner.widget,
                MouseEvent(x=owner.x_in_parent, y=owner.y_in_parent, buttons=(button,)),
            )
            # Handle focus
            focus = EventPropagator.handle_focus_in(owner.widget)
            if self._focus and self._focus != focus:
                assert self._focus is not None
                self._focus.handle_focus_out()
            self._focus = focus

    @on_event(MouseButtonUpEvent)
    def on_mouse_button_up(self, event: MouseButtonUpEvent) -> None:
        x, y, button = event.x, event.y, event.button
        owner = self._layout.get_mouse_owner(x, y)
        down_widget = self._down[button]
        if owner:
            EventPropagator.handle_mouse_up(
                owner.widget,
                MouseEvent(x=owner.x_in_parent, y=owner.y_in_parent, buttons=(button,)),
            )
            if down_widget == owner.widget:
                EventPropagator.handle_click(owner.widget, button)
            elif down_widget is not None:
                EventPropagator.handle_mouse_down_canceled(down_widget, button)
        elif down_widget is not None:
            EventPropagator.handle_mouse_down_canceled(down_widget, button)
        self._down[button] = None

    @on_event(MouseMotionEvent)
    def on_mouse_motion(self, event: MouseMotionEvent) -> None:
        owner = self._layout.get_mouse_owner(event.x, event.y)
        if owner:
            m_event = event.replace(x=owner.x_in_parent, y=owner.y_in_parent)
            if not self._motion:
                EventPropagator.handle_mouse_enter(owner.widget, m_event)
            elif self._motion is owner.widget:
                EventPropagator.handle_mouse_over(owner.widget, m_event)
            else:
                assert self._motion is not None
                EventPropagator.manage_mouse_motion(m_event, owner, self._motion)
            self._motion = owner.widget
        elif self._motion:
            EventPropagator.handle_mouse_exit(self._motion)
            self._motion = None
        for button in event.buttons:
            if self._down[button]:
                down = self._down[button]
                assert down is not None
                parent_x = 0 if down.parent is None else down.parent.global_x
                parent_y = 0 if down.parent is None else down.parent.global_y
                EventPropagator.handle_mouse_down_move(
                    down, event.replace(x=event.x - parent_x, y=event.y - parent_y)
                )

    @on_event(WindowLeaveEvent)
    def on_window_leave(self, _: WindowLeaveEvent) -> None:
        if self._motion:
            EventPropagator.handle_mouse_exit(self._motion)
            self._motion = None

    @on_event(TextInputEvent)
    def on_text_input(self, event: TextInputEvent) -> None:
        if self._focus:
            self._focus.handle_text_input(event.text)

    @on_event(KeyDownEvent)
    def on_keydown(self, event: KeyDownEvent) -> EscapeTask | None:
        if self._focus:
            self._focus.handle_keydown(event.entry)
        elif event.entry.escape:
            return EscapeTask()
        return None
