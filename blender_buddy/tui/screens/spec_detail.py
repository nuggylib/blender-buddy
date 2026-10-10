"""The spec detail screen — a placeholder awaiting the spec's contents.

It exists so `enter` on a `SpecRow` opens something *now*, keeping navigation
uniform with every other row and card in the app. The page it will become shows
and edits the spec document itself.
"""

from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class SpecDetailScreen(Screen):
    """Stub detail view for one spec. Shows which spec, and nothing else yet.

    Takes the spec it names as a constructor argument and is **not** registered
    in `SCREENS` — see `screens/CLAUDE.md` on why this is a named exemption to
    the read-app-state rule rather than a break from it.

    `model_type` is the filename stem, the spec's identity, so there is nothing
    to read from the file to title the page — which is why this screen touches
    no filesystem at all. It reads no `Settings` either, so it has no
    `#setup-prompt` branch.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("s", "app.open_setup", "Setup"),
    ]

    def __init__(self, model_type: str) -> None:
        super().__init__()
        self.model_type = model_type

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            # Escaped for the same reason `SpecRow` escapes it: a spec called
            # `mech[v2]` would otherwise be read as markup.
            Static(
                f"Spec — {escape(self.model_type)}",
                id="spec-title",
                classes="section-title",
            ),
            Static(
                "Viewing and editing a spec's contents is coming soon.",
                id="placeholder-note",
                classes="config-detail",
            ),
            id="detail-panel",
        )
        yield Footer()
