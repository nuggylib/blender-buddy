"""The Models detail screen — the `.blend` files behind each configured directory.

One group per directory in stored order, each ending in one of four states
(missing / unreadable / empty / populated) with a fix step for the problems.
The distinction is the point: an empty directory reads as a healthy `✓ found`
on the dashboard.

The filesystem walk is delegated to the `models` category inside a `@work`
worker; only the `is_dir()` that separates *missing* from the rest runs inline.
"""

from __future__ import annotations

import asyncio
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, cast

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from blender_buddy.models import discovery
from blender_buddy.tui.widgets.fix_panel import FixPanel
from blender_buddy.tui.widgets.model_row import ModelRow

if TYPE_CHECKING:
    from blender_buddy.app import BlenderBuddyApp
    from blender_buddy.config.settings import Settings

_SCANNING = "Scanning…"


class _State(Enum):
    """What a scan concluded about one configured directory."""

    MISSING = auto()
    UNAVAILABLE = auto()
    EMPTY = auto()
    POPULATED = auto()


_MARKERS = {
    _State.MISSING: "[red]✗ not found[/]",
    _State.UNAVAILABLE: "[yellow]⚠ models unavailable — check directory permissions[/]",
    _State.EMPTY: "[yellow]0 models[/]",
}

# One step per *problem* state; POPULATED has nothing to fix, so a healthy page
# shows nothing.
_FIX_STEPS = {
    _State.MISSING: (
        "[b]✗ not found[/] — press `s` to re-point the directory, or create it on disk."
    ),
    _State.UNAVAILABLE: (
        "[b]⚠ models unavailable[/] — the directory exists but can't be read; "
        "check its permissions."
    ),
    _State.EMPTY: (
        f"[b]0 models[/] — confirm this is the directory holding your source "
        f"files. Blender's `.blend1` save backups are ignored on purpose, and "
        f"the scan looks {discovery.DEFAULT_MAX_DEPTH} folders deep."
    ),
}
# Fixed order, so the block doesn't reshuffle between scans.
_STEP_ORDER = (_State.MISSING, _State.UNAVAILABLE, _State.EMPTY)


def _plural(count: int, noun: str, plural: str | None = None) -> str:
    """`1 model` / `2 models`. Spelled out because `directory(s)` is not a word."""
    if count == 1:
        return f"{count} {noun}"
    return f"{count} {plural or noun + 's'}"


class ModelsScreen(Screen):
    """Detail view for the configured source-model directories.

    Navigation mirrors the dashboard: rows are focusable (`ModelRow`), `↑`/`↓`
    and `j`/`k` step through them, `enter` selects one. Only the model rows are
    focus stops — the directory headings and state lines are plain `Static`s.

    Selecting a model currently does nothing but confirm the choice: there is no
    spec to validate against and no live Blender connection to validate through.
    `on_model_row_selected` is the seam that work replaces.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        # One binding per key: Textual expands a comma-joined pair into one
        # binding each, drawing the footer entry twice.
        Binding("down", "app.focus_next", "Move", key_display="↑↓"),
        Binding("j", "app.focus_next", "Move", show=False),
        Binding("up", "app.focus_previous", "Move", show=False),
        Binding("k", "app.focus_previous", "Move", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        settings = cast("BlenderBuddyApp", self.app).settings
        # can_focus=False keeps the scroller out of the row focus chain.
        yield VerticalScroll(
            Static("Models", classes="section-title"),
            Static(_SCANNING, id="models-summary", classes="config-detail"),
            *self._groups(settings),
            id="detail-panel",
            can_focus=False,
        )
        # Outside the scroller, so it survives a long list. Scan fills it.
        yield FixPanel(id="fix-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._scan_models()
        self.watch(self.app, "settings", self._on_settings_changed, init=False)

    async def _on_settings_changed(self, _settings: Settings | None) -> None:
        # The directories changed, so there is no row to restore focus to.
        await self.recompose()
        self._scan_models()

    # -- groups ------------------------------------------------------------

    def _groups(self, settings: Settings) -> list[Vertical]:
        """One shell per configured directory; the worker fills in the rest.

        Indexed by position, not path — a path is not a usable widget id.
        """
        return [
            Vertical(
                Static(escape(directory), classes="config-value models-directory"),
                Static(_SCANNING, id=f"models-state-{index}", classes="config-detail"),
                Vertical(id=f"models-files-{index}", classes="models-files"),
                classes="models-group",
            )
            for index, directory in enumerate(settings.models_directories)
        ]

    def _update(self, selector: str, text: str) -> bool:
        """Set a `Static`'s text; False if a recompose already removed it."""
        try:
            self.query_one(selector, Static).update(text)
        except NoMatches:
            return False
        return True

    # -- workers -----------------------------------------------------------

    @work(exclusive=True, group="models-scan")
    async def _scan_models(self) -> None:
        """Scan each configured directory, off the event loop.

        Sequential rather than gathered, to keep the output ordered.
        """
        settings = cast("BlenderBuddyApp", self.app).settings
        if settings is None:
            return
        total = 0
        seen: set[_State] = set()
        for index, directory in enumerate(settings.models_directories):
            path = Path(directory).expanduser()
            # Separates *missing* from *unreadable*; the scan raises for both.
            if not path.is_dir():
                seen.add(_State.MISSING)
                if not self._update(f"#models-state-{index}", _MARKERS[_State.MISSING]):
                    return
                continue
            try:
                found = await asyncio.to_thread(discovery.find_blend_files, path)
            except OSError:
                seen.add(_State.UNAVAILABLE)
                marker = _MARKERS[_State.UNAVAILABLE]
                if not self._update(f"#models-state-{index}", marker):
                    return
                continue
            total += len(found)
            if not found:
                seen.add(_State.EMPTY)
                if not self._update(f"#models-state-{index}", _MARKERS[_State.EMPTY]):
                    return
                continue
            seen.add(_State.POPULATED)
            if not self._update(f"#models-state-{index}", _plural(len(found), "model")):
                return
            try:
                container = self.query_one(f"#models-files-{index}", Vertical)
            except NoMatches:
                return  # recomposed away mid-scan
            await container.mount_all(
                ModelRow(model, self._label(model, path), classes="model-row")
                for model in found
            )
        summary = (
            f"{_plural(len(settings.models_directories), 'directory', 'directories')}"
            f" · {_plural(total, 'model')}"
        )
        self._update("#models-summary", summary)
        self._show_fix_steps(seen)
        self._focus_first_row()

    def _show_fix_steps(self, seen: set[_State]) -> None:
        """Show a step per problem state that occurred; none hides the panel."""
        try:
            panel = self.query_one("#fix-panel", FixPanel)
        except NoMatches:
            return  # recomposed away mid-scan
        panel.steps = tuple(_FIX_STEPS[state] for state in _STEP_ORDER if state in seen)

    @staticmethod
    def _label(model: Path, root: Path) -> str:
        """The model's path relative to its configured directory."""
        try:
            return str(model.relative_to(root.resolve()))
        except ValueError:
            # The scan resolves its root, so a symlinked dir yields outside paths.
            return model.name

    def _focus_first_row(self) -> None:
        """Focus the first model, unless the user already focused one."""
        if isinstance(self.focused, ModelRow):
            return
        rows = self.query(ModelRow)
        if rows:
            rows.first().focus()

    # -- selection ---------------------------------------------------------

    def on_model_row_selected(self, message: ModelRow.Selected) -> None:
        """Confirm the choice; validation has nothing to run against yet."""
        self.notify(
            f"{message.path.name} selected — model validation is not wired up yet."
        )
