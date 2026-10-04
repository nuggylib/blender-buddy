"""The Models detail screen — a placeholder awaiting its real content.

It exists so dashboard navigation is uniform *now*: every section opens
something, and no `enter` is a dead key. The page it will become groups the
`.blend` files found under each configured directory, distinguishes a *missing*
directory from a *present but empty* one, and closes with the steps to fix
either.

Deliberately thin: it lists the configured directories and nothing more. The
four-state per-directory rendering arrives with the scan that can tell those
states apart, rather than being written twice.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rich.markup import escape
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

if TYPE_CHECKING:
    from blender_buddy.app import BlenderBuddyApp


class ModelsScreen(Screen):
    """Detail view for the configured source-model directories."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("s", "app.open_setup", "Setup"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        settings = cast("BlenderBuddyApp", self.app).settings
        if settings is None:
            yield Static(
                "Setup incomplete or unreadable — press 's' to run setup.",
                id="setup-prompt",
            )
        else:
            # Stored order — the order they were added in the wizard, and the
            # order the dashboard lists them.
            rows = [
                Static(escape(directory), classes="config-value models-value")
                for directory in settings.models_directories
            ]
            yield Vertical(
                Static("Models", classes="section-title"),
                *rows,
                Static(
                    "The per-model listing is coming soon.",
                    id="placeholder-note",
                    classes="config-detail",
                ),
                id="detail-panel",
            )
        yield Footer()
