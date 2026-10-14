"""FieldList tests: the read-only, selectable list of one spec field."""

from textual.app import App

from model_meta.tui.widgets.field_list import FieldList


class _Host(App):
    def __init__(self, cursor=False):
        super().__init__()
        self.cursor = cursor
        self.selected = []

    def compose(self):
        yield FieldList("Bones", "Nothing yet.", cursor=self.cursor, id="list")

    def on_field_list_selected(self, event):
        self.selected.append((event.control.id, event.index))


ROLES = (("body", 0), ("vtx_grp: body", 1), ("glass", 0), ("wheel", 0), ("w", 1))


def _highlighted_rows(app):
    return [str(row.render()) for row in app.query(".field-list-highlighted")]


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
        assert app.selected == [("list", None), ("list", None)]


async def test_without_a_cursor_arrows_do_not_highlight():
    app = _Host()
    async with app.run_test() as pilot:
        field_list = app.query_one(FieldList)
        field_list.lines = ROLES
        await pilot.pause()
        await pilot.press("down", "enter")
        await pilot.pause()
        assert field_list.highlighted is None
        assert not app.query(".field-list-highlighted")
        assert app.selected == [("list", None)]


async def test_cursor_steps_over_items_and_clamps():
    app = _Host(cursor=True)
    async with app.run_test() as pilot:
        field_list = app.query_one(FieldList)
        assert field_list.highlighted is None
        await pilot.press("enter")
        await pilot.pause()
        assert app.selected == [("list", None)]

        field_list.lines = ROLES
        await pilot.pause()
        assert field_list.highlighted == 0
        assert _highlighted_rows(app) == ["body"]

        await pilot.press("up")
        assert field_list.highlighted == 0
        await pilot.press("down", "down", "down")
        await pilot.pause()
        assert field_list.highlighted == 2
        assert _highlighted_rows(app) == ["wheel"]
        await pilot.press("up", "enter")
        await pilot.pause()
        assert app.selected[-1] == ("list", 1)

        field_list.lines = ROLES[:2]
        await pilot.pause()
        assert field_list.highlighted == 0
        assert _highlighted_rows(app) == ["body"]

        field_list.lines = ()
        await pilot.pause()
        assert field_list.highlighted is None


async def test_cursor_click_selects_the_rows_item():
    app = _Host(cursor=True)
    async with app.run_test() as pilot:
        app.query_one(FieldList).lines = ROLES
        await pilot.pause()
        child = app.query(".field-list-child").last()
        await pilot.click(child)
        await pilot.pause()
        assert app.selected == [("list", 2)]
        assert _highlighted_rows(app) == ["wheel"]


async def test_cursor_keeps_the_highlight_in_view():
    app = _Host(cursor=True)
    async with app.run_test(size=(40, 10)) as pilot:
        field_list = app.query_one(FieldList)
        field_list.lines = tuple((f"bone{i}", 0) for i in range(40))
        await pilot.pause()
        for _ in range(30):
            await pilot.press("down")
        await pilot.pause()
        row = app.query_one(".field-list-highlighted")
        assert field_list.scroll_y > 0
        assert row.region.overlaps(field_list.content_region)
