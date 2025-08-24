* Layouts
  * ScrollView (1 control)
    * scroll_thickness: int
    * horizontal_scroll: bool
    * vertical_scroll: bool
    * wrap_horizontal: bool
    * wrap_vertical: bool
  * Column
    * horizontal_alignment: Alignment
    * expand_horizontal: bool
  * Row
    * vertical_alignment: Alignment
    * expand_vertical: bool
  * Container (1 control)
    * border: Border
    * padding: Padding
    * background_color: ColorDefinition
    * vertical_alignment: Alignment
    * horizontal_alignment: Alignment
  * RadioGroup (1 control)
    * value: Any | None
    * on_change: Callable[[RadioGroup], None]
    * can_deselect: bool = False
  * Animator (1 control)
    * on_frame: Callable[[Widget, int], None]
* Widgets
  * Button: AbstractButton
    * text: str
    * on_click: Callable[[Button], None]
  * Checkbox: AbstractButton
    * checked: bool = False
    * on_change: Callable[[Checkbox], None]
  * Radio: AbstractButton
    * value: Any  # read-only
  * Text
    * text: str
    * size: int
    * wrap: TextWrap
    * align: TextAlign
  * Label:
    * for_button: AbstractButton | str  # key, read-only
  * Picture
    * src: str | Path | bytes | bytearray | BinaryIO
  * ProgressBar
    * value: float = 0.0
  * Progressing
