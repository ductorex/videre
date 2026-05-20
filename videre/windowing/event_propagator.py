from typing import Protocol

from videre import MouseButton
from videre.core.events import MouseEvent
from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_backend import Event
from videre.widgets.widget import Widget


class _NamedMethod[W, **P, R](Protocol):
    """A function-like object exposing `__name__` — what we need to
    resolve the same method by name on a (possibly subclass) instance
    via `getattr`. Plain `Callable` doesn't promise `__name__`."""

    __name__: str

    def __call__(self, obj: W, /, *args: P.args, **kwargs: P.kwargs) -> R: ...


def call_overload[W, **P, R](
    obj: W, parent_method: _NamedMethod[W, P, R], *args: P.args, **kwargs: P.kwargs
) -> R:
    return getattr(obj, parent_method.__name__)(*args, **kwargs)


class EventPropagator:
    @classmethod
    def _handle[**P, R](
        cls,
        widget: Widget | None,
        handle_function: _NamedMethod[Widget, P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Widget | None:
        while widget:
            handled = call_overload(widget, handle_function, *args, **kwargs)
            if handled:
                assert isinstance(handled, Widget)
                return handled
            else:
                widget = widget.parent
        return None

    @classmethod
    def _handle_mouse_event[R](
        cls,
        widget: Widget | None,
        handle_function: _NamedMethod[Widget, [MouseEvent], R],
        event: MouseEvent,
    ) -> Widget | None:
        while widget:
            handled = call_overload(widget, handle_function, event)
            if handled:
                assert isinstance(handled, Widget)
                return handled
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
        return cls._handle(widget, Widget.handle_click, button)

    @classmethod
    def handle_focus_in(cls, widget: Widget) -> Widget | None:
        return cls._handle(widget, Widget.handle_focus_in)

    @classmethod
    def handle_mouse_over(cls, widget: Widget, event: MouseEvent) -> Widget | None:
        return cls._handle_mouse_event(widget, Widget.handle_mouse_over, event)

    @classmethod
    def handle_mouse_enter(cls, widget: Widget, event: MouseEvent) -> Widget | None:
        return cls._handle_mouse_event(widget, Widget.handle_mouse_enter, event)

    @classmethod
    def handle_mouse_exit(cls, widget: Widget) -> Widget | None:
        return cls._handle(widget, Widget.handle_mouse_exit)

    @classmethod
    def handle_mouse_down(cls, widget: Widget, event: MouseEvent) -> Widget | None:
        return cls._handle_mouse_event(widget, Widget.handle_mouse_down, event)

    @classmethod
    def handle_mouse_up(cls, widget: Widget, event: MouseEvent) -> Widget | None:
        return cls._handle_mouse_event(widget, Widget.handle_mouse_up, event)

    @classmethod
    def handle_mouse_down_move(cls, widget: Widget, event: MouseEvent) -> Widget | None:
        return cls._handle_mouse_event(widget, Widget.handle_mouse_down_move, event)

    @classmethod
    def handle_mouse_down_canceled(
        cls, widget: Widget, button: MouseButton
    ) -> Widget | None:
        return cls._handle(widget, Widget.handle_mouse_down_canceled, button)

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
