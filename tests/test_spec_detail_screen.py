"""Spec detail screen tests.

Driven through the pilot from the Specs page, because `enter` on a row is the
only way in — the screen is pushed as an instance and is not in `SCREENS`.

The screen never reads the spec file, so the malformed and mismatched cases are
here to assert exactly that: they open the stub like any other spec.
"""

import json

from textual.widgets import Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.config import store as config_store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.specs import schema
from blender_buddy.specs import store as specs_store
from blender_buddy.tui.screens.spec_detail import SpecDetailScreen
from blender_buddy.tui.screens.specs import SpecsScreen
from blender_buddy.tui.widgets.spec_row import SpecRow


def _text(widget):
    """The plain rendered text of a Static, markup applied/stripped."""
    return str(widget.render())


async def _wait_for(pilot, predicate, tries=100):
    for _ in range(tries):
        if predicate():
            return True
        await pilot.pause()
    return False


def _app(tmp_path, monkeypatch, specs=(), raw=()):
    """A dashboard-booting app over a valid config, with `specs` on disk.

    `raw` names spec files hand-written as text — the malformed and mismatched
    cases the screen must be indifferent to.
    """
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    models = tmp_path / "models"
    models.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()
    config_store.save(
        cfg,
        Settings(
            blender_executable="blender",
            blender_version="4.5.0",
            models_directories=(str(models),),
            godot_projects_root=str(godot),
        ),
    )
    for name in specs:
        specs_store.create(tmp_path / "specs", name)
    for name, payload in raw:
        directory = tmp_path / "specs"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.json").write_text(payload, encoding="utf-8")
    return BlenderBuddyApp(config_path=cfg)


async def _open_specs(pilot, app):
    """Navigate the dashboard to the Specs screen."""
    await pilot.pause()
    await pilot.press("down")  # Blender → Specs
    await pilot.press("enter")
    assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecsScreen))


async def _open_spec(pilot, app):
    """Navigate to the Specs screen and `enter` on its first row."""
    await _open_specs(pilot, app)
    assert await _wait_for(pilot, lambda: isinstance(app.screen.focused, SpecRow))
    await pilot.press("enter")
    assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecDetailScreen))


def _title(app):
    return _text(app.screen.query_one("#spec-title", Static))


async def test_spec_detail_opens_for_the_selected_row(tmp_path, monkeypatch):
    """The screen is named for the row that opened it, not for row one."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle", "character"))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen
        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 2)
        assert await _wait_for(pilot, lambda: isinstance(screen.focused, SpecRow))

        await pilot.press("down")  # character → vehicle
        assert screen.focused.model_type == "vehicle"
        await pilot.press("enter")

        assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecDetailScreen))
        assert app.screen.model_type == "vehicle"
        assert "vehicle" in _title(app)


async def test_spec_detail_shows_the_name_and_the_placeholder_note(
    tmp_path, monkeypatch
):
    """The name and a note that contents are coming — and no filename, because
    the stem is the identity and the file is never opened."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test(size=(80, 24)) as pilot:
        await _open_spec(pilot, app)

        assert "vehicle" in _title(app)
        note = _text(app.screen.query_one("#placeholder-note", Static))
        assert "coming soon" in note
        # Asserted against the composited screen: a filename leaking onto the
        # page is a thing the user would *see*.
        drawn = "\n".join(
            "".join(segment.text for segment in strip._segments)
            for strip in app.screen._compositor.render_strips()
        )
        assert "vehicle" in drawn
        assert "vehicle.json" not in drawn
        assert str(tmp_path) not in drawn


async def test_spec_detail_escapes_markup_in_a_spec_name(tmp_path, monkeypatch):
    """A name is user-supplied text rendered through Rich markup — `mech[v2]`
    would otherwise render with a chunk missing."""
    app = _app(
        tmp_path,
        monkeypatch,
        raw=(("mech[v2]", json.dumps(schema.skeleton("mech[v2]"))),),
    )
    async with app.run_test() as pilot:
        await _open_spec(pilot, app)
        assert app.screen.model_type == "mech[v2]"
        assert "mech[v2]" in _title(app)


async def test_spec_detail_opens_a_malformed_spec_normally(tmp_path, monkeypatch):
    """Nothing reads the file, so unreadable JSON is not this screen's problem."""
    app = _app(tmp_path, monkeypatch, raw=(("broken", "{not json"),))
    async with app.run_test() as pilot:
        await _open_spec(pilot, app)

        assert app.screen.model_type == "broken"
        assert "broken" in _title(app)
        assert _text(app.screen.query_one("#placeholder-note", Static))


async def test_spec_detail_is_headed_with_the_stem_not_the_files_model_type(
    tmp_path, monkeypatch
):
    """The filename stem is the identity and wins over a disagreeing file."""
    app = _app(
        tmp_path,
        monkeypatch,
        raw=(("vehicle", json.dumps(schema.skeleton("spaceship"))),),
    )
    async with app.run_test() as pilot:
        await _open_spec(pilot, app)

        assert app.screen.model_type == "vehicle"
        assert "vehicle" in _title(app)
        assert "spaceship" not in _title(app)


async def test_spec_detail_has_no_focusable_widgets(tmp_path, monkeypatch):
    """Nothing to arrow through on a page with nothing to interact with."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test() as pilot:
        await _open_spec(pilot, app)
        assert app.screen.focus_chain == []


async def test_spec_detail_escape_returns_to_the_specs_screen(tmp_path, monkeypatch):
    """`escape` pops back to a Specs page with its rows still listed."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle", "character"))
    async with app.run_test() as pilot:
        await _open_spec(pilot, app)

        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecsScreen))
        screen = app.screen
        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 2)
        assert [row.model_type for row in screen.query(SpecRow)] == [
            "character",
            "vehicle",
        ]


async def test_spec_detail_quit_still_works(tmp_path, monkeypatch):
    """`q` must reach the app's global quit from the screen."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test() as pilot:
        await _open_spec(pilot, app)

        await pilot.press("q")
        assert await _wait_for(pilot, lambda: not app.is_running)


async def test_spec_detail_opens_without_a_valid_config(tmp_path):
    """It reads no settings at all, so it opens with `settings is None`."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")
    specs_store.create(tmp_path / "specs", "vehicle")

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.settings is None

        await pilot.press("enter")  # Specs is the only card there is
        assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecsScreen))
        assert await _wait_for(pilot, lambda: isinstance(app.screen.focused, SpecRow))
        await pilot.press("enter")

        assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecDetailScreen))
        assert "vehicle" in _title(app)


async def test_spec_detail_writes_nothing_to_disk(tmp_path, monkeypatch):
    """Opening a spec is read-only — and `specs/` is never created by it."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    spec = tmp_path / "specs" / "vehicle.json"
    before = spec.read_bytes()

    async with app.run_test() as pilot:
        await _open_spec(pilot, app)

        assert spec.read_bytes() == before
        assert sorted(p.name for p in (tmp_path / "specs").iterdir()) == [
            "vehicle.json"
        ]
