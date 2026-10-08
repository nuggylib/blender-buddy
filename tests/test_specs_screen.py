"""Specs screen tests.

Drive the app through Textual's headless ``run_test()`` pilot, pointing at an
injected ``config_path``. The screen is still a placeholder, so these cover the
wiring: it is reachable, `escape` comes back, and — unlike the config-derived
detail screens — it renders the same with no valid config at all.
"""

from textual.widgets import Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.config import store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.tui.screens.dashboard import DashboardScreen
from blender_buddy.tui.screens.specs import SpecsScreen


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


def _app(tmp_path, monkeypatch):
    """A dashboard-booting app over a valid config."""
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    models = tmp_path / "models"
    models.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()
    store.save(
        cfg,
        Settings(
            blender_executable="blender",
            blender_version="4.5.0",
            models_directories=(str(models),),
            godot_projects_root=str(godot),
        ),
    )
    return BlenderBuddyApp(config_path=cfg)


async def test_specs_screen_renders_its_placeholder_note(tmp_path, monkeypatch):
    """The page says what is coming rather than opening empty."""
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)

        note = app.screen.query_one("#placeholder-note", Static)
        assert "coming soon" in _text(note)
        assert _text(app.screen.query_one(".section-title", Static)) == "Specs"


async def test_specs_screen_escape_returns_to_the_dashboard(tmp_path, monkeypatch):
    """`escape` pops, so the screen is not a one-way trip."""
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)

        await pilot.press("escape")
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))


async def test_specs_screen_mounts_without_a_valid_config(tmp_path):
    """It reads no settings, so it has no `#setup-prompt` branch and must render
    identically with `settings is None` instead of raising."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.settings is None

        await pilot.press("enter")  # Specs is the only card there is
        assert await _wait_for(pilot, lambda: isinstance(app.screen, SpecsScreen))
        assert not app.screen.query("#setup-prompt")
        assert "coming soon" in _text(app.screen.query_one("#placeholder-note", Static))


async def test_specs_screen_quit_still_works(tmp_path, monkeypatch):
    """`q` must reach the app's global quit from the screen."""
    app = _app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await _open_specs(pilot, app)

        await pilot.press("q")
        assert await _wait_for(pilot, lambda: not app.is_running)
