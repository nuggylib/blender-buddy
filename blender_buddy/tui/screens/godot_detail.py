"""The Godot detail screen — a placeholder awaiting its real content.

It exists so dashboard navigation is uniform *now*: every section opens
something, and no `enter` is a dead key. The page it will become lists the
discovered projects (the dashboard only counts them) and the export targets each
one offers.
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


class GodotDetailScreen(Screen):
    """Detail view for the configured Godot projects root."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
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
            yield Vertical(
                Static("Godot", classes="section-title"),
                Static(
                    escape(settings.godot_projects_root),
                    id="godot-value",
                    classes="config-value",
                ),
                Static(
                    "The per-project listing and export targets are coming soon.",
                    id="placeholder-note",
                    classes="config-detail",
                ),
                id="detail-panel",
            )
        yield Footer()
