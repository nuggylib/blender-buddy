"""A focusable row standing for one source model on the Models screen."""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static


class ModelRow(Static, can_focus=True):
    """One `.blend` file, selectable with `enter`.

    `label` is how the file is shown (the screen passes its path relative to the
    configured directory); `path` is what the message carries. `label` is
    escaped here because a model named `sedan[wip].blend` would read as markup.
    """

    BINDINGS = [Binding("enter", "select", "Select")]

    class Selected(Message):
        """Posted when the user activates a row. Handled by the Models screen."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    def __init__(self, path: Path, label: str, **kwargs) -> None:
        super().__init__(f"▸ {escape(label)}", **kwargs)
        self.path = path

    def action_select(self) -> None:
        self.post_message(self.Selected(self.path))
