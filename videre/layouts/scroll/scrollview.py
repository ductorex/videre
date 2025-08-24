import logging

from videre.core.mouse_ownership import MouseOwnership
from videre.core.pygame_utils import Surface
from videre.layouts.abstractlayout import AbstractLayout, get_top_mouse_wheel_owner
from videre.layouts.scroll._h_scroll_bar import _HScrollBar
from videre.layouts.scroll._v_scroll_bar import _VScrollBar
from videre.widgets.widget import Widget


class ScrollView(AbstractLayout):
    __wprops__ = {
        "scroll_thickness",
        "horizontal_scroll",
        "vertical_scroll",
        "wrap_horizontal",
        "wrap_vertical",
        "default_bottom",
    }
    __size__ = 3
    __slots__ = ("_ctrl", "_hscrollbar", "_vscrollbar")
    _SCROLL_STEP = 120

    def __init__(
        self,
        control: Widget,
        scroll_thickness=18,
        horizontal_scroll=True,
        vertical_scroll=True,
        wrap_horizontal=False,
        wrap_vertical=False,
        default_bottom=False,
        **kwargs,
    ):
        self._ctrl = control
        self._hscrollbar = _HScrollBar(
            thickness=scroll_thickness, on_jump=self.on_jump_x
        )
        self._vscrollbar = _VScrollBar(
            thickness=scroll_thickness, on_jump=self.on_jump_y
        )
        super().__init__([control, self._hscrollbar, self._vscrollbar], **kwargs)
        self.scroll_thickness = scroll_thickness
        self.horizontal_scroll = horizontal_scroll
        self.vertical_scroll = vertical_scroll
        self.wrap_horizontal = wrap_horizontal
        self.wrap_vertical = wrap_vertical
        self.default_bottom = default_bottom

    @property
    def scroll_thickness(self) -> int:
        return self._get_wprop("scroll_thickness")

    @scroll_thickness.setter
    def scroll_thickness(self, value: int):
        self._set_wprop("scroll_thickness", max(0, value))

    @property
    def horizontal_scroll(self) -> bool:
        return self._get_wprop("horizontal_scroll")

    @horizontal_scroll.setter
    def horizontal_scroll(self, value):
        self._set_wprop("horizontal_scroll", bool(value))

    @property
    def vertical_scroll(self) -> bool:
        return self._get_wprop("vertical_scroll")

    @vertical_scroll.setter
    def vertical_scroll(self, value):
        self._set_wprop("vertical_scroll", bool(value))

    @property
    def wrap_horizontal(self) -> bool:
        return self._get_wprop("wrap_horizontal")

    @wrap_horizontal.setter
    def wrap_horizontal(self, value):
        self._set_wprop("wrap_horizontal", bool(value))

    @property
    def wrap_vertical(self) -> bool:
        return self._get_wprop("wrap_vertical")

    @wrap_vertical.setter
    def wrap_vertical(self, value):
        self._set_wprop("wrap_vertical", bool(value))

    @property
    def default_bottom(self) -> bool:
        return self._get_wprop("default_bottom")

    @default_bottom.setter
    def default_bottom(self, value):
        self._set_wprop("default_bottom", bool(value))

    @property
    def control(self) -> Widget:
        return self._ctrl

    @control.setter
    def control(self, control: Widget):
        self._ctrl = control
        self._set_controls([control, self._hscrollbar, self._vscrollbar])

    @property
    def _content_x(self) -> int:
        return self._ctrl.x

    @_content_x.setter
    def _content_x(self, x: int):
        self._set_child_x(self._ctrl, x)

    @property
    def _content_y(self) -> int:
        return self._ctrl.y

    @_content_y.setter
    def _content_y(self, y: int):
        self._set_child_y(self._ctrl, y)

    def on_jump_x(self, content_x: int):
        self._content_x = -content_x
        self.update()

    def _add_scroll_event_y(self):
        self._transient_state["scroll_event_y"] = True

    def _has_scroll_event_y(self) -> bool:
        return self._transient_state.get("scroll_event_y")

    def on_jump_y(self, content_y: int):
        prev = self._content_y
        if prev != -content_y:
            self._content_y = -content_y
            self.update()
            self._add_scroll_event_y()

    def get_mouse_wheel_owner(
        self, x_in_parent: int, y_in_parent: int
    ) -> MouseOwnership | None:
        if Widget._get_mouse_owner(self, x_in_parent, y_in_parent):
            local_x, local_y = self.get_local_coordinates(x_in_parent, y_in_parent)
            child = get_top_mouse_wheel_owner(local_x, local_y, self._controls())
            if child and isinstance(child.widget, ScrollView):
                return child
            else:
                return MouseOwnership(self, x_in_parent, y_in_parent)
        return None

    def handle_mouse_wheel(self, x: int, y: int, shift: bool):
        if not x and not y:
            return

        horizontal, vertical = 0, 0
        if x and y:
            horizontal, vertical = x, y
        elif x:
            horizontal = x
        elif shift:
            horizontal = y
        else:
            vertical = y

        if self._can_scroll(
            horizontal,
            self.horizontal_scroll,
            self.rendered_width,
            self._ctrl.rendered_width,
            self._content_x,
        ):
            self._transient_state["h"] = horizontal
        if self._can_scroll(
            vertical,
            self.vertical_scroll,
            self.rendered_height,
            self._ctrl.rendered_height,
            self._content_y,
        ):
            self._transient_state["v"] = vertical
            self._add_scroll_event_y()

    @classmethod
    def _can_scroll(
        cls,
        direction: int,
        scroll_allowed: bool,
        view_length: int,
        content_length: int,
        content_pos: int,
    ) -> bool:
        if not scroll_allowed or not direction:
            return False
        if direction > 0:
            # scroll top
            return content_pos < 0
        else:
            # scroll bottom
            return content_pos > view_length - content_length

    def draw(self, window, width: int = None, height: int = None) -> Surface:
        thickness = self.scroll_thickness
        c_w_hint = width if self.wrap_horizontal else None
        c_h_hint = height if self.wrap_vertical else None
        content = self.control.render(window, c_w_hint, c_h_hint)
        content_w, content_h = content.get_width(), content.get_height()

        if width is None:
            width = content_w
        if height is None:
            height = content_h

        if (
            width == content_w
            and height == content_h
            and self._content_x == 0
            and self._content_y == 0
        ):
            return content

        self._content_x, has_h_scroll = self._update_content_pos(
            width,
            content_w,
            self._content_x,
            self._transient_state.get("h"),
            self.horizontal_scroll,
        )

        self._content_y, has_v_scroll = self._update_content_pos(
            height,
            content_h,
            self._content_y,
            self._transient_state.get("v"),
            self.vertical_scroll,
        )

        if has_v_scroll and self.default_bottom:
            end_pos = height - content_h
            if self._has_scroll_event_y():
                # We got a vertical scroll event
                # Does this event set content_y anywhere else than bottom
                if self._content_y != end_pos:
                    # content_y moved off from bottom.
                    # cancel default_bottom
                    self.default_bottom = False
            else:
                # set content_y to bottom
                self._content_y = end_pos

        view = window.new_surface(width, height)
        view.blit(content, (self._content_x, self._content_y))

        both = has_h_scroll and has_v_scroll
        if has_h_scroll:
            self._hscrollbar.configure(content_w, self._content_x, both, thickness)
            bg = self._hscrollbar.background.render(window, width, height)
            view.blit(bg, self._hscrollbar.background.pos)
            h_scroll = self._hscrollbar.render(window, width, height)
            view.blit(h_scroll, (self._hscrollbar.x, self._hscrollbar.y))
        if has_v_scroll:
            self._vscrollbar.configure(content_h, self._content_y, both, thickness)
            bg = self._vscrollbar.background.render(window, width, height)
            view.blit(bg, self._vscrollbar.background.pos)
            v_scroll = self._vscrollbar.render(window, width, height)
            view.blit(v_scroll, (self._vscrollbar.x, self._vscrollbar.y))

        logging.debug(
            f"{(width, height)} {(self._content_x, self._content_y)} "
            f"{(content_w, content_h)}"
        )
        return view

    @classmethod
    def _update_content_pos(
        cls, view_length, content_length, content_pos, step_count, scroll_allowed
    ) -> tuple[int, bool]:

        if content_length <= view_length:
            content_pos = 0
        elif content_pos > 0:
            content_pos = 0
        elif content_pos + content_length - 1 < view_length - 1:
            content_pos = view_length - content_length

        if step_count is not None:
            step = cls._SCROLL_STEP * step_count
            if step > 0:
                # move to bottom of view
                content_pos = min(content_pos + step, 0)
            else:
                # move to top of view
                content_pos = max(content_pos + step, view_length - content_length)

        scrollbar_is_visible = content_length > view_length and scroll_allowed
        return content_pos, scrollbar_is_visible
