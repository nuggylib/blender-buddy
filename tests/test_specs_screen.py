"""Specs screen tests.

Drive the app through Textual's headless ``run_test()`` pilot, pointing at an
injected ``config_path`` — which is also what fixes ``app.specs_dir``, since the
specs directory is derived from the config *path*. The store's filesystem
behavior is unit-tested in ``test_specs_store.py``; these tests exercise the
wiring (worker → rows → fix steps) and the navigation.
"""

import json

from textual.widgets import Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.config import store as config_store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.specs import schema
from blender_buddy.specs import store as specs_store
from blender_buddy.tui.screens.dashboard import DashboardScreen
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


async def _open_specs(pilot, app):
    """Navigate the dashboard to the Specs screen.

    Driven through the pilot rather than `app.push_screen`: pushing from the
    test's own thread races the new `Header`'s mount.
    """
    await pilot.pause()
    await pilot.press("down")  # Blender → Specs
    await pilot.press("enter")
    assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecsScreen))


def _app(tmp_path, monkeypatch, specs=(), broken=()):
    """A dashboard-booting app over a valid config, with `specs` on disk.

    `broken` names spec files hand-written as raw text (the unreadable cases).
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
    for name, payload in broken:
        directory = tmp_path / "specs"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f"{name}.json").write_text(payload, encoding="utf-8")
    return BlenderBuddyApp(config_path=cfg)


def _row_labels(screen):
    return [_text(row) for row in screen.query(SpecRow)]


def _fix_steps(screen):
    return [_text(step) for step in screen.query(".fix-step")]


async def test_specs_screen_lists_the_specs_on_disk(tmp_path, monkeypatch):
    """One focusable row per spec, sorted by name, with a count."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle", "character", "prop"))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen

        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 3)
        assert _row_labels(screen) == ["▸ character", "▸ prop", "▸ vehicle"]
        assert _text(screen.query_one("#specs-summary", Static)) == "3 specs"
        assert _fix_steps(screen) == []
        assert not screen.query("#specs-empty")


async def test_specs_screen_counts_one_spec_in_the_singular(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        summary = app.screen.query_one("#specs-summary", Static)
        assert await _wait_for(pilot, lambda: _text(summary) == "1 spec")


async def test_specs_screen_empty_state_is_a_note_not_a_problem(tmp_path, monkeypatch):
    """Zero specs is the normal state on a fresh install, so it gets a plain
    note and contributes no fix step — unlike a models directory with none."""
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen

        assert await _wait_for(pilot, lambda: bool(screen.query("#specs-empty")))
        note = _text(screen.query_one("#specs-empty", Static))
        assert "No specs yet" in note
        assert "n" in note  # says how to make one
        assert not screen.query(SpecRow)
        assert _fix_steps(screen) == []
        assert not screen.query_one("#fix-panel").display
        # Read-only: listing an absent directory must not create it.
        assert not (tmp_path / "specs").exists()


async def test_specs_screen_marks_an_unreadable_spec_and_keeps_the_good_ones(
    tmp_path, monkeypatch
):
    """One malformed file never hides the rest — it is marked and gets a step."""
    app = _app(
        tmp_path,
        monkeypatch,
        specs=("vehicle", "character"),
        broken=(("broken", "{not json"),),
    )
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen

        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 3)
        labels = _row_labels(screen)
        assert labels[0].startswith("▸ broken")
        assert "unreadable" in labels[0]
        assert labels[1:] == ["▸ character", "▸ vehicle"]

        (step,) = _fix_steps(screen)
        assert "unreadable" in step
        assert "JSON" in step
        # The good rows are still focus stops.
        assert all(row.can_focus for row in screen.query(SpecRow))


async def test_specs_screen_marks_a_name_mismatch(tmp_path, monkeypatch):
    """The stem is the identity, so a file disagreeing with it is surfaced."""
    app = _app(tmp_path, monkeypatch)
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "vehicle.json").write_text(
        json.dumps(schema.skeleton("spaceship")), encoding="utf-8"
    )
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen

        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 1)
        (label,) = _row_labels(screen)
        assert "mismatch" in label

        (step,) = _fix_steps(screen)
        assert "mismatch" in step
        assert "filename wins" in step


