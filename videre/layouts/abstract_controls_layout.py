from typing import Sequence

from videre.layouts.abstractlayout import AbstractLayout
from videre.widgets.widget import Widget


class AbstractControlsLayout(AbstractLayout):
    __slots__ = ()

    @property
    def controls(self) -> list[Widget]:
        return self._controls()

    @controls.setter
    def controls(self, controls: Sequence[Widget]):
        self._set_controls(controls)
