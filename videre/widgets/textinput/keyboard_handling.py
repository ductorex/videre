from cursword import get_next_word_end_position, get_previous_word_start_position

from videre.core.shaping import GlyphCursor, ShapedRenderedText


def _visual_next_pos(rendered: ShapedRenderedText, pos: int) -> int:
    """Source position one visual glyph-step to the right of `pos`.
    In a RTL run this *decreases* the source position; in an LTR run
    it increases it. Bridges the per-line glyph cursor with the
    single-int source position stored by `TextInput`."""
    cursor = rendered.source_to_glyph(pos)
    return rendered.glyph_to_source(rendered.next_glyph(cursor))


def _visual_prev_pos(rendered: ShapedRenderedText, pos: int) -> int:
    """Symmetric to `_visual_next_pos`: one glyph-step to the left."""
    cursor = rendered.source_to_glyph(pos)
    return rendered.glyph_to_source(rendered.prev_glyph(cursor))


def _all_word_ends(text: str) -> list[int]:
    """All source positions corresponding to the end of a word, in
    increasing source order. Computed by iterating
    `get_next_word_end_position` from 0, which is cursword's
    Ctrl+Right rule (each call jumps over leading whitespace, then
    over a word, returning the position just past the last word char).
    """
    ends: list[int] = []
    pos = 0
    while True:
        nxt = get_next_word_end_position(text, pos)
        if nxt <= pos:
            break
        ends.append(nxt)
        pos = nxt
    return ends


def _all_word_starts(text: str) -> list[int]:
    """Symmetric to `_all_word_ends` — source positions corresponding
    to the start of a word, computed by iterating
    `get_previous_word_start_position` from `len(text)` (cursword's
    Ctrl+Left rule)."""
    starts: set[int] = set()
    pos = len(text)
    while True:
        prv = get_previous_word_start_position(text, pos)
        if prv >= pos:
            break
        starts.add(prv)
        pos = prv
    return sorted(starts)


def _glyph_key(cursor: GlyphCursor) -> tuple[int, int]:
    """Tuple usable to compare two glyph cursors in visual order
    across lines (line first, then glyph index inside the line)."""
    return (cursor.line_index, cursor.glyph_index)


def _visual_next_word_end(rendered: ShapedRenderedText, text: str, pos: int) -> int:
    """Source position of the next word-end **visually to the right**
    of `pos`. In LTR-only text this matches cursword's
    `get_next_word_end_position`; in RTL or mixed text it picks the
    candidate whose glyph cursor is the smallest one strictly past
    the current cursor in visual order."""
    current = rendered.source_to_glyph(pos)
    current_key = _glyph_key(current)
    best_key: tuple[int, int] | None = None
    best_src: int | None = None
    for end_pos in _all_word_ends(text):
        candidate = rendered.source_to_glyph(end_pos)
        candidate_key = _glyph_key(candidate)
        if candidate_key <= current_key:
            continue
        if best_key is None or candidate_key < best_key:
            best_key = candidate_key
            best_src = end_pos
    if best_src is not None:
        return best_src
    # No word-end visually to the right — jump to end of document
    # (last glyph cursor in visual order).
    if not rendered.line_layouts:
        return pos
    last_line = len(rendered.line_layouts) - 1
    last_glyph = len(rendered.line_layouts[last_line].items)
    return rendered.glyph_to_source(GlyphCursor(last_line, last_glyph))


def _visual_prev_word_start(rendered: ShapedRenderedText, text: str, pos: int) -> int:
    """Symmetric to `_visual_next_word_end`: source position of the
    previous word-start **visually to the left** of `pos`."""
    current = rendered.source_to_glyph(pos)
    current_key = _glyph_key(current)
    best_key: tuple[int, int] | None = None
    best_src: int | None = None
    for start_pos in _all_word_starts(text):
        candidate = rendered.source_to_glyph(start_pos)
        candidate_key = _glyph_key(candidate)
        if candidate_key >= current_key:
            continue
        if best_key is None or candidate_key > best_key:
            best_key = candidate_key
            best_src = start_pos
    if best_src is not None:
        return best_src
    # No word-start visually to the left — clamp to start of document.
    if not rendered.line_layouts:
        return pos
    return rendered.glyph_to_source(GlyphCursor(0, 0))


