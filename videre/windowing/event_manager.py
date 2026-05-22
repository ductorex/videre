import logging

import pygame

from videre.core.constants import MouseButton
from videre.core.events import (
    CustomTasks,
    EscapeTask,
    ExitTask,
    KeyboardEntry,
    MouseEvent,
    SizeTask,
    VidereTask,
)
from videre.core.pygame_backend import Event
from videre.widgets.widget import Widget
from videre.windowing.event_propagator import EventPropagator
from videre.windowing.windowlayout import WindowLayout
from videre.windowing.windowutils import OnEvent

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

    def manage(self, event: Event) -> VidereTask | None:
        callback = self.on_event.get(event.type)
        if callback is not None:
            return callback(self, event)
        logger.debug(f"Unhandled pygame event: {pygame.event.event_name(event.type)}")
        return None

    def focus_out(self, widget: Widget | None = None) -> None:
        if self._focus and (widget is None or self._focus is widget):
            self._focus.handle_focus_out()
            self._focus = None

    on_event = OnEvent[int]()

    @on_event(pygame.QUIT)
    def _on_quit(self, event: Event) -> ExitTask:
        return CustomTasks.exit_task()

    @on_event(pygame.MOUSEWHEEL)
    def _on_mouse_wheel(self, event: Event) -> None:
        owner = self._layout.get_mouse_wheel_owner(*pygame.mouse.get_pos())
        if owner:
            shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
            owner.widget.handle_mouse_wheel(event.x, event.y, shift)

    @on_event(pygame.MOUSEBUTTONDOWN)
    def _on_mouse_button_down(self, event: Event) -> None:
        owner = self._layout.get_mouse_owner(*event.pos)
        if owner:
            # Handle mouse down
            button = MouseButton(event.button)
            self._down[button] = owner.widget
            EventPropagator.handle_mouse_down(
                owner.widget,
                MouseEvent(x=owner.x_in_parent, y=owner.y_in_parent, buttons=[button]),
            )
            # Handle focus
            focus = EventPropagator.handle_focus_in(owner.widget)
            if self._focus and self._focus != focus:
                assert self._focus is not None
                self._focus.handle_focus_out()
            self._focus = focus

    @on_event(pygame.MOUSEBUTTONUP)
    def _on_mouse_button_up(self, event: Event) -> None:
        button = MouseButton(event.button)
        owner = self._layout.get_mouse_owner(*event.pos)
        down_widget = self._down[button]
        if owner:
            EventPropagator.handle_mouse_up(
                owner.widget,
                MouseEvent(x=owner.x_in_parent, y=owner.y_in_parent, buttons=[button]),
            )
            if down_widget == owner.widget:
                EventPropagator.handle_click(owner.widget, button)
            elif down_widget is not None:
                EventPropagator.handle_mouse_down_canceled(down_widget, button)
        elif down_widget is not None:
            EventPropagator.handle_mouse_down_canceled(down_widget, button)
        self._down[button] = None

    @on_event(pygame.MOUSEMOTION)
    def _on_mouse_motion(self, event: Event) -> None:
        m_event = MouseEvent.from_mouse_motion(event)
        owner = self._layout.get_mouse_owner(*event.pos)
        if owner:
            m_event = MouseEvent.from_mouse_motion(
                event, owner.x_in_parent, owner.y_in_parent
            )
            if not self._motion:
                EventPropagator.handle_mouse_enter(owner.widget, m_event)
            elif self._motion is owner.widget:
                EventPropagator.handle_mouse_over(owner.widget, m_event)
            else:
                assert self._motion is not None
                EventPropagator.manage_mouse_motion(event, owner, self._motion)
            self._motion = owner.widget
        elif self._motion:
            EventPropagator.handle_mouse_exit(self._motion)
            self._motion = None
        for button in m_event.buttons:
            if self._down[button]:
                down = self._down[button]
                assert down is not None
                parent_x = 0 if down.parent is None else down.parent.global_x
                parent_y = 0 if down.parent is None else down.parent.global_y
                EventPropagator.handle_mouse_down_move(
                    down,
                    MouseEvent.from_mouse_motion(
                        event, event.pos[0] - parent_x, event.pos[1] - parent_y
                    ),
                )

    @on_event(pygame.WINDOWLEAVE)
    def _on_window_leave(self, event: Event) -> None:
        if self._motion:
            EventPropagator.handle_mouse_exit(self._motion)
            self._motion = None

    @on_event(pygame.WINDOWRESIZED)
    def _on_window_resized(self, event: Event) -> SizeTask:
        return SizeTask(event.x, event.y)

    @on_event(pygame.TEXTINPUT)
    def _on_text_input(self, event: Event) -> None:
        if self._focus:
            self._focus.handle_text_input(event.text)

    @on_event(pygame.KEYDOWN)
    def _on_keydown(self, event: Event) -> EscapeTask | None:
        keyboard_entry = KeyboardEntry(event)
        if self._focus:
            self._focus.handle_keydown(keyboard_entry)
        elif keyboard_entry.escape:
            return EscapeTask()
        return None
