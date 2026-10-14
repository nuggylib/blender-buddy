"""Mesh roles form tests, pushed directly over a dashboard-booted app."""

import json

from textual.widgets import Button, Input, SelectionList, Static

from model_meta.app import ModelMetaApp
from model_meta.config import store as config_store
from model_meta.config.settings import Settings
from model_meta.godot import discovery
from model_meta.specs import store as specs_store
from model_meta.tui.screens.dashboard import DashboardScreen
from model_meta.tui.screens.mesh_roles_form import MeshRolesFormScreen
from model_meta.tui.widgets.field_list import FieldList

BONES = ["body", "susarm.front.top.L", "susarm.front.top.R", "arm[L]"]


async def _wait_for(pilot, predicate, tries=100):
    for _ in range(tries):
        if predicate():
            return True
        await pilot.pause()
    return False


def _app(tmp_path, monkeypatch):
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    (tmp_path / "models").mkdir()
    (tmp_path / "godot").mkdir()
    config_store.save(
        cfg,
        Settings(
            blender_executable="blender",
            blender_version="4.5.0",
            models_directories=(str(tmp_path / "models"),),
            godot_projects_root=str(tmp_path / "godot"),
        ),
    )
    return ModelMetaApp(config_path=cfg)


def _spec(tmp_path, bones=BONES):
    path = specs_store.create(tmp_path / "specs", "vehicle")
    specs_store.update_armature(path, add_bones=bones)
    return path


def _roles(path):
    return json.loads(path.read_text(encoding="utf-8"))["mesh_roles"]


async def _open(pilot, app, path):
    await pilot.pause()
    app.push_screen(MeshRolesFormScreen(path))
    assert await _wait_for(pilot, lambda: isinstance(app.screen, MeshRolesFormScreen))
    await pilot.pause()


async def _start_add(pilot):
    await pilot.press("a")
    await pilot.pause()


async def _type(pilot, text):
    if text:
        await pilot.press(*text)
    await pilot.press("enter")
    await pilot.pause()


def _focused_id(app):
    return app.screen.focused.id if app.screen.focused else None


def _status(app):
    return str(app.screen.query_one("#role-status", Static).render())


def _question_shown(app):
    return app.screen.query_one("#role-bones-question").display


def _bones(app):
    checklist = app.screen.query_one("#role-bones", SelectionList)
    return [
        checklist.get_option_at_index(i).value for i in range(checklist.option_count)
    ]


def _selected(app):
    return app.screen.query_one("#role-bones", SelectionList).selected


def _preview(app):
    return str(app.screen.query_one("#role-preview", Static).render())


async def _check(pilot, app, *bones):
    checklist = app.screen.query_one("#role-bones", SelectionList)
    for bone in bones:
        checklist.select(bone)
    await pilot.pause()


async def _confirm(pilot, app):
    if _focused_id(app) == "role-bones":
        await pilot.press("tab")
    assert _focused_id(app) == "confirm-role"
    while app.screen.focused.has_class("-active"):  # Button ignores repeat presses
        await pilot.pause(0.05)
    await pilot.press("enter")
    await pilot.pause()


def _lines(app):
    return [str(row.render()) for row in app.screen.query("#role-list .field-list-row")]


