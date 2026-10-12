"""One spec field's contents as a titled, scrollable, read-only list to select."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static


class FieldList(VerticalScroll, can_focus=True):
    """A titled border around `(text, depth)` lines; `enter` or a click selects it.

    Assign `lines`; children come from `compose` via a `recompose` reactive, as
    in `FixPanel`. Depth 1 lines get `.field-list-child`. Text renders without
    markup. `empty` shows when there are no lines.
    """

    BINDINGS = [Binding("enter", "select", "Edit")]

    lines: reactive[tuple[tuple[str, int], ...]] = reactive((), recompose=True)

    class Selected(Message):
        """Posted when the user selects the list. Handled by the owning screen."""

        def __init__(self, field_list: FieldList) -> None:
            super().__init__()
            self.field_list = field_list

        @property
        def control(self) -> FieldList:
            return self.field_list

    def __init__(self, title: str, empty: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = title
        self.empty = empty

    def compose(self) -> ComposeResult:
        if not self.lines:
            yield Static(self.empty, classes="field-list-empty", markup=False)
        for text, depth in self.lines:
            classes = "field-list-row field-list-child" if depth else "field-list-row"
            yield Static(text, classes=classes, markup=False)

    def action_select(self) -> None:
        self.post_message(self.Selected(self))

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Selected(self))
