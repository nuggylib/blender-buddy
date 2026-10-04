"""A focusable dashboard section that opens a detail screen."""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget


class SectionCard(Vertical, can_focus=True, can_focus_children=False):
    """One focusable section of a hub screen.

    `can_focus_children=False` keeps the focus chain at one stop per section.
    """

    BINDINGS = [Binding("enter", "open", "Open")]

    class Opened(Message):
        """Posted when a card is activated; `target` is a `SCREENS` name."""

        def __init__(self, target: str) -> None:
            super().__init__()
            self.target = target

    def __init__(self, *children: Widget, target: str, **kwargs) -> None:
        super().__init__(*children, **kwargs)
        self._target = target

    def action_open(self) -> None:
        self.post_message(self.Opened(self._target))
