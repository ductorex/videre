from pygame.event import Event

from videre import MouseButton
from videre.core.events import MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.widgets.widget import Widget


class EventPropagator:
    @classmethod
    def _handle(
        cls, widget: Widget | None, handle_function: str, *args, **kwargs
    ) -> Widget | None:
        # print(handle_function, widget)
        if widget:
            handled = getattr(widget, handle_function)(*args, **kwargs)
            if handled:
                return handled if isinstance(handled, Widget) else widget
            else:
                return cls._handle(widget.parent, handle_function, *args, **kwargs)
        else:
            return None

    @classmethod
    def _handle_mouse_event(
        cls, widget: Widget | None, handle_function: str, event: MouseEvent
    ) -> Widget | None:
        # print(handle_function, widget)
        while widget:
            handled = getattr(widget, handle_function)(event)
            if handled:
                return handled if isinstance(handled, Widget) else widget
            else:
                parent = widget.parent
                widget = parent
                if parent:
                    x = parent.x + event.x
                    y = parent.y + event.y
                    event = event.with_coordinates(x, y)
        return None

    @classmethod
    def handle_click(cls, widget: Widget, button: MouseButton) -> Widget | None:
        return cls._handle(widget, Widget.handle_click.__name__, button)

    @classmethod
    def handle_focus_in(cls, widget: Widget) -> Widget | None:
        return cls._handle(widget, Widget.handle_focus_in.__name__)

    @classmethod
    def handle_mouse_over(cls, widget: Widget, event: MouseEvent):
        return cls._handle_mouse_event(widget, Widget.handle_mouse_over.__name__, event)

    @classmethod
    def handle_mouse_enter(cls, widget: Widget, event: MouseEvent):
        return cls._handle_mouse_event(
            widget, Widget.handle_mouse_enter.__name__, event
        )

    @classmethod
    def handle_mouse_exit(cls, widget: Widget):
        return cls._handle(widget, Widget.handle_mouse_exit.__name__)

    @classmethod
    def handle_mouse_down(cls, widget: Widget, event: MouseEvent):
        return cls._handle_mouse_event(widget, Widget.handle_mouse_down.__name__, event)

    @classmethod
    def handle_mouse_up(cls, widget: Widget, event: MouseEvent):
        return cls._handle_mouse_event(widget, Widget.handle_mouse_up.__name__, event)

    @classmethod
    def handle_mouse_down_move(cls, widget: Widget, event: MouseEvent):
        return cls._handle_mouse_event(
            widget, Widget.handle_mouse_down_move.__name__, event
        )

    @classmethod
    def handle_mouse_down_canceled(cls, widget: Widget, button: MouseButton):
        return cls._handle(widget, Widget.handle_mouse_down_canceled.__name__, button)

    @classmethod
    def manage_mouse_motion(cls, event: Event, owner: MouseOwnership, previous: Widget):
        # Get potential exited widgets
        exited = set(previous.get_lineage())

        # Handle mouse enter and mouse over
        current = owner.widget
        mouse_x = owner.x_in_parent
        mouse_y = owner.y_in_parent
        while True:
            if current in exited:
                # both in and out

                # to be removed from exited
                exited.remove(current)

                # in and out => just a mouse over on current
                if current.handle_mouse_over(
                    MouseEvent.from_mouse_motion(event, mouse_x, mouse_y)
                ):
                    # Mouse over captured, stop.
                    break
            else:
                # just in => mouse enter on current
                if current.handle_mouse_enter(
                    MouseEvent.from_mouse_motion(event, mouse_x, mouse_y)
                ):
                    # mouse enter captured, stop.
                    break

            # get next
            parent = current.parent
            if parent:
                mouse_x = parent.x + mouse_x
                mouse_y = parent.y + mouse_y
                current = parent
            else:
                # No parent, stop
                break

        # Handle mouse exit on previous
        current_prev = previous
        while True:
            if current_prev in exited:
                # mouse exit on current_prev
                if current_prev.handle_mouse_exit():
                    # Mouse exit captured, stop.
                    break
                else:
                    # Get next
                    parent = current_prev.parent
                    if parent:
                        current_prev = parent
                    else:
                        break
            else:
                # Not registered in exited
                # Thus, do not `mouse exit`, neither from widget nor from parents
                break
