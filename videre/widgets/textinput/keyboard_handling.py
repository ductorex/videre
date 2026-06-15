from videre.core.rendering_result import CursorState, TextRenderingResult


class Pipeline:
    """Mini state machine that turns one arrow-key press into a new
    cursor position + selection. Backend-agnostic: the visual
    movement primitives (`next_visual`, `next_visual_word`, ...) are
    methods of the rendering result, so the same Pipeline works with
    the legacy (source-order) and shaped (bidi-aware) renderers.

    The cursor's `state` is opaque — the Pipeline never inspects it,
    it just receives `in_state` and emits `out_state` paired with
    `out_pos`. TextInput stores both side by side.
    """

    __slots__ = (
        "_in_text",
        "_in_state",
        "_in_selection",
        "_rendered",
        "_cursor_is_select_start",
        "out_state",
        "_out_selection",
        "out_procedure",
    )

    def __init__(
        self,
        *,
        in_text: str,
        in_state: CursorState,
        selection: tuple[int, int] | None,
        rendered: TextRenderingResult,
    ):
        self._in_text = in_text
        self._in_state = in_state
        self._in_selection = selection
        self._rendered = rendered

        self._cursor_is_select_start = False
        self.out_state: CursorState = in_state
        self._out_selection: tuple[int, int] | None = None
        self.out_procedure = []

    def __repr__(self):
        return (
            f"Pipeline(in_text={self._in_text!r}, in_pos={self._in_state.pos}, "
            f"in_selection={self._in_selection}, "
            f"cursor_is_select_start={self._cursor_is_select_start}, "
            f"out_pos={self.out_state.pos}, "
            f"out_selection={self.out_selection}, "
            f"out_procedure={[f.__name__ for f in self.out_procedure]})"
        )

    @property
    def out_pos(self) -> int:
        return self.out_state.pos

    @property
    def out_selection(self) -> tuple[int | None, int | None]:
        return self._out_selection or (None, None)

    def select_no(self):
        assert not self._in_selection
        self._out_selection = None

    def select_out(self):
        self._out_selection = None

    def select_start(self):
        self._out_selection = (self._in_state.visual_pos, self._in_state.visual_pos)

    def select_has(self):
        assert self._in_selection
        self._out_selection = self._in_selection

    def ignore_select(self):
        pass

    def find_cursor_in_select(self):
        assert self._out_selection, f"No selection to find cursor in: {self}"
        assert self._in_state.visual_pos in self._out_selection
        self._cursor_is_select_start = (
            self._in_state.visual_pos == self._out_selection[0]
        )

    def move_to_next_char(self):
        self.out_state = self._step_char(forward=True)

    def move_to_previous_char(self):
        self.out_state = self._step_char(forward=False)

    def _step_char(self, *, forward: bool) -> CursorState:
        """One visual glyph-step. The renderer already aligns each step on an
        edit-unit boundary (a grapheme for the shaped backend, a codepoint for
        the legacy one), so there is nothing to snap here."""
        step = self._rendered.next_visual if forward else self._rendered.prev_visual
        return step(self._in_state)

    def move_to_next_word(self):
        self.out_state = self._rendered.next_visual_word(self._in_state, self._in_text)

    def move_to_previous_word(self):
        self.out_state = self._rendered.prev_visual_word(self._in_state, self._in_text)

    def move_to_select_end(self):
        selection = self._out_selection or self._in_selection
        assert selection, f"No selection to move cursor to end: {self}"
        if selection[0] == selection[1]:
            # Empty selection — degrade to one-char-right.
            self.move_to_next_char()
        else:
            # Real selection — jump to its end. The bounds are in
            # visual order, so derive the state from a visual position.
            self.out_state = self._rendered.visual_state_at(selection[1])

    def move_to_select_start(self):
        selection = self._out_selection or self._in_selection
        assert selection, f"No selection to move cursor to start: {self}"
        if selection[0] == selection[1]:
            self.move_to_previous_char()
        else:
            self.out_state = self._rendered.visual_state_at(selection[0])

    def update_select(self):
        assert self._out_selection is not None
        if self._cursor_is_select_start:
            self._out_selection = (self.out_state.visual_pos, self._out_selection[1])
        else:
            self._out_selection = (self._out_selection[0], self.out_state.visual_pos)


def compute_key_x(
    text: str,
    cursor_state: CursorState,
    selection: tuple[int, int] | None,
    ctrl: bool | int,
    shift: bool | int,
    rendered: TextRenderingResult,
    right: bool = True,
) -> Pipeline:
    """Compute the new cursor position / selection after an arrow-key
    press. Movement primitives are pulled from `rendered` (the
    `TextRenderingResult` for the current text), so Pipeline doesn't
    know whether the underlying renderer is the legacy source-order
    one or the bidi-aware shaped one. `cursor_state` is the opaque
    navigation state the backend handed out for the previous cursor
    position; the new state is exposed as `Pipeline.out_state`.

    Per-character moves land on edit-unit boundaries for free: the renderer's
    `next_visual` / `prev_visual` already step by edit unit (grapheme for the
    shaped backend, codepoint for the legacy one).
    """
    pp = Pipeline(
        in_text=text, in_state=cursor_state, selection=selection, rendered=rendered
    )
    proc_1_get_select = None
    proc_2_set_select = None
    proc_3_move_cursor = None
    proc_4_update_select = None

    if right:
        move_char = pp.move_to_next_char
        move_word = pp.move_to_next_word
        move_select = pp.move_to_select_end
    else:
        move_char = pp.move_to_previous_char
        move_word = pp.move_to_previous_word
        move_select = pp.move_to_select_start

    if shift:
        if selection:
            proc_1_get_select = pp.select_has
        else:
            proc_1_get_select = pp.select_start
        proc_2_set_select = pp.find_cursor_in_select
        proc_4_update_select = pp.update_select
    else:
        if selection:
            proc_1_get_select = pp.select_out
        else:
            proc_1_get_select = pp.select_no
        proc_2_set_select = pp.ignore_select
        proc_4_update_select = pp.ignore_select

    if ctrl:
        proc_3_move_cursor = move_word
    elif selection and not shift:
        proc_3_move_cursor = move_select
    else:
        proc_3_move_cursor = move_char

    pp.out_procedure = [
        proc_1_get_select,
        proc_2_set_select,
        proc_3_move_cursor,
        proc_4_update_select,
    ]
    for proc in pp.out_procedure:
        proc()

    assert pp.out_pos is not None
    return pp
