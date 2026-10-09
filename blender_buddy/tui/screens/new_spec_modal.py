"""The new-spec modal — ask for a model-type name and create its spec.

The spec document has four top-level sections, two of them maps of maps. Asking
for all of it up front would be a ten-step wizard; asking for the *name* and
writing a complete empty-valued skeleton gets a valid file on disk in two
keypresses and leaves every field to a later edit surface.

**Layering:** the screen validates nothing itself and writes nothing itself — the
name rules live in `specs.naming` and the write in `specs.store`. The write is a
single small file, done inline (like `app._save` for the config): no worker,
nothing to block the event loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from blender_buddy.config import paths
from blender_buddy.specs import naming, store

if TYPE_CHECKING:
    from blender_buddy.app import BlenderBuddyApp


class NewSpecModal(ModalScreen[Path | None]):
    """Ask for a model-type name and create its spec. Returns the path, or None.

    Takes **no constructor arguments** — it reads `self.app.specs_dir` — so any
    screen can open it with one `await`:

        @work
        async def _new_spec(self) -> None:
            path = await self.app.push_screen_wait(NewSpecModal())

    `escape` cancels. `q` is bound to a no-op purely to shadow the app's global
    quit while the modal is up: a focused `Input` already swallows a typed `q` as
    text, but a focused `Button` would otherwise let `q` bubble to the app and
    abandon the create.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        Binding("q", "noop", show=False),
    ]

    DEFAULT_CSS = """
    NewSpecModal {
        align: center middle;
    }
    NewSpecModal > Vertical {
        width: 80%;
        max-width: 70;
        height: auto;
        padding: 1 2;
        border: round $accent;
        background: $surface;
    }
    NewSpecModal Static {
        height: auto;
    }
    NewSpecModal Input {
        margin: 1 0 0 0;
    }
    NewSpecModal #spec-preview,
    NewSpecModal #spec-status {
        margin-top: 1;
    }
    NewSpecModal #spec-buttons {
        height: auto;
        align-horizontal: right;
    }
    NewSpecModal #spec-buttons Button {
        margin: 1 0 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("New spec", classes="section-title")
            yield Static(
                "Name the model type. It becomes the filename and the spec's "
                "`model_type`.",
                classes="config-detail",
            )
            yield Input(placeholder="vehicle", id="spec-name")
            yield Static("", id="spec-preview", classes="config-detail")
            yield Static("", id="spec-status", classes="config-detail")
            with Horizontal(id="spec-buttons"):
                yield Button("Cancel", id="cancel-spec")
                yield Button("Create", id="create-spec", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#spec-name", Input).focus()

    # -- bindings ----------------------------------------------------------

    def action_cancel(self) -> None:
        """Escape → cancel. Nothing has been written, so there is nothing to
        undo; the screen just returns `None`."""
        self.dismiss(None)

    def action_noop(self) -> None:
        """Absorb `q` so the app's global quit can't fire mid-create."""

    # -- the form ----------------------------------------------------------

    @on(Input.Changed, "#spec-name")
    def _on_changed(self) -> None:
        """Show the filename the typed name normalizes to, and drop a stale
        error — so the user sees the normalization *before* committing to it."""
        raw = self.query_one("#spec-name", Input).value
        name = naming.normalize(raw)
        preview = (
            f"→ {paths.SPECS_DIRNAME}/{escape(name)}{naming.SUFFIX}" if name else ""
        )
        self.query_one("#spec-preview", Static).update(preview)
        self._status("")

    @on(Input.Submitted, "#spec-name")
    def _on_submitted(self) -> None:
        """Enter in the Input **creates**.

        The opposite call from the wizard's models box, where Enter Adds and
        never advances: there the field feeds a list, here it *is* the whole
        form.
        """
        self._create()

    @on(Button.Pressed, "#create-spec")
    def _on_create_pressed(self) -> None:
        self._create()

    @on(Button.Pressed, "#cancel-spec")
    def _on_cancel_pressed(self) -> None:
        self.dismiss(None)

    def _create(self) -> None:
        raw = self.query_one("#spec-name", Input).value
        if error := naming.validate(raw):
            self._status(error)
            return
        model_type = naming.normalize(raw)
        specs_dir = cast("BlenderBuddyApp", self.app).specs_dir
        try:
            path = store.create(specs_dir, model_type)
        except FileExistsError:
            # Covers both the ordinary collision and the O_EXCL race — one
            # message, and the Input keeps its text so the user can just rename.
            self._status(f"A spec named '{escape(model_type)}' already exists.")
            return
        except OSError as error:
            self._status(
                f"Could not create spec: {escape(str(error.strerror or error))}"
            )
            return
        self.dismiss(path)

    def _status(self, text: str) -> None:
        self.query_one("#spec-status", Static).update(text)
