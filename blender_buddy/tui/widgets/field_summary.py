"""One spec root field at a glance, as a titled box of rows and/or item columns."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Static

COLUMN_LENGTH = 10


class FieldSummary(Vertical):
    """A titled border around `label: value` rows, then `items` in columns.

    Assign `rows` and/or `items`; children come from `compose` via `recompose`
    reactives, as in `FixPanel`, so the auto height re-measures. `items` fill
    columns of `COLUMN_LENGTH` top to bottom, left to right. `empty` shows when
    both are empty. Text renders without markup.
    """

    rows: reactive[tuple[tuple[str, str], ...]] = reactive((), recompose=True)
    items: reactive[tuple[str, ...]] = reactive((), recompose=True)

    def __init__(self, title: str, empty: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = title
        self._empty = empty

    def compose(self) -> ComposeResult:
        for label, value in self.rows:
            yield Static(f"{label}: {value}", classes="field-row", markup=False)
        if self.items:
            with Horizontal(classes="field-columns"):
                for start in range(0, len(self.items), COLUMN_LENGTH):
                    with Vertical(classes="field-column"):
                        for item in self.items[start : start + COLUMN_LENGTH]:
                            yield Static(item, classes="field-item", markup=False)
        elif not self.rows and self._empty:
            yield Static(self._empty, classes="field-empty", markup=False)
