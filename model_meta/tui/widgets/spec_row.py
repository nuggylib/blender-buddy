"""A focusable row standing for one validation spec on the Specs screen."""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static


class SpecRow(Static, can_focus=True):
    """One spec file, selectable with `enter`.

    `model_type` is the filename stem — the spec's identity — and is what the
    row is labeled with; `marker` is an optional state note rendered beside it.
    The message carries both the name and the `path`, because a caller may want
    either. `model_type` is escaped here: a spec called `mech[v2]` would
    otherwise be read as markup and render with a chunk missing.
    """

    BINDINGS = [Binding("enter", "select", "Select")]

    class Selected(Message):
        """Posted when the user activates a row. Handled by the Specs screen."""

        def __init__(self, path: Path, model_type: str) -> None:
            super().__init__()
            self.path = path
            self.model_type = model_type

    def __init__(self, path: Path, model_type: str, marker: str = "", **kwargs) -> None:
        label = f"▸ {escape(model_type)}"
        super().__init__(f"{label}  {marker}" if marker else label, **kwargs)
        self.path = path
        self.model_type = model_type

    def action_select(self) -> None:
        self.post_message(self.Selected(self.path, self.model_type))
