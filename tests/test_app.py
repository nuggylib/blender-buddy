"""Boot-routing and first-time-setup integration tests.

Drive the app through Textual's headless ``run_test()`` pilot (no TTY). Config is
always seeded/pointed through an injected ``config_path`` so tests never touch
the developer's real ``platformdirs`` directory. Textual 8.x applies a ~50ms
screen-switch delay, so we ``await pilot.pause()`` before asserting the screen.

The wizard's slow steps (``probe_version`` / ``find_projects``) are patched to
pure functions here — the subprocess and filesystem-walk behavior is unit-tested
in ``test_detect.py`` / ``test_discovery.py``; these tests exercise the wiring.
Windows-path serialization round-tripping is covered in ``test_config.py``.
"""

from textual.widgets import Button, ContentSwitcher, Input

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.blender import detect
from blender_buddy.blender.detect import ProbeOutcome, ProbeResult
from blender_buddy.config import store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.tui.screens.dashboard import DashboardScreen


def _seed_valid_config(path):
    store.save(
        path,
        Settings(
            blender_executable="blender",
            blender_version="4.5.0",
            models_directory=str(path.parent),
            godot_projects_root=str(path.parent),
        ),
    )


async def _wait_for(pilot, predicate, tries=100):
    """Pump the event loop until ``predicate()`` is true (or we give up)."""
    for _ in range(tries):
        if predicate():
            return True
        await pilot.pause()
    return False


async def test_valid_config_boots_dashboard(tmp_path):
    """Scenario 4 — a valid config boots straight to the dashboard."""
    cfg = tmp_path / "config.toml"
    _seed_valid_config(cfg)
    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        await pilot.press("q")
    assert app.return_code == 0


async def test_absent_config_shows_wizard(tmp_path):
    """Scenario 1 (part 1) — no config lands on the wizard, not the dashboard."""
    app = BlenderBuddyApp(config_path=tmp_path / "config.toml")
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "SetupWizard"
        await pilot.press("escape")


async def test_first_run_completes_and_writes_config(tmp_path, monkeypatch):
    """Scenario 1 (part 2) — walking all 3 steps writes a valid config, then the
    dashboard shows. Blender probe and Godot scan are patched to pure functions."""
    monkeypatch.setattr(
        detect,
        "probe_version",
        lambda exe, timeout=10.0: ProbeResult(ProbeOutcome.OK, version="4.5.0"),
    )
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    models = tmp_path / "models"
    models.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        wizard = app.screen
        switcher = wizard.query_one(ContentSwitcher)

        # Button.press() (not pilot.click) is used to drive Next: clicking the
        # same button twice in quick succession is swallowed by its 0.2s
        # `-active` guard, whereas press() posts the message deterministically.
        wizard.query_one("#blender-path", Input).value = "/fake/blender"
        wizard.query_one("#next", Button).press()
        assert await _wait_for(pilot, lambda: switcher.current == "step-models")

        wizard.query_one("#models-dir", Input).value = str(models)
        wizard.query_one("#next", Button).press()
        assert await _wait_for(pilot, lambda: switcher.current == "step-godot")

        wizard.query_one("#godot-root", Input).value = str(godot)
        wizard.query_one("#next", Button).press()  # Finish
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))

    state, settings = store.load(cfg)
    assert state == store.VALID
    assert settings.blender_version == "4.5.0"
    assert settings.models_directory == str(models)
    assert settings.godot_projects_root == str(godot)


async def test_missing_models_dir_offers_creation(tmp_path, monkeypatch):
    """Step 2 — a missing models directory reveals a Create button that makes it
    and advances."""
    monkeypatch.setattr(
        detect,
        "probe_version",
        lambda exe, timeout=10.0: ProbeResult(ProbeOutcome.OK, version="4.5.0"),
    )
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    new_models = tmp_path / "does-not-exist-yet"

    app = BlenderBuddyApp(config_path=tmp_path / "config.toml")
    async with app.run_test() as pilot:
        await pilot.pause()
        wizard = app.screen
        switcher = wizard.query_one(ContentSwitcher)
        create_button = wizard.query_one("#create-models", Button)

        wizard.query_one("#blender-path", Input).value = "/fake/blender"
        wizard.query_one("#next", Button).press()
        assert await _wait_for(pilot, lambda: switcher.current == "step-models")

        assert "hidden" in create_button.classes  # not offered until we try
        wizard.query_one("#models-dir", Input).value = str(new_models)
        wizard.query_one("#next", Button).press()
        assert await _wait_for(pilot, lambda: "hidden" not in create_button.classes)
        assert not new_models.exists()

        create_button.press()
        assert await _wait_for(pilot, lambda: switcher.current == "step-godot")
        assert new_models.is_dir()  # created on demand


async def test_quit_mid_wizard_writes_no_config(tmp_path):
    """Scenario 2 — cancelling mid-wizard writes no config and exits cleanly."""
    cfg = tmp_path / "config.toml"
    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.screen.__class__.__name__ == "SetupWizard"
        await pilot.press("escape")  # cancel → first-run exits
        await pilot.pause()
    assert not cfg.exists()
    assert app.return_code == 0


async def test_corrupt_config_boots_dashboard_and_is_not_overwritten(tmp_path):
    """Scenario 3 — a corrupt config boots the dashboard (with a recovery notice)
    and is never auto-overwritten."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")
    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
    assert cfg.read_text() == "this is not valid toml {{{"


async def test_dashboard_s_reopens_wizard_prefilled_and_cancel_preserves(tmp_path):
    """Re-run in edit mode: `s` opens the wizard pre-populated; cancel keeps the
    prior config unchanged."""
    cfg = tmp_path / "config.toml"
    _seed_valid_config(cfg)
    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        await pilot.press("s")
        assert await _wait_for(
            pilot, lambda: app.screen.__class__.__name__ == "SetupWizard"
        )
        assert app.screen.query_one("#blender-path", Input).value == "blender"
        await pilot.press("escape")  # cancel keeps prior config
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))

    state, settings = store.load(cfg)
    assert state == store.VALID
    assert settings.blender_executable == "blender"


async def test_typing_q_in_a_field_does_not_quit(tmp_path):
    """`q` typed into a focused path field is text input, not the quit binding."""
    app = BlenderBuddyApp(config_path=tmp_path / "config.toml")
    async with app.run_test() as pilot:
        await pilot.pause()
        wizard = app.screen
        assert wizard.__class__.__name__ == "SetupWizard"
        blender_input = wizard.query_one("#blender-path", Input)
        blender_input.value = ""
        blender_input.focus()
        await pilot.pause()
        await pilot.press("q")
        await pilot.pause()
        assert app.screen is wizard  # still on the wizard, app didn't quit
        assert "q" in blender_input.value


async def test_force_setup_opens_wizard_over_dashboard(tmp_path):
    """--setup opens the wizard even when a valid config exists, pre-populated."""
    cfg = tmp_path / "config.toml"
    _seed_valid_config(cfg)
    app = BlenderBuddyApp(config_path=cfg, force_setup=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert await _wait_for(
            pilot, lambda: app.screen.__class__.__name__ == "SetupWizard"
        )
        assert app.screen.query_one("#blender-path", Input).value == "blender"
        await pilot.press("escape")
