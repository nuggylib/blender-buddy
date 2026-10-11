"""The armature form — name the armature, and add required bones without leaving.

Enter in the armature-name field saves it (blank clears it). Each bone: type the name, answer one inline question per segment with no known
inverse, then confirm a pre-checked checklist of its variants. The name logic
lives in `specs.bones`; this screen only sequences it and writes via
`specs.store.update_armature`.

**Full chain first:** variants are computed only once `next_missing` returns
`None`, and a bone's pending inverse answers are written together, once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rich.markup import escape
from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Input, SelectionList, Static

from blender_buddy.specs import bones, store

_EMPTY = "No required bones yet."


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

    The name and each confirmed bone are written on Enter, so leaving never
    loses work. `escape` reverts an unsaved armature-name edit, steps back one
    question mid-bone, clears a non-empty idle bone field, and leaves from an
    empty one. `q` is shadowed: the form holds Inputs
    and a Button.
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
    ArmatureFormScreen #bone-question {
        height: auto;
    }
    ArmatureFormScreen #bone-variants {
        height: auto;
        max-height: 12;
    }
    ArmatureFormScreen #bone-status {
        height: auto;
    }
    ArmatureFormScreen #bone-list-title {
        margin-top: 1;
        padding: 0 2;
    }
    ArmatureFormScreen #bone-list {
        height: 1fr;
        padding: 0 2;
    }
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
        self._bone: _Bone | None = None
        self._saved_name = ""

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="armature-form"):
            yield Static(
                f"Armature — {escape(self.path.stem)}", classes="section-title"
            )
            yield Static("Armature name", classes="config-detail")
            yield Input(id="armature-name")
            yield Static("Bone name", classes="config-detail")
            yield Input(id="bone-name")
            yield Vertical(id="bone-question")
            yield Static("", id="bone-status", classes="config-detail", markup=False)
        yield Static("Required bones", id="bone-list-title", classes="section-title")
        yield VerticalScroll(id="bone-list", can_focus=False)
        yield Footer()

    async def on_mount(self) -> None:
        try:
            self._saved_name = store.armature_name(store.read(self.path))
        except (OSError, ValueError):
            pass  # `_show_bones` reports it
        self.query_one("#armature-name", Input).value = self._saved_name
        self.query_one("#bone-name", Input).focus()
        await self._show_bones()

    # -- bindings ----------------------------------------------------------

    async def action_back(self) -> None:
        self._status("")
        armature_name = self.query_one("#armature-name", Input)
        if armature_name.has_focus and armature_name.value != self._saved_name:
            armature_name.value = self._saved_name
            return
        bone = self._bone
        if bone is None:
            name = self.query_one("#bone-name", Input)
            if name.value:
                name.value = ""
            else:
                self.app.pop_screen()
            return
        if bone.history:
            segment, answer = bone.history.pop()
            await self._ask(segment, answer)
            return
        self._bone = None
        await self._clear_question()
        self.query_one("#bone-name", Input).focus()

    def action_noop(self) -> None:
        """Absorb `q` so the app's global quit can't fire mid-bone."""

    # -- the form ----------------------------------------------------------

    @on(Input.Submitted, "#armature-name")
    def _on_armature_name(self, event: Input.Submitted) -> None:
        self._status("")
        name = event.value.strip()
        if len(name.encode("utf-8")) > bones.MAX_BYTES:
            self._status(f"An armature name can be at most {bones.MAX_BYTES} bytes.")
            return
        if not self._write(object_name=name):
            return
        self._saved_name = name
        event.input.value = name
        self._status("Armature name saved." if name else "Armature name cleared.")
        if self._bone is None:
            self.query_one("#bone-name", Input).focus()

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
        await self._show_bones()
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

    async def _show_bones(self) -> None:
        try:
            required = store.required_bones(store.read(self.path))
        except (OSError, ValueError) as error:
            self._status(f"Could not read the spec: {_reason(error)}")
            return
        rows = [
            Static(name, classes="bone-row", markup=False) for name in required
        ] or [Static(_EMPTY, id="bone-list-empty", classes="config-detail")]
        bone_list = self.query_one("#bone-list", VerticalScroll)
        await bone_list.remove_children()
        await bone_list.mount_all(rows)

    def _status(self, text: str) -> None:
        self.query_one("#bone-status", Static).update(text)


def _reason(error: Exception) -> str:
    return str(getattr(error, "strerror", None) or error)
