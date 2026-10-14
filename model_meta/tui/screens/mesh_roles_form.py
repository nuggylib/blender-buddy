"""The mesh roles form — add mesh role after mesh role, or edit one.

The role list shows read-only, with a cursor. `a` adds: type the role's name,
then check the required bones its vertex group covers; **Add** writes the
inferred `vtx_grp` and returns to an empty name for the next one. Enter on a
role edits it: its name and checks are prefilled, and **Save** writes via
`specs.store.update_mesh_role` and closes. Both follow the same rules, which
live in `specs.mesh_roles`; this screen only sequences them.
"""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import Literal

from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, SelectionList, Static

from model_meta.specs import mesh_roles, store
from model_meta.tui.widgets.field_list import FieldList

_EMPTY = "No mesh roles yet."
_NO_BONES = "Add required bones first."


class MeshRolesFormScreen(Screen):
    """Stay-on form for a spec's mesh roles, pushed as an instance.

    One editor at a time (`_mode`); opening another discards the open one
    unwritten. `escape` in Add hides the bones question back to the name,
    clears a non-empty name, and closes the editor from an empty one; in Edit
    it closes unsaved; with no editor open it leaves. `a` works only with no
    editor open or from the list, so a stray `a` can't discard an edit. `q` is
    shadowed: the form holds Inputs and a Button.
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("a", "add", "Add"),
        Binding("q", "noop", show=False),
    ]

    DEFAULT_CSS = """
    MeshRolesFormScreen #mesh-roles-form {
        height: auto;
        padding: 1 2 0 2;
    }
    MeshRolesFormScreen #role-status, MeshRolesFormScreen #role-bones-question {
        height: auto;
    }
    MeshRolesFormScreen #role-bones {
        height: auto;
        max-height: 8;
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
        self._mode: Literal["add", "edit"] | None = None
        self._name: str | None = None
        self._original: str | None = None
        self._role_names: list[str] = []

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
                question = Vertical(id="role-bones-question")
                question.display = False
                with question:
                    yield Static(
                        "", id="role-bones-label", classes="config-detail", markup=False
                    )
                    yield SelectionList[str](id="role-bones")
                    yield Static(
                        "", id="role-preview", classes="config-detail", markup=False
                    )
                    yield Button("Add", id="confirm-role", variant="primary")
            yield FieldList(
                "Mesh roles", _EMPTY, cursor=True, id="role-list", classes="field-list"
            )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#role-list", FieldList).focus()
        self._show_roles()

    # -- bindings ----------------------------------------------------------

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool:
        if action == "add":
            focused = self.focused
            return self._mode is None or (
                focused is not None and focused.id == "role-list"
            )
        return True

    def action_back(self) -> None:
        self._status("")
        name = self.query_one("#role-name", Input)
        if self._mode is None:
            self.app.pop_screen()
        elif self._mode == "edit":
            self._close()
        elif self._name is not None:
            self._drop_question()
            name.focus()
        elif name.value:
            name.value = ""
        else:
            self._close()

    def action_add(self) -> None:
        self._status("")
        if self._mode != "add":
            if self._gate() is None:
                return
            self._close()
            self._open("add")
        target = "#role-name" if self._name is None else "#role-bones"
        self.query_one(target).focus()

    def action_noop(self) -> None:
        """Absorb `q` so the app's global quit can't fire from the form."""

    # -- editors -----------------------------------------------------------

    @on(FieldList.Selected, "#role-list")
    def _on_selected(self, event: FieldList.Selected) -> None:
        if event.index is None:
            self.action_add()
        else:
            self._edit(self._role_names[event.index])

    def _edit(self, name: str) -> None:
        self._status("")
        if self._mode == "edit" and self._original == name:
            self.query_one("#role-bones").focus()
            return
        document = self._gate()
        if document is None:
            return
        role = store.mesh_roles(document).get(name)
        if role is None:
            self._status(f"'{name}' is no longer a mesh role.")
            self._show_roles()
            return
        self._close()
        self._open("edit")
        self._original = name
        self.query_one("#role-name", Input).value = name
        required = store.required_bones(document)
        pattern = role.get("vtx_grp")
        checked = mesh_roles.matches(pattern, required) if pattern else []
        self._ask(name, required, checked)
        if pattern and not checked:
            self._status(f"Its vtx_grp '{pattern}' matches no required bone.")

    def _gate(self) -> dict | None:
        """A fresh read when the spec has bones to check, else `None` (status set)."""
        document = self._read()
        if document is not None and not store.required_bones(document):
            self._status(_NO_BONES)
            return None
        return document

    def _open(self, mode: Literal["add", "edit"]) -> None:
        self._mode = mode
        self.query_one("#confirm-role", Button).label = (
            "Add" if mode == "add" else "Save"
        )
        self.query_one("#role-editor").display = True
        self.refresh_bindings()

    def _close(self) -> None:
        """Hide the open editor, dropping its in-progress state unwritten."""
        if self._mode is None:
            return
        self._mode = None
        self._original = None
        self._drop_question()
        self.query_one("#role-name", Input).value = ""
        self.query_one("#role-editor").display = False
        self.query_one("#role-list", FieldList).focus()
        self.refresh_bindings()

    # -- the form ----------------------------------------------------------

    @on(Input.Submitted, "#role-name")
    def _on_name(self, event: Input.Submitted) -> None:
        self._status("")
        name = event.value.strip()
        if self._mode == "edit":
            if self._check_name(name) is not None:
                self._name = name
                self.query_one("#role-bones-label", Static).update(
                    f"Bones for '{name}'"
                )
                self.query_one("#role-bones").focus()
            return
        self._drop_question()
        document = self._check_name(name)
        if document is not None:
            self._ask(name, store.required_bones(document))

    @on(SelectionList.SelectedChanged, "#role-bones")
    def _on_bones_changed(self) -> None:
        self._preview()

    @on(Button.Pressed, "#confirm-role")
    def _on_confirm(self) -> None:
        self._status("")
        if self._mode == "edit":
            self._save()
        else:
            self._add()

    def _add(self) -> None:
        name = self._name
        if name is None:
            return
        pattern = self._infer_or_report()
        if pattern is None:
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

    def _save(self) -> None:
        original = self._original
        assert original is not None
        name = self.query_one("#role-name", Input).value.strip()
        if self._check_name(name) is None:
            return
        pattern = self._infer_or_report()
        if pattern is None:
            return
        try:
            store.update_mesh_role(self.path, original, name, pattern)
        except (OSError, ValueError) as error:
            self._status(f"Could not write the spec: {_reason(error)}")
            return
        self._close()
        self._show_roles()
        if name in self._role_names:
            role_list = self.query_one("#role-list", FieldList)
            role_list.highlighted = self._role_names.index(name)
        self._status(f"Mesh role '{name}' saved.")

    # -- rendering ---------------------------------------------------------

    def _check_name(self, name: str) -> dict | None:
        """A fresh read when `name` is valid, ignoring the role being edited."""
        document = self._read()
        if document is None:
            return None
        existing = [
            role for role in store.mesh_roles(document) if role != self._original
        ]
        if error := mesh_roles.validate_name(name, existing):
            self._status(error)
            return None
        return document

    def _ask(
        self, name: str, required: list[str], checked: Collection[str] = ()
    ) -> None:
        """Show the bones question for `name`, `checked` pre-checked."""
        self._name = name
        self.query_one("#role-bones-label", Static).update(f"Bones for '{name}'")
        checklist = self.query_one("#role-bones", SelectionList)
        checklist.clear_options()
        checklist.add_options(
            [(Text(bone), bone, bone in checked) for bone in required]
        )
        if checklist.option_count:
            checklist.highlighted = 0
        self._preview()
        self.query_one("#role-bones-question").display = True
        checklist.focus()

    def _preview(self) -> None:
        preview = self.query_one("#role-preview", Static)
        if (
            self._name is None
            or not self.query_one("#role-bones", SelectionList).selected
        ):
            preview.update("")
            return
        try:
            pattern = self._infer()
        except ValueError as error:
            preview.update(str(error))
            return
        preview.update("" if pattern is None else f"vtx_grp: {pattern}")

    def _infer_or_report(self) -> str | None:
        try:
            return self._infer()
        except ValueError as error:
            self._status(str(error))
            return None

    def _infer(self) -> str | None:
        """The `vtx_grp` for the checked bones on a fresh read; raises `ValueError`."""
        document = self._read()
        if document is None:
            return None
        return mesh_roles.infer_vtx_grp(
            self.query_one("#role-bones", SelectionList).selected,
            store.required_bones(document),
        )

    def _drop_question(self) -> None:
        self._name = None
        self.query_one("#role-bones", SelectionList).clear_options()
        self.query_one("#role-preview", Static).update("")
        self.query_one("#role-bones-question").display = False

    def _show_roles(self) -> None:
        document = self._read()
        if document is None:
            return
        roles = store.mesh_roles(document)
        self._role_names = list(roles)
        self.query_one("#role-list", FieldList).lines = tuple(
            line
            for name, role in roles.items()
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
