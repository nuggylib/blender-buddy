"""The Blender detail screen — a placeholder awaiting its real content.

It exists so dashboard navigation is uniform *now*: every section opens
something, and no `enter` is a dead key. The page it will become shows the live
`blender --version` probe result and the scene-connection state, once the
`blender` category's IPC client stops being a stub.
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


class BlenderDetailScreen(Screen):
    """Detail view for the configured Blender executable."""

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        settings = cast("BlenderBuddyApp", self.app).settings
        yield Vertical(
            Static("Blender", classes="section-title"),
            Static(
                escape(settings.blender_executable),
                id="blender-value",
                classes="config-value",
            ),
            Static(
                f"Recorded version: "
                f"{escape(settings.blender_version or 'unknown version')}",
                classes="config-detail",
            ),
            Static(
                "Live version probe and scene-connection details are coming soon.",
                id="placeholder-note",
                classes="config-detail",
            ),
            id="detail-panel",
        )
        yield Footer()
