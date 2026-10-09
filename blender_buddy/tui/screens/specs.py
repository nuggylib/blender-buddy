"""The Specs screen — the validation specs on disk.

One focusable row per `specs/*.json`, with a fix block for the files that could
not be read. Zero specs is the normal state on a fresh install, not a problem,
so it gets a plain note and contributes no fix step.

Unlike its sibling detail screens it has **no `#setup-prompt` branch**, and the
reason is now stronger rather than weaker: it reads `self.app.specs_dir`, a path
derived from the config *path* rather than its contents, so the page lists and
works identically with an absent or corrupt config.

The directory listing parses JSON per file, so it runs in a `@work` worker via
`asyncio.to_thread` — never on the event loop.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.css.query import NoMatches
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from blender_buddy.specs import store
from blender_buddy.specs.store import SpecState
from blender_buddy.tui.widgets.fix_panel import FixPanel
from blender_buddy.tui.widgets.spec_row import SpecRow

if TYPE_CHECKING:
    from blender_buddy.app import BlenderBuddyApp

_LOADING = "Loading…"
_EMPTY = "No specs yet — press `n` to create one."

_MARKERS = {
    SpecState.UNREADABLE: "[yellow]⚠ unreadable[/]",
    SpecState.MISMATCHED: "[yellow]⚠ name mismatch[/]",
}

# One step per *problem* state; OK has nothing to fix, so a healthy page shows
# nothing. An empty directory is not a problem and is not listed here.
_FIX_STEPS = {
    SpecState.UNREADABLE: (
        "[b]⚠ unreadable[/] — the file is not valid JSON; open it in an editor "
        "to repair it, or delete it and create the spec again."
    ),
    SpecState.MISMATCHED: (
        "[b]⚠ name mismatch[/] — the file's `model_type` disagrees with its "
        "filename. The filename wins; edit the file to match it."
    ),
}
# Fixed order, so the block doesn't reshuffle between loads.
_STEP_ORDER = (SpecState.UNREADABLE, SpecState.MISMATCHED)


def _plural(count: int) -> str:
    """`1 spec` / `2 specs`."""
    return f"{count} spec" if count == 1 else f"{count} specs"


class SpecsScreen(Screen):
    """Detail view for the validation specs in `specs/`.

    Navigation mirrors the Models screen: rows are focusable (`SpecRow`), `↑`/`↓`
    and `j`/`k` step through them, `enter` selects one. The rows are the only
    focus stops — the title and summary lines are plain `Static`s.

    Selecting a spec currently does nothing but confirm the choice: nothing
    persists a "current spec" yet. `on_spec_row_selected` is the seam that work
    replaces.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("s", "app.open_setup", "Setup"),
        # One binding per key: Textual expands a comma-joined pair into one
        # binding each, drawing the footer entry twice.
        Binding("down", "app.focus_next", "Move", key_display="↑↓"),
        Binding("j", "app.focus_next", "Move", show=False),
        Binding("up", "app.focus_previous", "Move", show=False),
        Binding("k", "app.focus_previous", "Move", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        # can_focus=False keeps the scroller out of the row focus chain.
        yield VerticalScroll(
            Static("Specs", classes="section-title"),
            Static(_LOADING, id="specs-summary", classes="config-detail"),
            id="detail-panel",
            can_focus=False,
        )
        # Outside the scroller, so it survives a long list. The load fills it.
        yield FixPanel(id="fix-panel")
        yield Footer()

    def on_mount(self) -> None:
        self._load_specs()

    # -- workers -----------------------------------------------------------

    @work(exclusive=True, group="specs-load")
    async def _load_specs(self) -> None:
        """List the specs directory off the event loop (it parses JSON)."""
        specs_dir = cast("BlenderBuddyApp", self.app).specs_dir
        entries = await asyncio.to_thread(store.list_specs, specs_dir)

        try:
            panel = self.query_one("#detail-panel", VerticalScroll)
            summary = self.query_one("#specs-summary", Static)
        except NoMatches:
            return  # popped or recomposed away mid-load

        if not entries:
            # Zero specs is the normal state on a fresh install, so this is a
            # plain note rather than a count of nothing — and no fix step.
            summary.display = False
            await panel.mount(Static(_EMPTY, id="specs-empty", classes="config-detail"))
            self._show_fix_steps(set())
            return

        summary.display = True
        summary.update(_plural(len(entries)))
        await panel.mount_all(
            SpecRow(
                entry.path,
                entry.model_type,
                marker=_MARKERS.get(entry.state, ""),
                classes="spec-row",
            )
            for entry in entries
        )
        self._show_fix_steps({entry.state for entry in entries})
        self._focus_first_row()

    def _show_fix_steps(self, seen: set[SpecState]) -> None:
        """Show a step per problem state that occurred; none hides the panel."""
        try:
            panel = self.query_one("#fix-panel", FixPanel)
        except NoMatches:
            return  # recomposed away mid-load
        panel.steps = tuple(_FIX_STEPS[state] for state in _STEP_ORDER if state in seen)

    def _focus_first_row(self) -> None:
        """Focus the first spec, unless the user already focused one."""
        if isinstance(self.focused, SpecRow):
            return
        rows = self.query(SpecRow)
        if rows:
            rows.first().focus()

    # -- selection ---------------------------------------------------------

    def on_spec_row_selected(self, message: SpecRow.Selected) -> None:
        """Confirm the choice; nothing persists a current spec yet."""
        self.notify(
            f"{message.model_type} selected — spec selection is not wired up yet."
        )
