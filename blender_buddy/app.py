"""Root Blender Buddy application and its entry point."""

import argparse
import asyncio
import sys
from pathlib import Path

from textual import work
from textual.app import App

from blender_buddy import __version__
from blender_buddy.config import paths, store
from blender_buddy.config.settings import Settings
from blender_buddy.tui.screens.dashboard import DashboardScreen
from blender_buddy.tui.screens.setup_wizard import SetupWizard


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

    Boot routing keys off the config file: a *valid* config goes straight to the
    dashboard, an *absent* one runs the first-time setup wizard, and a *corrupt*
    one boots the dashboard with a non-blocking recovery notice (never
    auto-overwritten). `config_path` is injectable so tests — and the future
    `blender-buddy setup` entry — can point at a throwaway file instead of the
    real `platformdirs` location.

    `force_setup` (the `--setup` flag) opens the wizard on top of whatever the
    config state routes to, rather than bypassing that routing: with no config
    it *is* the first run (cancel exits), and with a config it edits over the
    dashboard (cancel returns there) — so the same "no valid config + cancel"
    input never strands a config-less dashboard.
    """

    CSS_PATH = _resource_path("app.tcss")
    BINDINGS = [("q", "quit", "Quit")]
    SCREENS = {"dashboard": DashboardScreen}

    def __init__(
        self, config_path: Path | None = None, force_setup: bool = False
    ) -> None:
        super().__init__()
        self._config_path = config_path or paths.config_file()
        self._force_setup = force_setup

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        state, _ = store.load(self._config_path)
        if state == store.ABSENT:
            # No config: run first-time setup (cancel exits, no partial config).
            # `--setup` makes no difference here — there is nothing to edit.
            self._first_run()
            return
        # A config exists (valid or corrupt): the dashboard is always reachable.
        self.push_screen("dashboard")
        if state == store.CORRUPT:
            self.notify(
                "Config unreadable — press 's' to re-run setup.",
                severity="warning",
                timeout=10,
            )
        if self._force_setup:
            # --setup: open the wizard over the dashboard so a cancel returns
            # somewhere sensible. Edit mode when the config is valid; fresh
            # (but non-overwriting) when it is corrupt.
            self._open_setup()

    @work(exclusive=True, group="setup")
    async def _first_run(self) -> None:
        """Absent config → run the wizard. Save only on completion; a cancel
        (dismiss `None`) writes nothing and exits, so no partial config lingers."""
        settings = await self.push_screen_wait(SetupWizard())
        if settings is None:
            self.exit()
            return
        self._save(settings)
        self.push_screen("dashboard")

    def action_open_setup(self) -> None:
        """Bound to the dashboard's `s` key (`app.open_setup`)."""
        self._open_setup()

    @work(exclusive=True, group="setup")
    async def _open_setup(self) -> None:
        """Re-run setup over the dashboard. Pre-populates from a valid config
        (edit mode); a cancel keeps the prior config untouched.

        `exclusive` (shared with `_first_run`) guards against a fast double
        activation stacking two wizard screens."""
        state, settings = store.load(self._config_path)
        existing = settings if state == store.VALID else None
        result = await self.push_screen_wait(SetupWizard(existing=existing))
        if result is not None and self._save(result):
            self.notify("Setup saved.")

    def _save(self, settings: Settings) -> bool:
        """Persist the config, surfacing an OSError as an error notice instead of
        letting it crash the worker and lose the user's just-entered answers.

        Returns whether the write succeeded. `store.save` writes atomically, so a
        failure leaves no partial config behind (and boot re-runs setup)."""
        try:
            store.save(self._config_path, settings)
        except OSError as error:
            self.notify(
                f"Could not save config: {error.strerror or error}",
                severity="error",
                timeout=10,
            )
            return False
        return True


def main(argv: list[str] | None = None) -> None:
    """Console-script / ``python -m blender_buddy`` entry point.

    Bare invocation launches the TUI (unchanged behavior). ``--version`` and
    ``--check`` are non-interactive utilities the release pipeline relies on;
    ``--setup`` launches straight into the setup wizard to re-run first-time
    setup. ``argv`` is injectable so the CLI is unit-testable without
    ``subprocess``.
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
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Launch straight into the setup wizard to re-run first-time setup.",
    )
    args = parser.parse_args(argv)

    if args.check:
        # Imported here so the packaging smoke test lives with the pipeline
        # concerns, not in the app's import-time surface.
        from blender_buddy.diagnostics import run_headless_check

        asyncio.run(run_headless_check())
        return

    BlenderBuddyApp(force_setup=args.setup).run()


if __name__ == "__main__":
    main()