async def test_form_opens_read_only_on_the_role_list(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        assert _focused_id(app) == "role-list"
        assert app.screen.query_one("#role-list .field-list-empty")
        assert not app.screen.query_one("#role-editor").display

        await pilot.press("enter")  # nothing to edit on an empty list, so Enter adds
        await pilot.pause()
        assert app.screen.query_one("#role-editor").display
        assert not _question_shown(app)
        assert _focused_id(app) == "role-name"


async def test_lists_existing_roles_with_their_vtx_grp(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.add_mesh_role(path, "body", "body")
    document = json.loads(path.read_text(encoding="utf-8"))
    document["mesh_roles"]["glass"] = {}
    path.write_text(json.dumps(document), encoding="utf-8")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        assert _lines(app) == ["body", "vtx_grp: body", "glass"]
        children = app.screen.query("#role-list .field-list-child")
        assert [str(row.render()) for row in children] == ["vtx_grp: body"]


async def test_no_required_bones_opens_nothing(tmp_path, monkeypatch):
    path = _spec(tmp_path, bones=[])
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)
        assert not app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-list"
        assert _status(app) == "Add required bones first."


async def test_roles_are_added_one_after_another(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)

        await _type(pilot, "  susarm_upper  ")
        assert _question_shown(app)
        assert _focused_id(app) == "role-bones"
        label = app.screen.query_one("#role-bones-label", Static)
        assert str(label.render()) == "Bones for 'susarm_upper'"
        assert _bones(app) == BONES
        assert _preview(app) == ""

        await _check(pilot, app, "susarm.front.top.R", "susarm.front.top.L")
        assert _preview(app) == "vtx_grp: susarm.front.top.{1}"
        await _confirm(pilot, app)
        assert _roles(path) == {"susarm_upper": {"vtx_grp": "susarm.front.top.{1}"}}
        assert _status(app) == "Mesh role 'susarm_upper' added."
        assert not _question_shown(app)
        assert _focused_id(app) == "role-name"
        assert app.screen.query_one("#role-name", Input).value == ""

        await _type(pilot, "body")
        await pilot.press("space")
        await pilot.pause()
        assert _preview(app) == "vtx_grp: body"
        await _confirm(pilot, app)
        assert list(_roles(path)) == ["susarm_upper", "body"]
        assert _lines(app) == [
            "susarm_upper",
            "vtx_grp: susarm.front.top.{1}",
            "body",
            "vtx_grp: body",
        ]


async def test_bad_role_names_are_rejected(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.add_mesh_role(path, "body", "body")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)

        await _type(pilot, "   ")
        assert _status(app) == "Enter a role name."
        assert not _question_shown(app)

        await pilot.press("ctrl+u")
        await _type(pilot, "body")
        assert _status(app) == "'body' is already a mesh role."
        assert not _question_shown(app)
        assert app.screen.query_one("#role-name", Input).value == "body"


async def test_bad_selections_are_rejected_and_nothing_written(tmp_path, monkeypatch):
    path = _spec(tmp_path, bones=[*BONES, "susarm.rear.top.L"])
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)
        await _type(pilot, "wheel")

        cases = [
            ((), "Check at least one bone."),
            (
                ("body", "susarm.front.top.L"),
                "'body' and 'susarm.front.top.L' can't share one pattern.",
            ),
            (
                ("susarm.front.top.R", "susarm.rear.top.L"),
                "'susarm.{1}.top.{2}' would also match susarm.front.top.L.",
            ),
        ]
        for checked, message in cases:
            app.screen.query_one("#role-bones", SelectionList).deselect_all()
            await _check(pilot, app, *checked)
            if checked:
                assert _preview(app) == message
            await _confirm(pilot, app)
            assert _status(app) == message
            assert _selected(app) == list(checked)
            assert _question_shown(app)
        assert _roles(path) == {}


async def test_role_taken_in_between_is_reported(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)
        await _type(pilot, "body")
        specs_store.add_mesh_role(path, "body", "body")

        await _check(pilot, app, "body")
        await _confirm(pilot, app)
        assert (
            _status(app) == "Could not write the spec: 'body' is already a mesh role."
        )
        assert _roles(path) == {"body": {"vtx_grp": "body"}}
        assert _selected(app) == ["body"]


async def test_escape_semantics(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)
        await _type(pilot, "body")
        await _check(pilot, app, "body")

        await pilot.press("escape")
        assert not _question_shown(app)
        assert _focused_id(app) == "role-name"
        assert app.screen.query_one("#role-name", Input).value == "body"

        await _type(pilot, "")
        assert _selected(app) == []
        assert _preview(app) == ""
        await pilot.press("escape")
        assert _focused_id(app) == "role-name"

        await pilot.press("escape")
        assert app.screen.query_one("#role-name", Input).value == ""
        assert app.screen.query_one("#role-editor").display

        await pilot.press("escape")
        assert not app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-list"

        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))
        assert _roles(path) == {}


