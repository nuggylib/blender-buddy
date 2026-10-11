"""Armature form tests, pushed directly over a dashboard-booted app."""

import json

from textual.widgets import Input, SelectionList, Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.config import store as config_store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.specs import store as specs_store
from blender_buddy.tui.screens.armature_form import ArmatureFormScreen
from blender_buddy.tui.screens.dashboard import DashboardScreen

FRONT_REAR = {".front": ".rear", ".rear": ".front"}


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


def _spec(tmp_path):
    return specs_store.create(tmp_path / "specs", "vehicle")


def _armature(path):
    return json.loads(path.read_text(encoding="utf-8"))["armature"]


async def _open(pilot, app, path):
    await pilot.pause()
    app.push_screen(ArmatureFormScreen(path))
    assert await _wait_for(pilot, lambda: isinstance(app.screen, ArmatureFormScreen))
    await pilot.pause()


async def _type(pilot, text):
    if text:
        await pilot.press(*text)
    await pilot.press("enter")
    await pilot.pause()


def _focused_id(app):
    return app.screen.focused.id if app.screen.focused else None


def _status(app):
    return str(app.screen.query_one("#bone-status", Static).render())


def _listed(app):
    return [str(row.render()) for row in app.screen.query(".bone-row")]


def _variants(app):
    (checklist,) = app.screen.query("#bone-variants")
    return [
        checklist.get_option_at_index(i).value for i in range(checklist.option_count)
    ]


def _inverse_label(app):
    return str(app.screen.query_one("#bone-inverse-label", Static).render())


