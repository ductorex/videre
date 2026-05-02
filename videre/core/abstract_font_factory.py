from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from videre.core.drawer import DrawerFont


@dataclass(slots=True, frozen=True)
class CharMetrics:
    """Metrics for a single character at a given font and size."""

    advance: float
    """Horizontal advance of the cursor after drawing the glyph."""

    width: int
    """Bounding box width of the rendered glyph."""

    height: int
    """Bounding box height of the rendered glyph."""

    x: int
    """Horizontal position of the text origin in rendered glyph"""

    y: int
    """Vertical position of the text origin in rendered glyph"""


@dataclass(slots=True, frozen=True)
class LineMetrics:
    """Line metrics for a given font and size."""

    height: int
    """Full line height including ascender, descender and internal leading."""

    ascender: int
    """Distance between the baseline and the top of the line (positive)."""

    descender: int
    """Distance between the baseline and the bottom of the line (positive)."""

    space_advance: float
    """Horizontal advance of the space character."""


@dataclass(slots=True, frozen=True)
class UnderlineMetrics:
    """Underline metrics for a given font and size."""

    offset: int
    """Pixels below the baseline where the underline stroke starts."""

    thickness: int
    """Stroke height in pixels."""


class AbstractFontFactory(ABC):
    """Backend-agnostic font factory consumed by widgets to lay text out.

    The factory is data-only: it provides metrics and resolves font fallback
    per character, but performs no rendering. Rasterization is the executor's
    responsibility.
    """

    __slots__ = ()

    @property
    @abstractmethod
    def default_size(self) -> int:
        """Default font size, fixed when the window is created."""

    @property
    @abstractmethod
    def symbol_size(self) -> float:
        """Recommended size for symbol-like glyphs (typically default_size * 1.625)."""

    @abstractmethod
    def resolve(
        self, char: str, *, strong: bool = False, italic: bool = False
    ) -> DrawerFont:
        """Return the DrawerFont to use for rendering ``char``.

        Implements per-character font fallback: a single string may require
        several fonts (e.g. Latin -> Noto Sans, CJK -> Noto Sans CJK). Text
        widgets call this method character by character and group the results
        into homogeneous runs before emitting TextArgs.
        """

    @abstractmethod
    def line_metrics(self, font: DrawerFont, size: int) -> LineMetrics:
        """Line metrics for a font and size (vertical layout)."""

    @abstractmethod
    def char_metrics(self, font: DrawerFont, char: str, size: int) -> CharMetrics:
        """Character metrics for a font and size (horizontal layout)."""

    @abstractmethod
    def underline_metrics(self, font: DrawerFont, size: int) -> UnderlineMetrics:
        """Underline position (relative to baseline) and thickness."""

    @property
    def font_height(self) -> int:
        """Shortcut: line height in the default font at the default size."""
        return self.line_metrics(self.resolve(" "), self.default_size).height
