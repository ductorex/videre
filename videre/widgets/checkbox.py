"""
https://en.wikipedia.org/wiki/Check_mark
⍻ 	U+237B 	NOT CHECK MARK
☐ 	U+2610 	BALLOT BOX
☑ 	U+2611 	BALLOT BOX WITH CHECK
✅ 	U+2705 	WHITE HEAVY CHECK MARK
✓ 	U+2713 	CHECK MARK
✔ 	U+2714 	HEAVY CHECK MARK
𐄂 	U+10102 	AEGEAN CHECK MARK
𝤿 	U+1D93F 	SIGNWRITING MOVEMENT-WALLPLANE CHECK SMALL
𝥀 	U+1D940 	SIGNWRITING MOVEMENT-WALLPLANE CHECK MEDIUM
𝥁 	U+1D941 	SIGNWRITING MOVEMENT-WALLPLANE CHECK LARGE
🗸 	U+1F5F8 	LIGHT CHECK MARK
🗹 	U+1F5F9 	BALLOT BOX WITH BOLD CHECK
🮱 	U+1FBB1 	INVERSE CHECK MARK
"""

from videre.layouts.div import OnClickType
from videre.widgets.abstract_check_button import AbstractCheckButton


class Checkbox(AbstractCheckButton):
    __wprops__ = {"name"}
    __slots__ = ()

    def __init__(self, checked=False, on_change: OnClickType | None = None, **kwargs):
        super().__init__(**kwargs)
        self.checked = checked
        self.on_change = on_change

    @property
    def checked(self) -> bool:
        return self._get_checked()

    @checked.setter
    def checked(self, value: bool):
        prev = self._get_checked()
        if prev != value:
            self._set_checked(value)
            if self._on_click:
                self._on_click(self)

    @property
    def on_change(self) -> OnClickType | None:
        return self._on_click

    @on_change.setter
    def on_change(self, callback: OnClickType | None):
        if self._on_click is not callback:
            self._on_click = callback
            self.update()