async def test_form_opens_focused_on_the_name_field(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        assert _focused_id(app) == "bone-name"
        assert app.screen.query_one("#bone-list-empty")


async def test_plain_name_is_written_listed_and_cleared(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "body")

        assert _armature(path)["required_bones"] == ["body"]
        assert _listed(app) == ["body"]
        assert app.screen.query_one("#bone-name", Input).value == ""
        assert _focused_id(app) == "bone-name"


async def test_wheel_front_left_end_to_end(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "wheel.front.L")

        assert "Inverse of `.front`" in _inverse_label(app)
        assert "leave blank" in _inverse_label(app)
        assert _focused_id(app) == "bone-inverse"

        await _type(pilot, ".rear")
        assert _armature(path)["bone_name_inverses"] == FRONT_REAR
        assert _variants(app) == ["wheel.front.R", "wheel.rear.L", "wheel.rear.R"]
        assert _focused_id(app) == "add-bones"

        await pilot.press("enter")
        await pilot.pause()
        assert _armature(path)["required_bones"] == [
            "wheel.front.L",
            "wheel.front.R",
            "wheel.rear.L",
            "wheel.rear.R",
        ]
        assert not app.screen.query("#bone-variants")
        assert _focused_id(app) == "bone-name"


async def test_full_chain_first_with_two_unmapped_segments(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        before = path.read_bytes()

        await _type(pilot, "susarm.front.top.L")
        assert "`.front`" in _inverse_label(app)
        await _type(pilot, "rear")  # leading dot added

        assert path.read_bytes() == before
        assert not app.screen.query("#bone-variants")
        assert "`.top`" in _inverse_label(app)

        await _type(pilot, ".bottom")
        assert _armature(path)["bone_name_inverses"] == {
            **FRONT_REAR,
            ".top": ".bottom",
            ".bottom": ".top",
        }
        assert len(_variants(app)) == 7

        await pilot.press("enter")
        await pilot.pause()
        assert len(_armature(path)["required_bones"]) == 8


async def test_several_bones_in_one_visit_and_builtin_only_skips_questions(
    tmp_path, monkeypatch
):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "body")
        await _type(pilot, "arm.L")

        assert not app.screen.query("#bone-inverse")
        assert _variants(app) == ["arm.R"]
        await pilot.press("enter")
        await pilot.pause()

        await _type(pilot, "head")
        assert _armature(path)["required_bones"] == ["body", "arm.L", "arm.R", "head"]
        assert _listed(app) == ["body", "arm.L", "arm.R", "head"]


async def test_unchecking_a_variant_leaves_it_out(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "wheel.front.L")
        await _type(pilot, ".rear")

        checklist = app.screen.query_one("#bone-variants", SelectionList)
        checklist.deselect("wheel.rear.L")
        await pilot.pause()
        await pilot.press("enter")  # focus is still on Add
        await pilot.pause()

        assert _armature(path)["required_bones"] == [
            "wheel.front.L",
            "wheel.front.R",
            "wheel.rear.R",
        ]


async def test_blank_inverse_is_saved_as_a_self_mapping(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "finger.tip")
        await _type(pilot, "")

        # Nothing to choose: written directly, no checklist.
        assert _armature(path)["bone_name_inverses"] == {".tip": ".tip"}
        assert _armature(path)["required_bones"] == ["finger.tip"]
        assert not app.screen.query("#bone-variants")

        await _type(pilot, "toe.tip")
        assert not app.screen.query("#bone-inverse")
        assert _armature(path)["required_bones"] == ["finger.tip", "toe.tip"]


async def test_checklist_skipped_when_every_variant_is_required(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.update_armature(path, add_bones=["arm.R"])
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "arm.L")

        assert not app.screen.query("#bone-variants")
        assert _armature(path)["required_bones"] == ["arm.R", "arm.L"]


async def test_back_from_checklist_rewrites_the_mapping(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "wheel.front.L")
        await _type(pilot, ".rear")
        assert _armature(path)["bone_name_inverses"] == FRONT_REAR

        await pilot.press("escape")
        await pilot.pause()
        assert not app.screen.query("#bone-variants")
        inverse = app.screen.query_one("#bone-inverse", Input)
        assert inverse.value == ".rear"  # pre-filled with the earlier answer

        inverse.value = ""
        await _type(pilot, ".back")
        assert _armature(path)["bone_name_inverses"] == {
            ".front": ".back",
            ".back": ".front",
        }
        assert _variants(app) == ["wheel.front.R", "wheel.back.L", "wheel.back.R"]


async def test_escape_semantics(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "wheel.front.L")

        await pilot.press("escape")  # inverse question → name field
        await pilot.pause()
        assert not app.screen.query("#bone-inverse")
        name = app.screen.query_one("#bone-name", Input)
        assert name.value == "wheel.front.L"
        assert _focused_id(app) == "bone-name"

        await pilot.press("escape")  # idle with text → cleared
        await pilot.pause()
        assert name.value == ""
        assert isinstance(app.screen, ArmatureFormScreen)

        await pilot.press("escape")  # idle and empty → leaves
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))
        assert _armature(path)["required_bones"] == []


async def test_failures_keep_text_and_write_nothing(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.update_armature(
        path, add_bones=["body"], set_inverses={".top": ".bottom", ".bottom": ".top"}
    )
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        before = path.read_bytes()

        await _type(pilot, "body")
        assert "already required" in _status(app)
        assert app.screen.query_one("#bone-name", Input).value == "body"

        app.screen.query_one("#bone-name", Input).value = ""
        await _type(pilot, "a..b")
        assert "empty segment" in _status(app)

        app.screen.query_one("#bone-name", Input).value = ""
        await _type(pilot, "wheel.front.L")
        await _type(pilot, ".bottom")
        assert "already paired with '.top'" in _status(app)
        assert app.screen.query_one("#bone-inverse", Input).value == ".bottom"

        assert path.read_bytes() == before


async def test_unwritable_spec_reports_and_keeps_the_name(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)

    def refuse(*args, **kwargs):
        raise PermissionError(13, "Permission denied")

    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        monkeypatch.setattr(specs_store, "update_armature", refuse)
        await _type(pilot, "body")

        assert "Permission denied" in _status(app)
        assert app.screen.query_one("#bone-name", Input).value == "body"
        assert _armature(path)["required_bones"] == []


async def test_q_does_not_quit_from_the_add_button(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "arm.L")
        assert _focused_id(app) == "add-bones"

        await pilot.press("q")
        await pilot.pause()
        assert app.is_running
