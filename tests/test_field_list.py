"""FieldList tests: the read-only, selectable list of one spec field."""

from textual.app import App

from blender_buddy.tui.widgets.field_list import FieldList


class _Host(App):
    def __init__(self):
        super().__init__()
        self.selected = []

    def compose(self):
        yield FieldList("Bones", "Nothing yet.", id="list")

    def on_field_list_selected(self, event):
        self.selected.append(event.control.id)


def _rows(app):
    return [
        (str(row.render()), row.has_class("field-list-child"))
        for row in app.query(".field-list-row")
    ]


async def test_empty_text_shows_until_lines_are_set():
    app = _Host()
    async with app.run_test() as pilot:
        field_list = app.query_one(FieldList)
        assert field_list.border_title == "Bones"
        assert str(app.query_one(".field-list-empty").render()) == "Nothing yet."

        field_list.lines = (("root", 0), ("wheel.[L]", 1))
        await pilot.pause()
        assert not app.query(".field-list-empty")
        assert _rows(app) == [("root", False), ("wheel.[L]", True)]


async def test_enter_and_click_both_select():
    app = _Host()
    async with app.run_test() as pilot:
        app.query_one(FieldList).lines = (("root", 0),)
        await pilot.pause()
        assert app.focused is app.query_one(FieldList)
        await pilot.press("enter")
        await pilot.click(".field-list-row")
        await pilot.pause()
        assert app.selected == ["list", "list"]
