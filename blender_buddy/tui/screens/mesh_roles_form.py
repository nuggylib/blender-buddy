"""The mesh roles form — add mesh role after mesh role without leaving.

The role list shows read-only until selected. Each role: type its name, then
its `vtx_grp` pattern; Enter on the pattern writes the role and returns to an
empty name for the next one. The rules live in `specs.mesh_roles`; this screen
only sequences them and writes via `specs.store.add_mesh_role`.
"""

from __future__ import annotations

from pathlib import Path

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

from blender_buddy.specs import mesh_roles, store
from blender_buddy.tui.widgets.field_list import FieldList

_EMPTY = "No mesh roles yet."
_NO_BONES = "Add required bones first."


class MeshRolesFormScreen(Screen):
    """Stay-on form for a spec's mesh roles, pushed as an instance.

    `escape` hides the pattern question back to the name, clears a non-empty
    name, closes the editor from an empty one, and leaves when no editor is
    open. `q` is shadowed: the form holds Inputs.
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "noop", show=False),
    ]

    DEFAULT_CSS = """
    MeshRolesFormScreen #mesh-roles-form {
        height: auto;
        padding: 1 2 0 2;
    }
    MeshRolesFormScreen #role-status, MeshRolesFormScreen #role-vtx-grp-question {
        height: auto;
    }
    MeshRolesFormScreen .editor {
        height: auto;
        display: none;
    }
    MeshRolesFormScreen #role-column {
        height: 1fr;
        padding: 0 2;
    }
    MeshRolesFormScreen #role-list {
        height: 1fr;
        margin-top: 1;
    }
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self._editing = False
        self._name: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="mesh-roles-form"):
            yield Static(
                f"Mesh roles — {escape(self.path.stem)}", classes="section-title"
            )
            yield Static("", id="role-status", classes="config-detail", markup=False)
        with Vertical(id="role-column"):
            with Vertical(id="role-editor", classes="editor"):
                yield Static("Role name", classes="config-detail")
                yield Input(id="role-name")
                question = Vertical(id="role-vtx-grp-question")
                question.display = False
                with question:
                    yield Static(
                        "",
                        id="role-vtx-grp-label",
                        classes="config-detail",
                        markup=False,
                    )
                    yield Input(id="role-vtx-grp")
            yield FieldList("Mesh roles", _EMPTY, id="role-list", classes="field-list")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#role-list", FieldList).focus()
        self._show_roles()

    # -- bindings ----------------------------------------------------------

    def action_back(self) -> None:
        self._status("")
        name = self.query_one("#role-name", Input)
        if not self._editing:
            self.app.pop_screen()
        elif self._name is not None:
            self._drop_question()
            name.focus()
        elif name.value:
            name.value = ""
        else:
            self._editing = False
            self.query_one("#role-editor").display = False
            self.query_one("#role-list", FieldList).focus()

    def action_noop(self) -> None:
        """Absorb `q` so the app's global quit can't fire from the form."""

    # -- the form ----------------------------------------------------------

    @on(FieldList.Selected, "#role-list")
    def _on_selected(self) -> None:
        self._status("")
        if not self._editing:
            document = self._read()
            if document is None:
                return
            if not store.required_bones(document):
                self._status(_NO_BONES)
                return
            self._editing = True
            self.query_one("#role-editor").display = True
        target = "#role-name" if self._name is None else "#role-vtx-grp"
        self.query_one(target, Input).focus()

    @on(Input.Submitted, "#role-name")
    def _on_name(self, event: Input.Submitted) -> None:
        self._status("")
        self._drop_question()
        name = event.value.strip()
        document = self._read()
        if document is None:
            return
        if error := mesh_roles.validate_name(name, store.mesh_roles(document)):
            self._status(error)
            return
        self._name = name
        self.query_one("#role-vtx-grp-label", Static).update(f"vtx_grp for '{name}'")
        self.query_one("#role-vtx-grp-question").display = True
        self.query_one("#role-vtx-grp", Input).focus()

    @on(Input.Submitted, "#role-vtx-grp")
    def _on_vtx_grp(self, event: Input.Submitted) -> None:
        self._status("")
        name = self._name
        if name is None:
            return
        pattern = event.value.strip()
        document = self._read()
        if document is None:
            return
        if error := mesh_roles.validate_vtx_grp(
            pattern, store.required_bones(document)
        ):
            self._status(error)
            return
        try:
            store.add_mesh_role(self.path, name, pattern)
        except (OSError, ValueError) as error:
            self._status(f"Could not write the spec: {_reason(error)}")
            return
        self._drop_question()
        role_name = self.query_one("#role-name", Input)
        role_name.value = ""
        role_name.focus()
        self._show_roles()
        self._status(f"Mesh role '{name}' added.")

    # -- rendering ---------------------------------------------------------

    def _drop_question(self) -> None:
        self._name = None
        self.query_one("#role-vtx-grp", Input).value = ""
        self.query_one("#role-vtx-grp-question").display = False

    def _show_roles(self) -> None:
        document = self._read()
        if document is None:
            return
        self.query_one("#role-list", FieldList).lines = tuple(
            line
            for name, role in store.mesh_roles(document).items()
            for line in [
                (name, 0),
                *([(f"vtx_grp: {role['vtx_grp']}", 1)] if "vtx_grp" in role else []),
            ]
        )

    def _read(self) -> dict | None:
        try:
            return store.read(self.path)
        except (OSError, ValueError) as error:
            self._status(f"Could not read the spec: {_reason(error)}")
            return None

    def _status(self, text: str) -> None:
        self.query_one("#role-status", Static).update(text)


def _reason(error: Exception) -> str:
    return str(getattr(error, "strerror", None) or error)
