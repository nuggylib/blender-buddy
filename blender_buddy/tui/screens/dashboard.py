"""The dashboard screen — the app's landing view.

Displays the three configured anchors — **Blender (top) → Models (middle) →
Godot (bottom)** — each with a lightweight live existence/validity marker so the
user can tell at a glance whether a saved path has since moved or been deleted.

**Layering:** the screen holds no config of its own — it reads `self.app.settings`
(app-level state) and never touches TOML or spawns a subprocess. Cheap file stats
(`is_dir` / `executable_state`) run inline; the one job that walks the filesystem —
counting Godot projects — is delegated to the `godot` category inside a Textual
`@work` worker (via `asyncio.to_thread`), exactly as the setup wizard does, so the
event loop never blocks.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, cast

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from blender_buddy.blender import detect
from blender_buddy.godot import discovery

if TYPE_CHECKING:
    from blender_buddy.app import BlenderBuddyApp
    from blender_buddy.config.settings import Settings

_FOUND = "[green]✓ found[/]"
_MISSING = "[red]✗ not found[/]"


class DashboardScreen(Screen):
    """The landing view: the configured anchors plus live validity markers.

    Reads `self.app.settings` and re-renders whenever it changes (an edit via `s`
    reassigns it). When there is no valid config (`settings is None`) it shows a
    single "run setup" prompt rather than empty section shells.

    Future: live validation results driven by a Blender-polling worker, and
    per-category detail screens pushed on top of this one.
    """

    BINDINGS = [("s", "app.open_setup", "Setup")]

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
                self._blender_section(settings),
                self._models_section(settings),
                self._godot_section(settings),
                id="config-panel",
            )
        yield Footer()

    def on_mount(self) -> None:
        # Kick off the (filesystem-walking) Godot count once the sections exist,
        # and re-render + re-scan whenever the app's config is reassigned. `init`
        # is off so this doesn't fire redundantly against the value compose already
        # read.
        self._scan_godot()
        self.watch(self.app, "settings", self._on_settings_changed, init=False)

    async def _on_settings_changed(self, _settings: Settings | None) -> None:
        await self.recompose()
        self._scan_godot()

    # -- sections ----------------------------------------------------------

    def _blender_section(self, settings: Settings) -> Vertical:
        state = detect.executable_state(settings.blender_executable)
        if state is detect.ExecutableState.OK:
            marker = "[green]✓ executable[/]"
        elif state is detect.ExecutableState.NOT_EXECUTABLE:
            marker = "[yellow]⚠ present, not executable[/]"
        else:
            marker = _MISSING
        version = settings.blender_version or "unknown version"
        return Vertical(
            Static("Blender", classes="section-title"),
            Static(
                f"{escape(settings.blender_executable)}  {marker}",
                id="blender-value",
                classes="config-value",
            ),
            Static(f"Recorded version: {escape(version)}", classes="config-detail"),
            id="section-blender",
            classes="section",
        )

    def _models_section(self, settings: Settings) -> Vertical:
        # One row per configured location, in stored order (the order the user
        # added them in the wizard). The schema and the wizard both enforce at
        # least one, so there is no empty-list state to render.
        rows = [
            Static(
                f"{escape(directory)}  "
                f"{_FOUND if Path(directory).expanduser().is_dir() else _MISSING}",
                classes="config-value models-value",
            )
            for directory in settings.models_directories
        ]
        return Vertical(
            Static("Models", classes="section-title"),
            *rows,
            id="section-models",
            classes="section",
        )

    def _godot_section(self, settings: Settings) -> Vertical:
        found = Path(settings.godot_projects_root).expanduser().is_dir()
        # The count is filled in by `_scan_godot` (it walks the fs); until then show
        # a placeholder, or a dash when the root is missing and there is nothing to
        # scan.
        count = "Scanning…" if found else "—"
        return Vertical(
            Static("Godot", classes="section-title"),
            Static(
                f"{escape(settings.godot_projects_root)}  "
                f"{_FOUND if found else _MISSING}",
                id="godot-value",
                classes="config-value",
            ),
            Static(count, id="godot-count", classes="config-detail"),
            id="section-godot",
            classes="section",
        )

    # -- workers -----------------------------------------------------------

    @work(exclusive=True, group="godot-scan")
    async def _scan_godot(self) -> None:
        """Count Godot projects under the configured root, off the event loop.

        The scan walks the filesystem, so it runs in a thread (like the wizard's).
        A missing root needs no scan (the inline marker already says so); zero
        projects is a valid `0`, and any failure degrades to "count unavailable"
        rather than crashing the screen.
        """
        settings = cast("BlenderBuddyApp", self.app).settings
        if settings is None:
            return
        root = Path(settings.godot_projects_root).expanduser()
        if not root.is_dir():
            return  # inline marker already shows "not found"; leave count at "—"
        try:
            projects = await asyncio.to_thread(discovery.find_projects, root)
            text = f"{len(projects)} Godot project(s) found"
        except OSError:
            text = "Project count unavailable."
        try:
            self.query_one("#godot-count", Static).update(text)
        except NoMatches:
            return  # recomposed away before the scan returned
