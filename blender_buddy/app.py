"""Root Blender Buddy application and its entry point."""

import argparse
import asyncio
import sys
from pathlib import Path

from textual.app import App

from blender_buddy import __version__
from blender_buddy.tui.screens.dashboard import DashboardScreen


def _resource_path(name: str) -> Path:
    """Resolve a bundled data file both when frozen and from a source checkout.

    In a PyInstaller build ``sys.frozen`` is set and ``sys._MEIPASS`` points at
    the extracted bundle root; ``collect_data_files("blender_buddy")`` ships our
    data under the preserved ``blender_buddy/`` package prefix, so we join that
    explicitly rather than guessing from the filesystem. From a normal checkout
    the file sits next to this module.
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "blender_buddy" / name  # type: ignore[attr-defined]
    return Path(__file__).parent / name


class BlenderBuddyApp(App):
    """The Blender Buddy TUI.

    This is the spine the product hangs off of: future work adds reactive
    validation state driven by a Blender-polling worker, plus category detail
    screens pushed on top of the dashboard.
    """

    CSS_PATH = _resource_path("app.tcss")
    BINDINGS = [("q", "quit", "Quit")]
    SCREENS = {"dashboard": DashboardScreen}

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.push_screen("dashboard")


def main(argv: list[str] | None = None) -> None:
    """Console-script / ``python -m blender_buddy`` entry point.

    Bare invocation launches the TUI (unchanged behavior). ``--version`` and
    ``--check`` are non-interactive utilities the release pipeline relies on;
    ``argv`` is injectable so the CLI is unit-testable without ``subprocess``.
    """
    parser = argparse.ArgumentParser(
        prog="blender-buddy",
        description="TUI to expedite building Godot-ready game models in Blender.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Boot the app headlessly and exit 0 if it launches (smoke test).",
    )
    args = parser.parse_args(argv)

    if args.check:
        # Imported here so the packaging smoke test lives with the pipeline
        # concerns, not in the app's import-time surface.
        from blender_buddy.diagnostics import run_headless_check

        asyncio.run(run_headless_check())
        return

    BlenderBuddyApp().run()


if __name__ == "__main__":
    main()