async def test_specs_screen_fix_block_lists_both_problems_present(
    tmp_path, monkeypatch
):
    """Both problem states at once — one step each, in a fixed order."""
    app = _app(tmp_path, monkeypatch, broken=(("broken", "{nope"),))
    specs = tmp_path / "specs"
    (specs / "vehicle.json").write_text(
        json.dumps(schema.skeleton("spaceship")), encoding="utf-8"
    )
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen

        assert await _wait_for(pilot, lambda: len(_fix_steps(screen)) == 2)
        unreadable, mismatched = _fix_steps(screen)
        assert "unreadable" in unreadable
        assert "mismatch" in mismatched


async def test_specs_screen_escapes_markup_in_a_spec_name(tmp_path, monkeypatch):
    """A name is user-supplied text rendered through Rich markup — `mech[v2]`
    would otherwise render with a chunk missing."""
    app = _app(tmp_path, monkeypatch)
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "mech[v2].json").write_text(
        json.dumps(schema.skeleton("mech[v2]")), encoding="utf-8"
    )
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen
        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 1)
        assert _row_labels(screen) == ["▸ mech[v2]"]


async def test_specs_screen_focus_chain_is_exactly_the_rows(tmp_path, monkeypatch):
    """Rows are the only focus stops — the scroller must opt out, or it becomes
    a stop the user arrows past."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle", "character"))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen
        assert await _wait_for(pilot, lambda: len(screen.query(SpecRow)) == 2)

        assert not screen.query_one("#detail-panel").can_focus
        assert await _wait_for(pilot, lambda: isinstance(screen.focused, SpecRow))
        assert screen.focused.model_type == "character"

        await pilot.press("down")
        assert screen.focused.model_type == "vehicle"
        await pilot.press("j")  # wraps, and the vim alias is bound
        assert screen.focused.model_type == "character"
        await pilot.press("k")
        assert screen.focused.model_type == "vehicle"


async def test_specs_screen_enter_on_a_row_persists_nothing(tmp_path, monkeypatch):
    """A deliberately inert seam: it confirms the choice and says so."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        screen = app.screen
        assert await _wait_for(pilot, lambda: isinstance(screen.focused, SpecRow))

        before = config_store.load(app._config_path)
        await pilot.press("enter")
        await pilot.pause()

        notices = [str(notification.message) for notification in app._notifications]
        assert any("vehicle" in notice for notice in notices)
        assert any("not wired up yet" in notice for notice in notices)
        assert config_store.load(app._config_path) == before


async def test_specs_screen_escape_returns_to_the_dashboard(tmp_path, monkeypatch):
    """`escape` pops, so the screen is not a one-way trip."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)

        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))


async def test_specs_screen_lists_without_a_valid_config(tmp_path):
    """It reads a path derived from the config *path*, not its contents — so it
    has no `#setup-prompt` branch and lists normally with `settings is None`."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")
    specs_store.create(tmp_path / "specs", "vehicle")

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.settings is None

        await pilot.press("enter")  # Specs is the only card there is
        assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecsScreen))
        screen = app.screen
        assert not screen.query("#setup-prompt")
        assert await _wait_for(pilot, lambda: _row_labels(screen) == ["▸ vehicle"])


async def test_specs_screen_quit_still_works(tmp_path, monkeypatch):
    """`q` must reach the app's global quit from the screen."""
    app = _app(tmp_path, monkeypatch, specs=("vehicle",))
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)

        await pilot.press("q")
        assert await _wait_for(pilot, lambda: not app.is_running)


async def test_specs_screen_survives_being_closed_mid_load(tmp_path, monkeypatch):
    """Popping the screen while the worker is in flight must not crash it."""
    import asyncio
    import time

    app = _app(tmp_path, monkeypatch, specs=("vehicle",))

    def slow_list(specs_dir):
        time.sleep(0.2)
        return []

    monkeypatch.setattr(specs_store, "list_specs", slow_list)

    async with app.run_test() as pilot:
        await _open_specs(pilot, app)
        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))

        await asyncio.sleep(0.3)  # let the worker's thread finish and return
        await pilot.pause()
        assert app.is_running
        assert isinstance(app.screen, DashboardScreen)
