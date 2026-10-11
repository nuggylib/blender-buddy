"""One spec root field at a glance, as a titled box of `label: value` rows."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static


class FieldSummary(Vertical):
    """A titled border around `label: value` rows. Display-only.

    Assign `rows`; children come from `compose` via a `recompose` reactive, as
    in `FixPanel`, so the auto height re-measures. Values render without markup.
    """

    rows: reactive[tuple[tuple[str, str], ...]] = reactive((), recompose=True)

    def __init__(self, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.border_title = title

    def compose(self) -> ComposeResult:
        for label, value in self.rows:
            yield Static(f"{label}: {value}", classes="field-row", markup=False)
