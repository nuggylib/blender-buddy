"""The Specs screen — a placeholder awaiting its real content.

It exists so the dashboard's Specs card is not a dead key. The page it will
become creates, selects, and edits the validation specs the rest of the tool
checks models against.

Unlike its sibling detail screens it has **no `#setup-prompt` branch**: it reads
no settings at all, so it renders identically in every config state and cannot
raise on a `--setup` cancellation push.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class SpecsScreen(Screen):
    """Detail view for validation specs — a placeholder awaiting its content."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("s", "app.open_setup", "Setup"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static("Specs", classes="section-title"),
            Static(
                "Spec creation, selection, and the validation they drive are "
                "coming soon.",
                id="placeholder-note",
                classes="config-detail",
            ),
            id="detail-panel",
        )
        yield Footer()
