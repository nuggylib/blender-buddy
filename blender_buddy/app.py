"""Root Blender Buddy application and its entry point."""

from textual.app import App

from blender_buddy.tui.screens.dashboard import DashboardScreen


class BlenderBuddyApp(App):
    """The Blender Buddy TUI.

    This is the spine the product hangs off of: future work adds reactive
    validation state driven by a Blender-polling worker, plus category detail
    screens pushed on top of the dashboard.
    """

    CSS_PATH = "app.tcss"
    BINDINGS = [("q", "quit", "Quit")]
    SCREENS = {"dashboard": DashboardScreen}

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.push_screen("dashboard")


def main() -> None:
    """Console-script / ``python -m blender_buddy`` entry point."""
    BlenderBuddyApp().run()


if __name__ == "__main__":
    main()
