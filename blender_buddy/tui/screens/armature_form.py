"""The armature form — name the armature, and add required bones without leaving.

Each field shows read-only until selected. Enter in the armature-name editor
saves it (blank clears it). Each bone: type the name, answer one inline
question per segment with no known inverse, then confirm a pre-checked
checklist of its variants. The name logic lives in `specs.bones`; this screen
only sequences it and writes via `specs.store.update_armature`.

**Full chain first:** variants are computed only once `next_missing` returns
`None`, and a bone's pending inverse answers are written together, once.

Parenting: check parents from the required bones, choose, check children, and
Add writes what `specs.parenting.infer` returns — the same call the live
preview shows, so the preview is exactly what gets written.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    SelectionList,
    Static,
)

from blender_buddy.specs import bones, parenting, store
from blender_buddy.tui.widgets.field_list import FieldList

_EMPTY = "No required bones yet."
_NO_PARENTING = "No parenting yet."
_NO_PARENTS = "Add required bones first."
_SKIPPED = "Bones with a `{n}` segment can't be parented."
_NOT_SET = "not set"
_VIEWS = {
    "name": "#armature-name-view",
    "bones": "#bone-list",
    "parenting": "#parenting-list",
}
_EDITORS = {
    "name": "#armature-name",
    "bones": "#bone-editor",
    "parenting": "#parenting-editor",
}
_FIELDS = {view[1:]: field for field, view in _VIEWS.items()}


@dataclass
class _Bone:
    """The bone being added. `file_inverses` is the spec's map when it started."""

    name: str
    file_inverses: dict[str, str]
    required: list[str]
    history: list[tuple[str, str]] = field(default_factory=list)
    written: tuple[str, ...] = ()
    asking: str | None = None
    choices: list[str] = field(default_factory=list)

    def pending(self) -> dict[str, str]:
        answers: dict[str, str] = {}
        for segment, answer in self.history:
            answers.update(bones.pairs(segment, answer))
        return answers

    def known(self) -> dict[str, str]:
        return {**self.file_inverses, **self.pending()}