class Pipeline:
    __slots__ = (
        "_in_text",
        "_in_pos",
        "_in_selection",
        "_rendered",
        "_cursor_is_select_start",
        "out_pos",
        "_out_selection",
        "out_procedure",
    )

    def __init__(
        self,
        *,
        in_text: str,
        in_pos: int,
        selection: tuple[int, int] | None,
        rendered: ShapedRenderedText | None = None,
    ):
        self._in_text = in_text
        self._in_pos = in_pos
        self._in_selection = selection
        # When provided, single-char movement uses visual order (one
        # glyph step on the rendered layout). Without it, falls back to
        # logical-order movement (`pos ± 1`), which matches the legacy
        # behavior — useful for tests or code paths that don't have a
        # rendered layout yet.
        self._rendered = rendered

        self._cursor_is_select_start = False
        self.out_pos = None
        self._out_selection = None
        self.out_procedure = []

    def __repr__(self):
        return (
            f"Pipeline(in_text={self._in_text!r}, in_pos={self._in_pos}, "
            f"in_selection={self._in_selection}, "
            f"cursor_is_select_start={self._cursor_is_select_start}, "
            f"out_pos={self.out_pos}, "
            f"out_selection={self.out_selection}, "
            f"out_procedure={[f.__name__ for f in self.out_procedure]})"
        )

    @property
    def out_selection(self) -> tuple[int | None, int | None]:
        return self._out_selection or (None, None)

    def select_no(self):
        assert not self._in_selection
        self._out_selection = None

    def select_out(self):
        self._out_selection = None

    def select_start(self):
        self._out_selection = (self._in_pos, self._in_pos)

    def select_has(self):
        assert self._in_selection
        self._out_selection = self._in_selection

    def ignore_select(self):
        pass

    def find_cursor_in_select(self):
        assert self._out_selection, f"No selection to find cursor in: {self}"
        assert self._in_pos in self._out_selection
        self._cursor_is_select_start = self._in_pos == self._out_selection[0]

    def move_to_next_char(self):
        if self._rendered is not None:
            self.out_pos = _visual_next_pos(self._rendered, self._in_pos)
        else:
            self.out_pos = min(self._in_pos + 1, len(self._in_text))

    def move_to_previous_char(self):
        if self._rendered is not None:
            self.out_pos = _visual_prev_pos(self._rendered, self._in_pos)
        else:
            self.out_pos = max(0, self._in_pos - 1)

    def move_to_next_word(self):
        if self._rendered is not None:
            self.out_pos = _visual_next_word_end(
                self._rendered, self._in_text, self._in_pos
            )
        else:
            self.out_pos = get_next_word_end_position(self._in_text, self._in_pos)

    def move_to_previous_word(self):
        if self._rendered is not None:
            self.out_pos = _visual_prev_word_start(
                self._rendered, self._in_text, self._in_pos
            )
        else:
            self.out_pos = get_previous_word_start_position(self._in_text, self._in_pos)

    def move_to_select_end(self):
        selection = self._out_selection or self._in_selection
        assert selection, f"No selection to move cursor to end: {self}"
        if selection[0] == selection[1]:
            # We are getting out of an actually empty selection
            # Let's move to next character
            self.move_to_next_char()
        else:
            # Selection is not empty
            # Let's get out of selection
            # and move just to end of selection
            self.out_pos = selection[1]

    def move_to_select_start(self):
        selection = self._out_selection or self._in_selection
        assert selection, f"No selection to move cursor to start: {self}"
        if selection[0] == selection[1]:
            self.move_to_previous_char()
        else:
            self.out_pos = selection[0]

    def update_select(self):
        assert self._out_selection is not None
        assert self.out_pos is not None
        if self._cursor_is_select_start:
            self._out_selection = (self.out_pos, self._out_selection[1])
        else:
            self._out_selection = (self._out_selection[0], self.out_pos)


def compute_key_x(
    text: str,
    cursor: int,
    selection: tuple[int, int] | None,
    ctrl: bool | int,
    shift: bool | int,
    right: bool = True,
    rendered: ShapedRenderedText | None = None,
) -> Pipeline:
    """When `rendered` is supplied, both single-char and word-level
    arrow movement are visual: a step is one glyph (or one word
    boundary) to the right or left of the current caret in visual
    order. Without `rendered`, movement falls back to cursword's
    source-order rules (`cursor ± 1` for arrow, `get_next_word_end_position`
    / `get_previous_word_start_position` for Ctrl+arrow)."""
    pp = Pipeline(in_text=text, in_pos=cursor, selection=selection, rendered=rendered)
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
