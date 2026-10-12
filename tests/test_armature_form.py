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


async def test_form_lists_every_bone_already_in_the_spec(tmp_path, monkeypatch):
    """The full list lives here — the detail page only shows a count."""
    path = _spec(tmp_path)
    bones = [f"bone{i}" for i in range(40)]
    specs_store.update_armature(path, add_bones=bones)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(80, 24)) as pilot:
        await _open(pilot, app, path)
        assert await _wait_for(pilot, lambda: _listed(app) == bones)


def _armature_name(app):
    return app.screen.query_one("#armature-name", Input)


async def test_armature_name_is_prefilled_and_one_shift_tab_away(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.update_armature(path, object_name="Rig")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        assert _armature_name(app).value == "Rig"
        assert _focused_id(app) == "bone-name"
        await pilot.press("shift+tab")
        assert _focused_id(app) == "armature-name"


async def test_armature_name_is_saved_on_enter(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.update_armature(path, add_bones=["body"])
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await pilot.press("shift+tab")
        await _type(pilot, "  Rig[L] ")

        assert _armature(path)["object_name"] == "Rig[L]"
        assert _armature(path)["required_bones"] == ["body"]
        assert _armature_name(app).value == "Rig[L]"
        assert _status(app) == "Armature name saved."
        assert _focused_id(app) == "bone-name"


async def test_blank_armature_name_clears_it(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.update_armature(path, object_name="Rig")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await pilot.press("shift+tab")
        _armature_name(app).value = ""
        await _type(pilot, "")

        assert _armature(path)["object_name"] == ""
        assert _status(app) == "Armature name cleared."


async def test_over_long_armature_name_is_rejected(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    before = path.read_bytes()
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await pilot.press("shift+tab")
        _armature_name(app).value = "a" * 64
        await _type(pilot, "")

        assert path.read_bytes() == before
        assert _armature_name(app).value == "a" * 64
        assert "63 bytes" in _status(app)
        assert _focused_id(app) == "armature-name"


async def test_escape_reverts_an_unsaved_armature_name_then_leaves(
    tmp_path, monkeypatch
):
    path = _spec(tmp_path)
    specs_store.update_armature(path, object_name="Rig")
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open(pilot, app, path)
        await pilot.press("shift+tab", "end", "2")
        assert _armature_name(app).value == "Rig2"

        await pilot.press("escape")
        assert _armature_name(app).value == "Rig"
        assert isinstance(app.screen, ArmatureFormScreen)
        assert _armature(path)["object_name"] == "Rig"

        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))


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


# --- parenting -------------------------------------------------------------

CORNERS = ["front.L", "front.R", "rear.L", "rear.R"]
RIG = [
    "root",
    *(f"axle.{c}" for c in CORNERS),
    *(f"wheel.{c}" for c in CORNERS),
    *(f"shockmount.body.{c}" for c in CORNERS),
    *(f"shockmount.wheel.{c}" for c in CORNERS),
]
RIG_INVERSES = {**FRONT_REAR, ".body": ".wheel", ".wheel": ".body"}


def _rig(tmp_path, parenting=None):
    path = _spec(tmp_path)
    specs_store.update_armature(
        path, add_bones=RIG, set_inverses=RIG_INVERSES, add_parenting=parenting
    )
    return path


async def _choose(pilot, app, parents):
    await pilot.press("tab")
    assert _focused_id(app) == "parent-bones"
    checklist = app.screen.query_one("#parent-bones", SelectionList)
    for parent in parents:
        checklist.select(parent)
    await pilot.press("tab")
    assert _focused_id(app) == "choose-children"
    await pilot.press("enter")
    await pilot.pause()


def _corners(base):
    return [f"{base}.{c}" for c in CORNERS]


def _children(app):
    (checklist,) = app.screen.query("#child-bones")
    return [
        checklist.get_option_at_index(i).value for i in range(checklist.option_count)
    ]


def _parenting_rows(app):
    return [
        ("  " if row.has_class("parenting-child") else "") + str(row.render())
        for row in app.screen.query(".parenting-row")
    ]


async def test_parenting_section_empty_states(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        assert not app.screen.query_one("#parent-picker").display
        assert app.screen.query_one("#parent-bones-empty").display
        assert app.screen.query_one("#parenting-list-empty")


async def test_checked_parents_end_to_end(tmp_path, monkeypatch):
    path = _rig(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 50)) as pilot:
        await _open(pilot, app, path)
        await _choose(pilot, app, _corners("axle"))
        assert _focused_id(app) == "child-bones"
        assert not app.screen.query_one("#parent-picker").display

        checklist = app.screen.query_one("#child-bones", SelectionList)
        for child in [*_corners("wheel"), *_corners("shockmount.wheel")]:
            checklist.select(child)
        await pilot.pause()
        preview = str(app.screen.query_one("#parenting-preview", Static).render())
        assert preview.startswith(
            "axle.{1}.{2}\n  wheel.{1}.{2}\n  shockmount.wheel.{1}.{2}\n"
        )
        assert "8 pairs" in preview

        app.screen.query_one("#add-children").press()
        assert await _wait_for(pilot, lambda: _status(app) == "Parenting saved.")
        assert _armature(path)["parenting"] == {
            "axle.{1}.{2}": ["wheel.{1}.{2}", "shockmount.wheel.{1}.{2}"]
        }
        assert _focused_id(app) == "parent-bones"
        assert app.screen.query_one("#parent-bones", SelectionList).selected == []
        assert not app.screen.query("#child-bones")
        assert _parenting_rows(app) == [
            "axle.{1}.{2}",
            "  wheel.{1}.{2}",
            "  shockmount.wheel.{1}.{2}",
        ]


async def test_children_exclude_parents_parented_bones_and_ancestors(
    tmp_path, monkeypatch
):
    path = _rig(tmp_path, {"root": ["axle.{1}.{2}"]})
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 50)) as pilot:
        await _open(pilot, app, path)
        await _choose(pilot, app, ["axle.front.L", "wheel.front.L"])
        children = _children(app)
        assert "root" not in children
        assert "wheel.front.L" not in children
        assert not any(name.startswith("axle.") for name in children)
        assert "wheel.front.R" in children