async def test_q_does_not_quit(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await pilot.press("q")
        await pilot.pause()
        assert app.is_running
        assert isinstance(app.screen, MeshRolesFormScreen)


async def test_markup_looking_text_renders_literally(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _start_add(pilot)
        await _type(pilot, "[b]arm")
        label = app.screen.query_one("#role-bones-label", Static)
        assert str(label.render()) == "Bones for '[b]arm'"

        await _check(pilot, app, "arm[L]")
        assert _preview(app) == "vtx_grp: arm[L]"
        await _confirm(pilot, app)
        assert _lines(app) == ["[b]arm", "vtx_grp: arm[L]"]
        assert _status(app) == "Mesh role '[b]arm' added."


async def test_clicking_the_list_opens_or_refocuses_the_editor(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await pilot.click("#role-list")
        await pilot.pause()
        assert app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-name"

        await _type(pilot, "body")
        await pilot.click("#role-list")
        await pilot.pause()
        assert _focused_id(app) == "role-bones"


# --- editing a role ---------------------------------------------------------


def _with_roles(tmp_path, bones=BONES):
    path = _spec(tmp_path, bones)
    specs_store.add_mesh_role(path, "body", "body")
    specs_store.add_mesh_role(path, "susarm", "susarm.front.top.{1}")
    document = json.loads(path.read_text(encoding="utf-8"))
    document["mesh_roles"]["glass"] = {"weight": 1.0}
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


async def _edit_role(pilot, app, index):
    role_list = app.screen.query_one("#role-list", FieldList)
    role_list.focus()
    role_list.highlighted = index
    await pilot.press("enter")
    await pilot.pause()


def _mode(app):
    return app.screen._mode


def _button(app):
    return str(app.screen.query_one("#confirm-role", Button).label)


def _cursor(app):
    return app.screen.query_one("#role-list", FieldList).highlighted


async def test_enter_on_a_role_opens_it_prefilled(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        assert _cursor(app) == 0
        await pilot.press("down", "enter")
        await pilot.pause()

        assert _mode(app) == "edit"
        assert app.screen.query_one("#role-name", Input).value == "susarm"
        assert _question_shown(app)
        label = app.screen.query_one("#role-bones-label", Static)
        assert str(label.render()) == "Bones for 'susarm'"
        assert _bones(app) == BONES
        assert _selected(app) == ["susarm.front.top.L", "susarm.front.top.R"]
        assert _preview(app) == "vtx_grp: susarm.front.top.{1}"
        assert _button(app) == "Save"
        assert _focused_id(app) == "role-bones"
        assert _status(app) == ""

        await pilot.press("escape")
        await _edit_role(pilot, app, 2)
        assert app.screen.query_one("#role-name", Input).value == "glass"
        assert _selected(app) == []
        assert _preview(app) == ""


async def test_a_stored_pattern_matching_no_bone_says_so(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.add_mesh_role(path, "door", "door.{1}")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 0)
        assert _selected(app) == []
        assert _status(app) == "Its vtx_grp 'door.{1}' matches no required bone."


async def test_save_writes_the_new_bones_and_closes(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 1)
        app.screen.query_one("#role-bones", SelectionList).deselect(
            "susarm.front.top.R"
        )
        await pilot.pause()
        assert _preview(app) == "vtx_grp: susarm.front.top.L"

        await _confirm(pilot, app)
        assert _roles(path)["susarm"] == {"vtx_grp": "susarm.front.top.L"}
        assert _status(app) == "Mesh role 'susarm' saved."
        assert _mode(app) is None
        assert not app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-list"
        assert _cursor(app) == 1
        assert _lines(app)[2:4] == ["susarm", "vtx_grp: susarm.front.top.L"]


async def test_an_unsubmitted_rename_is_saved_in_place(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 2)
        await _check(pilot, app, "body")
        await pilot.press("shift+tab", "ctrl+u", *"  windows ", "tab")
        await pilot.pause()

        await _confirm(pilot, app)
        assert list(_roles(path)) == ["body", "susarm", "windows"]
        assert _roles(path)["windows"] == {"weight": 1.0, "vtx_grp": "body"}
        assert _status(app) == "Mesh role 'windows' saved."
        assert _cursor(app) == 2


async def test_rename_follows_the_add_name_rules(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    before = path.read_bytes()
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 1)
        await pilot.press("shift+tab", "ctrl+u")
        await _type(pilot, "body")
        assert _status(app) == "'body' is already a mesh role."
        assert _focused_id(app) == "role-name"
        assert _selected(app) == ["susarm.front.top.L", "susarm.front.top.R"]

        await pilot.press("tab")
        await _confirm(pilot, app)
        assert _status(app) == "'body' is already a mesh role."
        assert _mode(app) == "edit"

        await pilot.press("shift+tab", "shift+tab", "ctrl+u")
        await _type(pilot, "   ")
        assert _status(app) == "Enter a role name."
        assert path.read_bytes() == before

        await _type(pilot, "susarm")
        assert _status(app) == ""
        assert _focused_id(app) == "role-bones"


async def test_rejected_selections_keep_the_editor_open(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    before = path.read_bytes()
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 1)
        await _check(pilot, app, "body")
        await _confirm(pilot, app)
        message = "'body' and 'susarm.front.top.L' can't share one pattern."
        assert _status(app) == message
        assert _mode(app) == "edit"
        assert path.read_bytes() == before


async def test_one_editor_at_a_time(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    before = path.read_bytes()
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 1)
        app.screen.query_one("#role-bones", SelectionList).deselect_all()
        await pilot.pause()

        await _edit_role(pilot, app, 1)  # the open role: nothing resets
        assert _selected(app) == []
        assert _focused_id(app) == "role-bones"

        app.screen.query_one("#role-list").focus()
        await _start_add(pilot)
        assert _mode(app) == "add"
        assert _button(app) == "Add"
        assert app.screen.query_one("#role-name", Input).value == ""
        assert not _question_shown(app)
        assert _focused_id(app) == "role-name"

        await _type(pilot, "wheel")
        assert _question_shown(app)
        await _edit_role(pilot, app, 0)
        assert _mode(app) == "edit"
        assert app.screen.query_one("#role-name", Input).value == "body"
        assert _selected(app) == ["body"]
        assert path.read_bytes() == before


async def test_a_is_ignored_inside_an_open_editor(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        assert app.screen.check_action("add", ())
        await _edit_role(pilot, app, 1)
        assert _focused_id(app) == "role-bones"
        assert not app.screen.check_action("add", ())
        await pilot.press("a")
        await pilot.pause()
        assert _mode(app) == "edit"
        assert app.screen.query_one("#role-name", Input).value == "susarm"


async def test_escape_closes_an_edit_unsaved(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    before = path.read_bytes()
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 1)
        app.screen.query_one("#role-bones", SelectionList).deselect_all()
        await pilot.pause()

        await pilot.press("escape")
        assert _mode(app) is None
        assert not app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-list"
        assert _cursor(app) == 1
        assert path.read_bytes() == before

        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))


async def test_clicking_a_role_edits_it(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        child = app.screen.query("#role-list .field-list-child").last()
        await pilot.click(child)
        await pilot.pause()
        assert _mode(app) == "edit"
        assert app.screen.query_one("#role-name", Input).value == "susarm"


async def test_editing_needs_required_bones(tmp_path, monkeypatch):
    path = _spec(tmp_path, bones=[])
    document = json.loads(path.read_text(encoding="utf-8"))
    document["mesh_roles"]["glass"] = {}
    path.write_text(json.dumps(document), encoding="utf-8")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 0)
        assert _mode(app) is None
        assert _focused_id(app) == "role-list"
        assert _status(app) == "Add required bones first."


async def test_a_role_removed_by_hand_is_reported(tmp_path, monkeypatch):
    path = _with_roles(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _edit_role(pilot, app, 0)

        document = json.loads(path.read_text(encoding="utf-8"))
        del document["mesh_roles"]["body"]
        path.write_text(json.dumps(document), encoding="utf-8")
        await _confirm(pilot, app)
        assert (
            _status(app) == "Could not write the spec: 'body' is no longer a mesh role."
        )
        assert _mode(app) == "edit"

        await pilot.press("escape")
        await _edit_role(pilot, app, 0)  # the list is stale until it refreshes
        assert _status(app) == "'body' is no longer a mesh role."
        assert _mode(app) is None
        assert _lines(app)[0] == "susarm"
