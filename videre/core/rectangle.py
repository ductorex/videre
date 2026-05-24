from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Rectangle:
    # left <=> x, top <=> y
    left: int | float = 0
    top: int | float = 0
    width: int | float = 0
    height: int | float = 0
