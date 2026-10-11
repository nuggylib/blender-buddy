"""The spec detail screen — one spec's contents, and the way to add to them.

Lists `armature.required_bones`. `a` (**Add data**) opens `AddDataModal`, a
picker of the spec's root fields, and routes the choice to that field's form.
The spec is one small file, read inline (like `NewSpecModal`'s inline write)
and re-read on every resume so it reflects whatever a form wrote.
"""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from blender_buddy.specs import store
from blender_buddy.tui.screens.add_data_modal import AddDataModal
from blender_buddy.tui.screens.armature_form import ArmatureFormScreen

_EMPTY = "No required bones yet — press `a` to add data."
_UNREADABLE = "This spec can't be read — see the fix steps on the Specs page."


class SpecDetailScreen(Screen):
    """Detail view for one spec, pushed as an instance (see `screens/CLAUDE.md`).

    `model_type` is the filename stem — the identity, so it titles the page even
    when the file can't be read. `path` is the file the sections are read from.
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        Binding("a", "add_data", "Add data"),
    ]

    def __init__(self, model_type: str, path: Path) -> None:
        super().__init__()
        self.model_type = model_type
        self.path = path
        self._readable = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(
            # Escaped for the same reason `SpecRow` escapes it: a spec called
            # `mech[v2]` would otherwise be read as markup.
            Static(
                f"Spec — {escape(self.model_type)}",
                id="spec-title",
                classes="section-title",
            ),
            Static("Armature", id="armature-title", classes="section-title"),
            Vertical(id="armature-bones"),
            id="detail-panel",
            can_focus=False,
        )
        yield Footer()

    async def on_screen_resume(self) -> None:
        await self._show_armature()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """`a` is disabled while the spec can't be read."""
        if action == "add_data" and not self._readable:
            return None
        return True

    # -- add data ----------------------------------------------------------

    def action_add_data(self) -> None:
        self._add_data()

    @work(exclusive=True, group="add-data")
    async def _add_data(self) -> None:
        """Pick a root field, then open its form. Armature is the only route."""
        field = await self.app.push_screen_wait(AddDataModal())
        if field == "armature":
            self.app.push_screen(ArmatureFormScreen(self.path))

    # -- sections ----------------------------------------------------------

    async def _show_armature(self) -> None:
        try:
            bones = store.required_bones(store.read(self.path))
        except (OSError, ValueError):
            self._readable = False
            rows = [
                Static(_UNREADABLE, id="armature-unreadable", classes="config-detail")
            ]
        else:
            self._readable = True
            rows = [
                Static(bone, classes="bone-row", markup=False) for bone in bones
            ] or [Static(_EMPTY, id="armature-empty", classes="config-detail")]
        self.refresh_bindings()
        container = self.query_one("#armature-bones", Vertical)
        await container.remove_children()
        await container.mount_all(rows)
