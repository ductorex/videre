class MouseOwnership:
    """
    Represent a mouse ownership.
    widget: widget that owns mouse.
    x_in_parent, y_in_parent: mouse coordinates relative to widget parent.
    """

    __slots__ = ("widget", "x_in_parent", "y_in_parent")

    def __init__(self, widget, x_in_parent: int, y_in_parent: int):
        from videre.widgets.widget import Widget

        self.widget: Widget = widget
        self.x_in_parent = x_in_parent
        self.y_in_parent = y_in_parent
