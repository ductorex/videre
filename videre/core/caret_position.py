from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class CaretPosition:
    """
    Caret position for text input. Coordinates are
    absolute within the rendered surface; the caret is a vertical
    segment from `y_top` to `y_bottom` at horizontal position `x`.
    """

    x: int
    y_top: int
    y_bottom: int
