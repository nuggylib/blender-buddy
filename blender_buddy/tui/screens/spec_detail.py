"""The spec detail screen — one spec's contents, and the way to add to them.

Summarizes each root field in a `FieldSummary` (Armature: name and bone count;
the full bone list lives on the armature form). `a` (**Add data**) opens
`AddDataModal`, a picker of the spec's root fields, and routes the choice to
that field's form. The spec is one small file, read inline (like
`NewSpecModal`'s inline write) and re-read on every resume so it reflects
whatever a form wrote.
"""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from blender_buddy.specs import store
from blender_buddy.tui.screens.add_data_modal import AddDataModal
from blender_buddy.tui.screens.armature_form import ArmatureFormScreen
from blender_buddy.tui.widgets.field_summary import FieldSummary

_UNREADABLE = "This spec can't be read — see the fix steps on the Specs page."
_NOT_SET = "not set"


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
        unreadable = Static(_UNREADABLE, id="spec-unreadable", classes="config-detail")
        unreadable.display = False
        yield VerticalScroll(
            # Escaped for the same reason `SpecRow` escapes it: a spec called
            # `mech[v2]` would otherwise be read as markup.
            Static(
                f"Spec — {escape(self.model_type)}",
                id="spec-title",
                classes="section-title",
            ),
            FieldSummary("Armature", id="armature-summary", classes="field-summary"),
            unreadable,
            id="detail-panel",
            can_focus=False,
        )
        yield Footer()

    def on_screen_resume(self) -> None:
        self._show_fields()

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

    def _show_fields(self) -> None:
        try:
            document = store.read(self.path)
        except (OSError, ValueError):
            self._readable = False
        else:
            self._readable = True
            self.query_one("#armature-summary", FieldSummary).rows = (
                ("Name", store.armature_name(document) or _NOT_SET),
                ("Bones", str(len(store.required_bones(document)))),
            )
        for summary in self.query(FieldSummary):
            summary.display = self._readable
        self.query_one("#spec-unreadable", Static).display = not self._readable
        self.refresh_bindings()
