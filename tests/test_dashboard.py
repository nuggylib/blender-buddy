"""Dashboard config-display tests.

Drive the app through Textual's headless ``run_test()`` pilot (no TTY), pointing
at an injected ``config_path`` so tests never touch the real ``platformdirs``
location. Textual 8.x applies a ~50ms screen-switch delay, so we ``await
pilot.pause()`` before asserting.

The Godot scan (``find_projects``) is patched to a pure function here — the
filesystem-walk behavior is unit-tested in ``test_discovery.py``; these tests
exercise the wiring (worker → count) and the live existence markers.
"""

from textual.widgets import Button, ContentSwitcher, Input, Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.blender import detect
from blender_buddy.blender.detect import ProbeOutcome, ProbeResult
from blender_buddy.config import store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.tui.screens.dashboard import DashboardScreen


def _seed(cfg, models, godot, blender_exe="blender"):
    store.save(
        cfg,
        Settings(
            blender_executable=blender_exe,
            blender_version="4.5.0",
            models_directory=str(models),
            godot_projects_root=str(godot),
        ),
    )


def _text(widget):
    """The plain rendered text of a Static, markup applied/stripped."""
    return str(widget.render())


async def _wait_for(pilot, predicate, tries=100):
    for _ in range(tries):
        if predicate():
            return True
        await pilot.pause()
    return False


async def test_dashboard_shows_three_sections_in_order(tmp_path, monkeypatch):
    """Scenario 1 — a valid config renders Blender → Models → Godot with values."""
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    models = tmp_path / "models"
    models.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()
    _seed(cfg, models, godot)

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)

        order = [section.id for section in screen.query(".section")]
        assert order == ["section-blender", "section-models", "section-godot"]

        assert str(models) in _text(screen.query_one("#models-value", Static))
        assert str(godot) in _text(screen.query_one("#godot-value", Static))


async def test_dashboard_marks_missing_models_dir(tmp_path, monkeypatch):
    """Scenario 2 — a deleted models directory shows a 'not found' marker and the
    app does not crash."""
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    missing = tmp_path / "gone"  # never created
    godot = tmp_path / "godot"
    godot.mkdir()
    _seed(cfg, missing, godot)

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        value = _text(app.screen.query_one("#models-value", Static))
        assert str(missing) in value
        assert "✗" in value


async def test_dashboard_shows_setup_prompt_when_corrupt(tmp_path):
    """Corrupt/None state — a single 'run setup' prompt, not empty section shells."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        assert app.settings is None
        prompt = screen.query_one("#setup-prompt", Static)
        assert "setup" in _text(prompt).lower()
        assert not screen.query(".section")  # no section shells rendered


async def test_dashboard_godot_count_from_worker(tmp_path, monkeypatch):
    """Godot count — computed in a worker and rendered (zero is a valid 0)."""
    projects = [tmp_path / "a", tmp_path / "b"]
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: projects)
    cfg = tmp_path / "config.toml"
    models = tmp_path / "models"
    models.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()
    _seed(cfg, models, godot)

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        count = app.screen.query_one("#godot-count", Static)
        assert await _wait_for(pilot, lambda: "2" in _text(count))


async def test_dashboard_refreshes_after_edit(tmp_path, monkeypatch):
    """Scenario 3 — editing config via `s` and saving updates the dashboard's
    displayed value without an app restart."""
    monkeypatch.setattr(
        detect,
        "probe_version",
        lambda exe, timeout=10.0: ProbeResult(ProbeOutcome.OK, version="4.5.0"),
    )
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    models = tmp_path / "models"
    models.mkdir()
    new_models = tmp_path / "new-models"
    new_models.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()
    _seed(cfg, models, godot)

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert str(models) in _text(app.screen.query_one("#models-value", Static))

        await pilot.press("s")
        assert await _wait_for(
            pilot, lambda: app.screen.__class__.__name__ == "SetupWizard"
        )
        wizard = app.screen
        switcher = wizard.query_one(ContentSwitcher)

        wizard.query_one("#next", Button).press()  # Blender prefilled → advance
        assert await _wait_for(pilot, lambda: switcher.current == "step-models")

        wizard.query_one("#models-dir", Input).value = str(new_models)
        wizard.query_one("#next", Button).press()
        assert await _wait_for(pilot, lambda: switcher.current == "step-godot")

        wizard.query_one("#godot-root", Input).value = str(godot)
        wizard.query_one("#next", Button).press()  # Finish
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))

        assert await _wait_for(
            pilot,
            lambda: (
                str(new_models) in _text(app.screen.query_one("#models-value", Static))
            ),
        )
