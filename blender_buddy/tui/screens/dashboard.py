"""The dashboard screen — the app's landing view."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class DashboardScreen(Screen):
    """Placeholder dashboard.

    Future: displays live validation results as reactive state driven by a
    background worker polling the active Blender scene; selecting a category
    pushes a detail screen with fix steps.
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Blender Buddy — no Blender scene connected yet.")
        yield Footer()
