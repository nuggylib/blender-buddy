"""A focusable row standing for one source model on the Models screen.

The sibling of `SectionCard`: same shape — focusable, `enter` posts a message,
navigation stays with the screen — but it carries a `Path` rather than the name
of a screen to push, because what happens to a selected model is not a
navigation decision.
"""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Static


class ModelRow(Static, can_focus=True):
    """One `.blend` file, selectable with `enter`.

    `label` is how the file is shown — the screen passes its path relative to
    the configured directory it was found under, so a model in a subfolder keeps
    that context without repeating the directory prefix on every row. `path` is
    the absolute path the message carries.

    `label` is escaped here rather than at the call site: it is always a
    filename, and a model called `sedan[wip].blend` would otherwise be read as
    markup and rendered with a chunk missing.
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
