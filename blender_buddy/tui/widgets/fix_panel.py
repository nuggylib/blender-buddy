"""A block of "here's what to do about it" advice, kept out of a scrolling page."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static


class FixPanel(Vertical):
    """Advice that stays on screen, hidden until there is something to advise about.

    Assign `steps` (rendered strings, markup allowed); an empty tuple hides the
    panel. Children come from `compose` via a `recompose` reactive rather than
    `mount_all`, so the auto height is resolved in a normal layout pass.
    """

    steps: reactive[tuple[str, ...]] = reactive((), recompose=True)

    def __init__(self, heading: str = "How to fix issues", **kwargs) -> None:
        super().__init__(**kwargs)
        self._heading = heading
        self.display = False

    def compose(self) -> ComposeResult:
        if not self.steps:
            return
        yield Static(self._heading, id="fix-heading", classes="section-title")
        for step in self.steps:
            yield Static(f"• {step}", classes="config-detail fix-step")

    def watch_steps(self, steps: tuple[str, ...]) -> None:
        self.display = bool(steps)
