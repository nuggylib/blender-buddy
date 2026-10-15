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

    With `cursor=True`, up/down move `highlighted` over the items (depth-0
    lines; a depth-1 line belongs to the item above it) instead of scrolling,
    and `Selected.index` names the highlighted item.

    `marked` holds line indices whose rows get `.field-list-marked`; assigning
    `lines` clears it, so set it after them.
    """

    BINDINGS = [
        Binding("enter", "select", "Edit"),
        Binding("up", "cursor_up", show=False),
        Binding("down", "cursor_down", show=False),
    ]

    lines: reactive[tuple[tuple[str, int], ...]] = reactive((), recompose=True)
    highlighted: reactive[int | None] = reactive(None)
    marked: reactive[frozenset[int]] = reactive(frozenset())

    class Selected(Message):
        """Posted when the user selects the list. Handled by the owning screen."""

        def __init__(self, field_list: FieldList, index: int | None) -> None:
            super().__init__()
            self.field_list = field_list
            self.index = index

        @property
        def control(self) -> FieldList:
            return self.field_list

    def __init__(self, title: str, empty: str, *, cursor: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.border_title = title
        self.empty = empty
        self.cursor = cursor

    def compose(self) -> ComposeResult:
        if not self.lines:
            yield Static(self.empty, classes="field-list-empty", markup=False)
        lines = zip(self.lines, self._items(), strict=True)
        for index, ((text, depth), item) in enumerate(lines):
            classes = "field-list-row field-list-child" if depth else "field-list-row"
            if not depth and item == self.highlighted:
                classes += " field-list-highlighted"
            if index in self.marked:
                classes += " field-list-marked"
            yield Static(text, classes=classes, markup=False)

    def watch_lines(self) -> None:
        self.marked = frozenset()
        if not self.cursor:
            return
        count = self._count()
        if not count:
            self.highlighted = None
        else:
            self.highlighted = min(self.highlighted or 0, count - 1)
        self.call_after_refresh(self._scroll_to_highlighted)

    def watch_highlighted(self) -> None:
        rows = self.query(".field-list-row")
        for row, (_, depth), item in zip(rows, self.lines, self._items(), strict=False):
            row.set_class(
                not depth and item == self.highlighted, "field-list-highlighted"
            )
        self._scroll_to_highlighted()

    def watch_marked(self) -> None:
        for index, row in enumerate(self.query(".field-list-row")):
            row.set_class(index in self.marked, "field-list-marked")

    def action_cursor_up(self) -> None:
        if self.cursor:
            self._move(-1)
        else:
            self.action_scroll_up()

    def action_cursor_down(self) -> None:
        if self.cursor:
            self._move(1)
        else:
            self.action_scroll_down()

    def action_select(self) -> None:
        self.post_message(self.Selected(self, self.highlighted))

    def on_click(self, event: events.Click) -> None:
        if self.cursor and event.widget is not None:
            rows = list(self.query(".field-list-row"))
            if event.widget in rows:
                self.highlighted = self._items()[rows.index(event.widget)]
        self.post_message(self.Selected(self, self.highlighted))

    def _items(self) -> list[int]:
        """The item index of each line: depth-1 lines take the item above them."""
        items, item = [], -1
        for _, depth in self.lines:
            item += not depth
            items.append(item)
        return items

    def _count(self) -> int:
        return sum(1 for _, depth in self.lines if not depth)

    def _move(self, step: int) -> None:
        if self.highlighted is not None:
            self.highlighted = max(0, min(self.highlighted + step, self._count() - 1))

    def _scroll_to_highlighted(self) -> None:
        row = next(iter(self.query(".field-list-highlighted")), None)
        if row is not None:
            self.scroll_to_widget(row, animate=False)