async def test_choose_with_no_parents_checked_shows_a_status(tmp_path, monkeypatch):
    path = _rig(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 50)) as pilot:
        await _open(pilot, app, path)
        await _choose(pilot, app, [])
        assert _status(app) == "Check at least one parent."
        assert not app.screen.query("#child-bones")


async def test_add_with_nothing_checked_writes_nothing(tmp_path, monkeypatch):
    path = _rig(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 50)) as pilot:
        await _open(pilot, app, path)
        before = path.read_bytes()
        await _choose(pilot, app, ["root"])
        app.screen.query_one("#add-children").press()
        await pilot.pause()
        assert _status(app) == "Check at least one child."
        assert path.read_bytes() == before


async def test_unpairable_child_is_reported_and_not_written(tmp_path, monkeypatch):
    path = _rig(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 50)) as pilot:
        await _open(pilot, app, path)
        before = path.read_bytes()
        await _choose(pilot, app, _corners("wheel"))
        app.screen.query_one("#child-bones", SelectionList).select("root")
        await pilot.pause()
        preview = str(app.screen.query_one("#parenting-preview", Static).render())
        assert "'root' matches no checked parent." in preview

        app.screen.query_one("#add-children").press()
        await pilot.pause()
        assert _status(app) == "'root' matches no checked parent."
        assert path.read_bytes() == before


async def test_no_eligible_children_shows_a_status(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    specs_store.update_armature(
        path, add_bones=["root", "body"], add_parenting={"root": ["body"]}
    )
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _choose(pilot, app, ["root"])
        assert _status(app) == "Every other bone already has a parent."
        assert not app.screen.query("#child-bones")


async def test_parenting_escape_steps_back_then_clears_then_leaves(
    tmp_path, monkeypatch
):
    path = _rig(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 50)) as pilot:
        await _open(pilot, app, path)
        before = path.read_bytes()
        await _choose(pilot, app, ["root"])
        app.screen.query_one("#child-bones", SelectionList).select("axle.front.L")
        await pilot.pause()

        await pilot.press("escape")
        await pilot.pause()
        parents = app.screen.query_one("#parent-bones", SelectionList)
        assert not app.screen.query("#child-bones")
        assert app.screen.query_one("#parent-picker").display
        assert _focused_id(app) == "parent-bones"
        assert parents.selected == ["root"]

        await pilot.press("escape")
        await pilot.pause()
        assert parents.selected == []
        assert isinstance(app.screen, ArmatureFormScreen)
        assert path.read_bytes() == before

        await pilot.press("escape")
        assert await _wait_for(
            pilot, lambda: not isinstance(app.screen, ArmatureFormScreen)
        )


async def test_new_bone_refreshes_the_parent_list(tmp_path, monkeypatch):
    path = _spec(tmp_path)
    app = _app(tmp_path, monkeypatch)
    async with app.run_test(size=(100, 40)) as pilot:
        await _open(pilot, app, path)
        await _type(pilot, "body")
        assert app.screen._parents == ["body"]
        assert app.screen.query_one("#parent-picker").display
