"""The Models detail screen — the source `.blend` files behind each configured
models directory.

One group per configured directory, in stored order (the order they were added
in the wizard, and the order the dashboard lists them). Each group ends in one
of four states, and the distinction is the point of the page: a directory that
*exists* but holds no models reads as a healthy `✓ found` on the dashboard, which
is exactly how a mis-pointed directory hides. So **missing**, **unreadable**,
**empty**, and **populated** each render differently and each gets its own fix
step at the bottom of the page.

**Layering:** no TOML, no `subprocess`. The screen reads `self.app.settings`
(app-level state) and delegates the filesystem *walk* to the `models` category
inside a Textual `@work` worker (via `asyncio.to_thread`), so the event loop
never blocks. The cheap `is_dir()` that separates *missing* from the rest runs
inline.
"""

from __future__ import annotations

import asyncio
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
from blender_buddy.tui.widgets.model_row import ModelRow

if TYPE_CHECKING:
    from blender_buddy.app import BlenderBuddyApp
    from blender_buddy.config.settings import Settings

_SCANNING = "Scanning…"
_MISSING = "[red]✗ not found[/]"
_UNAVAILABLE = "[yellow]⚠ models unavailable — check directory permissions[/]"
_EMPTY = "[yellow]0 models[/]"

_FIX_STEPS = [
    "[b]✗ not found[/] — press `s` to re-point the directory, or create it on disk.",
    "[b]⚠ models unavailable[/] — the directory exists but can't be read; "
    "check its permissions.",
    "[b]0 models[/] — the directory is empty of models. Confirm it is the one "
    "holding your source files; Blender's `.blend1` save backups are ignored "
    "on purpose.",
    f"[b]A model is missing from a list[/] — it may sit deeper than "
    f"{discovery.DEFAULT_MAX_DEPTH} folders below the configured directory.",
]


def _plural(count: int, noun: str, plural: str | None = None) -> str:
    """`1 model` / `2 models`. Spelled out rather than the `model(s)` shorthand
    used elsewhere because this page also counts *directories*, and
    `directory(s)` is not a word."""
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
        ("s", "app.open_setup", "Setup"),
        # One binding per key, not comma-joined keys: Textual expands those into
        # a separate binding each, so a shown pair draws its footer entry twice.
        Binding("down", "app.focus_next", "Move", key_display="↑↓"),
        Binding("j", "app.focus_next", "Move", show=False),
        Binding("up", "app.focus_previous", "Move", show=False),
        Binding("k", "app.focus_previous", "Move", show=False),
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
            # The one scrolling page in the app — a models directory can hold
            # any number of files. `can_focus=False` keeps the scroller itself
            # out of the row focus chain (ScrollableContainer opts in by
            # default), while focusing a row still scrolls it into view.
            yield VerticalScroll(
                Static("Models", classes="section-title"),
                Static(_SCANNING, id="models-summary", classes="config-detail"),
                *self._groups(settings),
                Static("How to fix issues", id="fix-heading", classes="section-title"),
                *(
                    Static(f"• {step}", classes="config-detail fix-step")
                    for step in _FIX_STEPS
                ),
                id="detail-panel",
                can_focus=False,
            )
        yield Footer()

    def on_mount(self) -> None:
        self._scan_models()
        self.watch(self.app, "settings", self._on_settings_changed, init=False)

    async def _on_settings_changed(self, _settings: Settings | None) -> None:
        # The configured directories themselves changed, so there is no row to
        # restore focus to — the scan re-focuses the first one it mounts.
        await self.recompose()
        self._scan_models()

    # -- groups ------------------------------------------------------------

    def _groups(self, settings: Settings) -> list[Vertical]:
        """One shell per configured directory; the worker fills in the rest.

        Both the state line and the row container are indexed by position rather
        than by path, because a path is not a usable widget id (slashes, dots)
        and two directories could differ only in characters an id would mangle.
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
        """Set a `Static`'s text, tolerating a recompose that removed it.

        Returns whether the widget was still there — the worker uses that to
        stop early rather than keep scanning for a screen that has moved on.
        """
        try:
            self.query_one(selector, Static).update(text)
        except NoMatches:
            return False
        return True

    # -- workers -----------------------------------------------------------

    @work(exclusive=True, group="models-scan")
    async def _scan_models(self) -> None:
        """Scan each configured directory, off the event loop.

        Sequential rather than gathered: the directories are few, the output is
        ordered, and one slow directory holding up the rest is a better failure
        than rows appearing out of order. `exclusive` means a recompose-driven
        rescan cancels the one in flight instead of racing it.
        """
        settings = cast("BlenderBuddyApp", self.app).settings
        if settings is None:
            return
        total = 0
        for index, directory in enumerate(settings.models_directories):
            path = Path(directory).expanduser()
            # `is_dir()` is what separates *missing* from *unreadable*: the scan
            # raises for both, and conflating them would tell the user to fix
            # permissions on a directory that isn't there.
            if not path.is_dir():
                if not self._update(f"#models-state-{index}", _MISSING):
                    return
                continue
            try:
                found = await asyncio.to_thread(discovery.find_blend_files, path)
            except OSError:
                if not self._update(f"#models-state-{index}", _UNAVAILABLE):
                    return
                continue
            total += len(found)
            state = _EMPTY if not found else _plural(len(found), "model")
            if not self._update(f"#models-state-{index}", state):
                return
            if found:
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
        self._focus_first_row()

    @staticmethod
    def _label(model: Path, root: Path) -> str:
        """How a row is shown: the model's path *relative to* the configured
        directory, so a model in a subfolder keeps that context without
        repeating the directory prefix on every row."""
        try:
            return str(model.relative_to(root.resolve()))
        except ValueError:
            # The scan resolves its root, so a symlinked configured directory
            # can yield paths outside the unresolved `root` we were handed.
            return model.name

    def _focus_first_row(self) -> None:
        """Put focus on the first model once there is one to focus.

        Rows don't exist until the scan mounts them, so this runs at the end of
        the scan rather than on mount. It yields to anything the user already
        focused while waiting.
        """
        if isinstance(self.focused, ModelRow):
            return
        rows = self.query(ModelRow)
        if rows:
            rows.first().focus()

    # -- selection ---------------------------------------------------------

    def on_model_row_selected(self, message: ModelRow.Selected) -> None:
        """Confirm the choice and say plainly that nothing acts on it yet.

        Validating a model needs a spec to check against and a live Blender
        connection to check through; neither exists. This is the seam that work
        replaces — the message and its `path` are already right.
        """
        self.notify(
            f"{message.path.name} selected — model validation is not wired up yet."
        )
