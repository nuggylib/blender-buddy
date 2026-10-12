"""Edit-data modal tests: the root-field picker opened by `e` on a spec."""

from textual.app import App
from textual.widgets import OptionList

from blender_buddy.specs import schema
from blender_buddy.tui.screens.edit_data_modal import FIELDS, EditDataModal


class _Host(App):
    def __init__(self):
        super().__init__()
        self.result = "unset"

    def on_mount(self):
        self.push_screen(EditDataModal(), self._done)

    def _done(self, result):
        self.result = result


def test_field_keys_are_skeleton_root_keys():
    assert {key for key, _ in FIELDS} <= set(schema.skeleton("x"))


async def test_armature_is_the_only_option_and_enter_picks_it():
    app = _Host()
    async with app.run_test() as pilot:
        await pilot.pause()
        options = app.screen.query_one("#data-fields", OptionList)
        assert options.option_count == 1
        assert str(options.get_option_at_index(0).prompt) == "Armature"
        assert app.screen.focused is options

        await pilot.press("enter")
        await pilot.pause()
        assert app.result == "armature"


async def test_escape_returns_none():
    app = _Host()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert app.result is None


async def test_q_does_not_quit():
    app = _Host()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        assert app.is_running
        assert isinstance(app.screen, EditDataModal)
