"""Mesh roles form tests, pushed directly over a dashboard-booted app."""

import json

from textual.widgets import Input, Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.config import store as config_store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.specs import store as specs_store
from blender_buddy.tui.screens.dashboard import DashboardScreen
from blender_buddy.tui.screens.mesh_roles_form import MeshRolesFormScreen

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
    return BlenderBuddyApp(config_path=cfg)


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


async def _edit(pilot):
    await pilot.press("enter")
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
    return app.screen.query_one("#role-vtx-grp-question").display


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

        await _edit(pilot)
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
        await _edit(pilot)
        assert not app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-list"
        assert _status(app) == "Add required bones first."


async def test_roles_are_added_one_after_another(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit(pilot)

        await _type(pilot, "  susarm_upper  ")
        assert _question_shown(app)
        assert _focused_id(app) == "role-vtx-grp"
        label = app.screen.query_one("#role-vtx-grp-label", Static)
        assert str(label.render()) == "vtx_grp for 'susarm_upper'"

        await _type(pilot, "susarm.{1}.top.{2}")
        assert _roles(path) == {"susarm_upper": {"vtx_grp": "susarm.{1}.top.{2}"}}
        assert _status(app) == "Mesh role 'susarm_upper' added."
        assert not _question_shown(app)
        assert _focused_id(app) == "role-name"
        assert app.screen.query_one("#role-name", Input).value == ""
        assert app.screen.query_one("#role-vtx-grp", Input).value == ""

        await _type(pilot, "body")
        await _type(pilot, "body")
        assert list(_roles(path)) == ["susarm_upper", "body"]
        assert _lines(app) == [
            "susarm_upper",
            "vtx_grp: susarm.{1}.top.{2}",
            "body",
            "vtx_grp: body",
        ]


async def test_bad_role_names_are_rejected(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.add_mesh_role(path, "body", "body")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit(pilot)

        await _type(pilot, "   ")
        assert _status(app) == "Enter a role name."
        assert not _question_shown(app)

        await pilot.press("ctrl+u")
        await _type(pilot, "body")
        assert _status(app) == "'body' is already a mesh role."
        assert not _question_shown(app)
        assert app.screen.query_one("#role-name", Input).value == "body"


async def test_bad_vtx_grp_is_rejected_and_nothing_written(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit(pilot)
        await _type(pilot, "wheel")

        cases = [
            ("", "Enter a vertex group pattern."),
            ("a" * 64, "Vertex group names are limited to 63 bytes."),
            ("susarm..L", "'susarm..L' has an empty segment."),
            ("wheel.{1}", "'wheel.{1}' matches no required bone."),
        ]
        for text, message in cases:
            app.screen.query_one("#role-vtx-grp", Input).value = ""
            await _type(pilot, text)
            assert _status(app) == message
            assert app.screen.query_one("#role-vtx-grp", Input).value == text
            assert _focused_id(app) == "role-vtx-grp"
        assert _roles(path) == {}


async def test_role_taken_in_between_is_reported(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit(pilot)
        await _type(pilot, "body")
        specs_store.add_mesh_role(path, "body", "body")

        await _type(pilot, "susarm.{1}.top.{2}")
        assert (
            _status(app) == "Could not write the spec: 'body' is already a mesh role."
        )
        assert _roles(path) == {"body": {"vtx_grp": "body"}}
        assert app.screen.query_one("#role-vtx-grp", Input).value == (
            "susarm.{1}.top.{2}"
        )


async def test_escape_semantics(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit(pilot)
        await _type(pilot, "body")
        await pilot.press(*"bo")

        await pilot.press("escape")
        assert not _question_shown(app)
        assert app.screen.query_one("#role-vtx-grp", Input).value == ""
        assert _focused_id(app) == "role-name"
        assert app.screen.query_one("#role-name", Input).value == "body"

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
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _edit(pilot)
        await _type(pilot, "[b]arm")
        label = app.screen.query_one("#role-vtx-grp-label", Static)
        assert str(label.render()) == "vtx_grp for '[b]arm'"

        await _type(pilot, "arm[L]")
        assert _lines(app) == ["[b]arm", "vtx_grp: arm[L]"]
        assert _status(app) == "Mesh role '[b]arm' added."


async def test_clicking_the_list_opens_the_editor(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await pilot.click("#role-list")
        await pilot.pause()
        assert app.screen.query_one("#role-editor").display
        assert _focused_id(app) == "role-name"