class ArmatureFormScreen(Screen):
    """Stay-on form for the armature's name and bones, pushed as an instance.

    Fields show read-only in `FieldList`s; selecting one opens its editor and
    closes any other. The name and each confirmed bone are written on Enter, so
    leaving never loses work. `escape` closes the name editor unsaved, steps
    back one question mid-bone, clears a non-empty idle bone field, closes
    the editor from an empty one, and leaves when no editor is open. `q` is
    shadowed: the form holds Inputs and a Button.
    """

    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("q", "noop", show=False),
    ]

    DEFAULT_CSS = """
    ArmatureFormScreen #armature-form {
        height: auto;
        padding: 1 2 0 2;
    }
    ArmatureFormScreen #bone-status, ArmatureFormScreen #armature-name-view {
        height: auto;
    }
    ArmatureFormScreen #armature-columns {
        height: 1fr;
        padding: 0 2;
    }
    ArmatureFormScreen #armature-columns > Vertical {
        width: 1fr;
    }
    ArmatureFormScreen #bone-column {
        margin-right: 2;
    }
    ArmatureFormScreen .editor {
        height: auto;
        display: none;
    }
    ArmatureFormScreen #bone-question, ArmatureFormScreen #parent-question,
    ArmatureFormScreen #parent-picker {
        height: auto;
    }
    ArmatureFormScreen #bone-variants {
        height: auto;
        max-height: 12;
    }
    ArmatureFormScreen #parent-bones {
        height: auto;
        max-height: 8;
    }
    ArmatureFormScreen #child-bones {
        height: auto;
        max-height: 8;
    }
    ArmatureFormScreen #bone-list, ArmatureFormScreen #parenting-list {
        height: 1fr;
        margin-top: 1;
    }
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self._bone: _Bone | None = None
        self._saved_name = ""
        self._parents: list[str] = []
        self._skipped = False
        self._picked: list[str] = []
        self._editing: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="armature-form"):
            yield Static(
                f"Armature — {escape(self.path.stem)}", classes="section-title"
            )
            yield FieldList(
                "Armature name",
                _NOT_SET,
                id="armature-name-view",
                classes="field-list",
            )
            armature_name = Input(id="armature-name", classes="editor")
            armature_name.border_title = "Armature name"
            yield armature_name
            yield Static("", id="bone-status", classes="config-detail", markup=False)
        with Horizontal(id="armature-columns"):
            with Vertical(id="bone-column"):
                with Vertical(id="bone-editor", classes="editor"):
                    yield Static("Bone name", classes="config-detail")
                    yield Input(id="bone-name")
                    yield Vertical(id="bone-question")
                yield FieldList(
                    "Required bones", _EMPTY, id="bone-list", classes="field-list"
                )
            with Vertical(id="parenting-column"):
                with Vertical(id="parenting-editor", classes="editor"):
                    with Vertical(id="parent-picker"):
                        yield Static("Parent bones", classes="config-detail")
                        yield SelectionList[str](id="parent-bones")
                        yield Button("Choose children", id="choose-children")
                    yield Static(
                        _SKIPPED,
                        id="parent-bones-skipped",
                        classes="config-detail",
                        markup=False,
                    )
                    yield Vertical(id="parent-question")
                yield FieldList(
                    "Parenting",
                    _NO_PARENTING,
                    id="parenting-list",
                    classes="field-list",
                )
        yield Footer()

    async def on_mount(self) -> None:
        try:
            self._saved_name = store.armature_name(store.read(self.path))
        except (OSError, ValueError):
            pass  # `_show_bones` reports it
        self._show_name()
        self.query_one("#bone-list", FieldList).focus()
        self._show_bones()

    # -- bindings ----------------------------------------------------------

    async def action_back(self) -> None:
        self._status("")
        if self._editing == "parenting":
            parents = self.query_one("#parent-bones", SelectionList)
            if self._picked:
                await self._drop_children()
            elif parents.selected:
                parents.deselect_all()
            else:
                await self._close()
            return
        if self._editing == "bones":
            await self._back_bone()
        elif self._editing == "name":
            await self._close()
        else:
            self.app.pop_screen()

    async def _back_bone(self) -> None:
        name = self.query_one("#bone-name", Input)
        bone = self._bone
        if bone is None:
            if name.value:
                name.value = ""
            else:
                await self._close()
            return
        if bone.history:
            segment, answer = bone.history.pop()
            await self._ask(segment, answer)
            return
        self._bone = None
        await self._clear_question()
        name.focus()

    def action_noop(self) -> None:
        """Absorb `q` so the app's global quit can't fire mid-bone."""

    # -- editors -----------------------------------------------------------

    @on(FieldList.Selected)
    async def _on_selected(self, event: FieldList.Selected) -> None:
        await self._edit(_FIELDS[event.control.id or ""])

    async def _edit(self, field: str) -> None:
        """Open `field`'s editor, closing any other; one is open at a time."""
        self._status("")
        if field == "parenting" and not self._parents:
            self._status(_SKIPPED if self._skipped else _NO_PARENTS)
            return
        if self._editing != field:
            await self._close()
            self._editing = field
            self.query_one(_EDITORS[field]).display = True
            if field == "name":
                self.query_one("#armature-name", Input).value = self._saved_name
                self.query_one(_VIEWS[field]).display = False
        self._focus_editor()

    def _focus_editor(self) -> None:
        if self._editing == "name":
            self.query_one("#armature-name", Input).focus()
        elif self._editing == "bones":
            self.query_one("#bone-name", Input).focus()
        elif self._editing == "parenting":
            self.query_one("#child-bones" if self._picked else "#parent-bones").focus()

    async def _close(self) -> None:
        """Hide the open editor, dropping its in-progress state unwritten."""
        field, self._editing = self._editing, None
        if field is None:
            return
        if field == "name":
            self.query_one(_VIEWS[field]).display = True
        elif field == "bones":
            self._bone = None
            await self._clear_question()
            self.query_one("#bone-name", Input).value = ""
        else:
            await self._drop_children()
            self.query_one("#parent-bones", SelectionList).deselect_all()
        self.query_one(_EDITORS[field]).display = False
        self.query_one(_VIEWS[field], FieldList).focus()

    # -- the form ----------------------------------------------------------

    @on(Input.Submitted, "#armature-name")
    async def _on_armature_name(self, event: Input.Submitted) -> None:
        self._status("")
        name = event.value.strip()
        if len(name.encode("utf-8")) > bones.MAX_BYTES:
            self._status(f"An armature name can be at most {bones.MAX_BYTES} bytes.")
            return
        if not self._write(object_name=name):
            return
        self._saved_name = name
        self._show_name()
        await self._close()
        self._status("Armature name saved." if name else "Armature name cleared.")

    @on(Input.Submitted, "#bone-name")
    async def _on_name(self, event: Input.Submitted) -> None:
        self._status("")
        self._bone = None
        await self._clear_question()
        name = event.value.strip()
        if error := bones.validate_name(name):
            self._status(error)
            return
        try:
            document = store.read(self.path)
        except (OSError, ValueError) as error:
            self._status(f"Could not read the spec: {_reason(error)}")
            return
        required = store.required_bones(document)
        if name in required:
            self._status(f"'{name}' is already required.")
            return
        self._bone = _Bone(name, dict(store.bone_name_inverses(document)), required)
        if not await self._advance():
            self._bone = None

    @on(Input.Submitted, "#bone-inverse")
    async def _on_inverse(self, event: Input.Submitted) -> None:
        self._status("")
        bone = self._bone
        if bone is None or bone.asking is None:
            return
        segment = bone.asking
        if error := bones.validate_inverse(segment, event.value, bone.known()):
            self._status(error)
            return
        bone.history.append((segment, bones.normalize_inverse(event.value)))
        if not await self._advance():
            bone.history.pop()
            bone.asking = segment

    @on(Button.Pressed, "#add-bones")
    async def _on_add(self) -> None:
        bone = self._bone
        if bone is None:
            return
        selected = set(self.query_one("#bone-variants", SelectionList).selected)
        await self._add([name for name in bone.choices if name in selected])

    @on(Button.Pressed, "#choose-children")
    async def _on_choose_children(self) -> None:
        self._status("")
        checked = set(self.query_one("#parent-bones", SelectionList).selected)
        picked = [name for name in self._parents if name in checked]
        if not picked:
            self._status("Check at least one parent.")
            return
        try:
            document = store.read(self.path)
        except (OSError, ValueError) as error:
            self._status(f"Could not read the spec: {_reason(error)}")
            return
        required = store.required_bones(document)
        resolved = parenting.resolve(store.parenting_map(document), required)
        above = set().union(*(parenting.ancestors(p, resolved) for p in picked))
        eligible = [
            name
            for name in required
            if name not in checked
            and name not in resolved
            and name not in above
            and not parenting.has_placeholder_segment(name)
        ]
        if not eligible:
            self._status("Every other bone already has a parent.")
            return
        self._picked = picked
        self.query_one("#parent-picker").display = False
        children = SelectionList[str](
            *((Text(name), name, False) for name in eligible), id="child-bones"
        )
        await self.query_one("#parent-question", Vertical).mount(
            Static(
                f"Children of {', '.join(picked)}",
                id="child-bones-label",
                classes="config-detail",
                markup=False,
            ),
            children,
            Static("", id="parenting-preview", classes="config-detail", markup=False),
            Button("Add", id="add-children", variant="primary"),
        )
        children.focus()

    @on(SelectionList.SelectedChanged, "#child-bones")
    def _on_children_changed(self) -> None:
        preview = self.query_one("#parenting-preview", Static)
        try:
            result = self._infer()
        except ValueError as error:
            preview.update(str(error))
            return
        if result is None or not result[1]:
            preview.update("")
            return
        required, entries, _ = result
        count = len(parenting.pairs(entries, required))
        lines = ["  " * depth + text for text, depth in _entry_lines(entries)]
        preview.update("\n".join([*lines, f"{count} pairs"]))

    @on(Button.Pressed, "#add-children")
    async def _on_add_children(self) -> None:
        self._status("")
        try:
            result = self._infer()
        except ValueError as error:
            self._status(str(error))
            return
        if result is None:
            return
        required, entries, current = result
        if not entries:
            self._status("Check at least one child.")
            return
        if not parenting.is_valid(parenting.merge(current, entries), required):
            self._status("The spec changed — choose the parents again.")
            return
        if not self._write(add_parenting=entries):
            return
        self.query_one("#parent-bones", SelectionList).deselect_all()
        await self._drop_children()
        self._show_bones()
        self._status("Parenting saved.")

    def _infer(
        self,
    ) -> tuple[list[str], dict[str, list[str]], dict[str, list[str]]] | None:
        """(required, inferred entries, current map) from a fresh read, or `None`.

        Raises `ValueError` when a checked child can't be paired with a parent.
        """
        if not self._picked:
            return None
        try:
            document = store.read(self.path)
        except (OSError, ValueError) as error:
            self._status(f"Could not read the spec: {_reason(error)}")
            return None
        required = store.required_bones(document)
        current = store.parenting_map(document)
        entries = parenting.infer(
            self._picked,
            self.query_one("#child-bones", SelectionList).selected,
            required,
            current,
        )
        return required, entries, current

    async def _advance(self) -> bool:
        """Ask the next unmapped segment, or finish the chain. False on failure."""
        bone = self._bone
        assert bone is not None
        known = bone.known()
        segment = bones.next_missing(bone.name, known)
        if segment is not None:
            await self._ask(segment, "")
            return True
        names = bones.variants(bone.name, known)
        too_long = next((name for name in names if bones.validate_name(name)), None)
        if too_long is not None:
            self._status(
                f"'{too_long}' would exceed {bones.MAX_BYTES} bytes — "
                "use a shorter inverse."
            )
            return False
        if bone.history:
            pending = bone.pending()
            if not self._write(drop_inverses=bone.written, set_inverses=pending):
                return False
            bone.written = tuple(pending)
        bone.asking = None
        bone.choices = [name for name in names if name not in bone.required]
        if bone.choices:
            await self._show_checklist(bone.choices)
            return True
        return await self._add([])

    async def _add(self, variants: list[str]) -> bool:
        bone = self._bone
        assert bone is not None
        if not self._write(add_bones=[bone.name, *variants]):
            return False
        self._bone = None
        await self._clear_question()
        name = self.query_one("#bone-name", Input)
        name.value = ""
        name.focus()
        self._show_bones()
        return True

    def _write(self, **changes) -> bool:
        try:
            store.update_armature(self.path, **changes)
        except (OSError, ValueError) as error:
            self._status(f"Could not write the spec: {_reason(error)}")
            return False
        return True

    # -- rendering ---------------------------------------------------------

    async def _ask(self, segment: str, answer: str) -> None:
        assert self._bone is not None
        self._bone.asking = segment
        await self._clear_question()
        inverse = Input(answer, id="bone-inverse")
        await self.query_one("#bone-question", Vertical).mount(
            Static(
                f"Inverse of `{segment}` — leave blank if it has none",
                id="bone-inverse-label",
                classes="config-detail",
                markup=False,
            ),
            inverse,
        )
        inverse.focus()

    async def _show_checklist(self, choices: list[str]) -> None:
        await self._clear_question()
        add = Button("Add", id="add-bones", variant="primary")
        await self.query_one("#bone-question", Vertical).mount(
            SelectionList[str](
                *((Text(name), name, True) for name in choices), id="bone-variants"
            ),
            add,
        )
        add.focus()

    async def _clear_question(self) -> None:
        await self.query_one("#bone-question", Vertical).remove_children()

    async def _drop_children(self) -> None:
        """Back to the parent checklist, its checks kept."""
        self._picked = []
        await self.query_one("#parent-question", Vertical).remove_children()
        picker = self.query_one("#parent-picker")
        picker.display = bool(self._parents)
        if picker.display:
            self.query_one("#parent-bones", SelectionList).focus()

    def _show_name(self) -> None:
        self.query_one("#armature-name-view", FieldList).lines = (
            ((self._saved_name, 0),) if self._saved_name else ()
        )

    def _show_bones(self) -> None:
        try:
            document = store.read(self.path)
        except (OSError, ValueError) as error:
            self._status(f"Could not read the spec: {_reason(error)}")
            return
        required = store.required_bones(document)
        self.query_one("#bone-list", FieldList).lines = tuple(
            (name, 0) for name in required
        )
        self._show_parents(required)
        self.query_one("#parenting-list", FieldList).lines = tuple(
            _entry_lines(store.parenting_map(document))
        )

    def _show_parents(self, required: list[str]) -> None:
        self._parents = [
            name for name in required if not parenting.has_placeholder_segment(name)
        ]
        parents = self.query_one("#parent-bones", SelectionList)
        checked = set(parents.selected)
        highlighted = parents.highlighted
        parents.clear_options()
        parents.add_options(
            [(Text(name), name, name in checked) for name in self._parents]
        )
        if self._parents:
            parents.highlighted = min(highlighted or 0, len(self._parents) - 1)
        self.query_one("#parent-picker").display = (
            bool(self._parents) and not self._picked
        )
        self._skipped = len(self._parents) != len(required)
        self.query_one("#parent-bones-skipped").display = self._skipped

    def _status(self, text: str) -> None:
        self.query_one("#bone-status", Static).update(text)


def _entry_lines(entries: dict[str, list[str]]) -> list[tuple[str, int]]:
    """Each key at depth 0, followed by its child patterns at depth 1."""
    return [
        line
        for key, patterns in entries.items()
        for line in [(key, 0), *((pattern, 1) for pattern in patterns)]
    ]


def _reason(error: Exception) -> str:
    return str(getattr(error, "strerror", None) or error)
