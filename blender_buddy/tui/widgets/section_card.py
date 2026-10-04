"""A focusable dashboard section that opens a detail screen.

The dashboard is a hub: each section summarizes one configured anchor and leads
to a page with the full details and the steps to fix what's wrong. This widget
is the "leads to" half — a `Vertical` that can hold focus and turns `enter` into
a message naming the screen to push.

**Why a message and not a `push_screen` call:** the card knows *which* screen it
stands for, but navigation is the screen stack's business, and the dashboard owns
that. Posting a message keeps the card reusable by any future hub screen and
keeps the push in one place.
"""

from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widget import Widget


class SectionCard(Vertical, can_focus=True, can_focus_children=False):
    """One focusable section of a hub screen.

    `can_focus_children=False` keeps the hub's focus chain at exactly one stop
    per section: sections hold only `Static`s today, but a `Button` added to one
    later would otherwise become a focus stop of its own and break the
    "arrow keys step through sections" contract.
    """

    BINDINGS = [Binding("enter", "open", "Open")]

    class Opened(Message):
        """Posted when the user activates a card. Handled by the hub screen.

        `target` is a name registered in `BlenderBuddyApp.SCREENS`, not a screen
        instance — the house convention is to push landing views by name.
        """

        def __init__(self, target: str) -> None:
            super().__init__()
            self.target = target

    def __init__(self, *children: Widget, target: str, **kwargs) -> None:
        super().__init__(*children, **kwargs)
        self._target = target

    def action_open(self) -> None:
        self.post_message(self.Opened(self._target))
