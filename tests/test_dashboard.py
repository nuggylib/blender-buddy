"""Dashboard config-display and section-navigation tests.

Drive the app through Textual's headless ``run_test()`` pilot (no TTY), pointing
at an injected ``config_path`` so tests never touch the real ``platformdirs``
location. Textual 8.x applies a ~50ms screen-switch delay, so we ``await
pilot.pause()`` before asserting.

The Godot scan (``find_projects``) is patched to a pure function here — the
filesystem-walk behavior is unit-tested in ``test_discovery.py``; these tests
exercise the wiring (worker → count) and the live existence markers.
"""

from pathlib import Path

from textual.widgets import Button, ContentSwitcher, Input, ListView, Static

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.blender import detect
from blender_buddy.blender.detect import ProbeOutcome, ProbeResult
from blender_buddy.config import store
from blender_buddy.config.settings import Settings
from blender_buddy.godot import discovery
from blender_buddy.tui.screens.blender_detail import BlenderDetailScreen
from blender_buddy.tui.screens.dashboard import DashboardScreen
from blender_buddy.tui.screens.godot_detail import GodotDetailScreen
from blender_buddy.tui.screens.models import ModelsScreen
from blender_buddy.tui.widgets.section_card import SectionCard


def _seed(cfg, models, godot, blender_exe="blender"):
    """Seed a valid config. `models` is one path or an iterable of them."""
    directories = (models,) if isinstance(models, str | Path) else tuple(models)
    store.save(
        cfg,
        Settings(
            blender_executable=blender_exe,
            blender_version="4.5.0",
            models_directories=tuple(str(d) for d in directories),
            godot_projects_root=str(godot),
        ),
    )


def _text(widget):
    """The plain rendered text of a Static, markup applied/stripped."""
    return str(widget.render())


def _models_rows(screen):
    """The rendered text of every Models row (one per configured directory)."""
    return [_text(row) for row in screen.query(".models-value")]


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

        assert _models_rows(screen) == [f"{models}  ✓ found"]
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
        (value,) = _models_rows(app.screen)
        assert str(missing) in value
        assert "✗" in value


async def test_dashboard_lists_every_models_directory(tmp_path, monkeypatch):
    """Multi-location display — one row per configured directory, in stored
    order, each with its own independent existence indicator."""
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    vehicles = tmp_path / "vehicles"
    vehicles.mkdir()
    props = tmp_path / "props"  # never created → its own "missing" marker
    characters = tmp_path / "characters"
    characters.mkdir()
    godot = tmp_path / "godot"
    godot.mkdir()
    _seed(cfg, [vehicles, props, characters], godot)

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert _models_rows(app.screen) == [
            f"{vehicles}  ✓ found",
            f"{props}  ✗ not found",
            f"{characters}  ✓ found",
        ]


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
        assert _models_rows(app.screen) == [f"{models}  ✓ found"]

        await pilot.press("s")
        assert await _wait_for(
            pilot, lambda: app.screen.__class__.__name__ == "SetupWizard"
        )
        wizard = app.screen
        switcher = wizard.query_one(ContentSwitcher)

        wizard.query_one("#next", Button).press()  # Blender prefilled → advance
        assert await _wait_for(pilot, lambda: switcher.current == "step-models")

        # Edit mode pre-populates the list; swap the one entry for a new one.
        listing = wizard.query_one("#models-list", ListView)
        assert len(listing) == 1
        listing.index = 0
        wizard.query_one("#remove-models", Button).press()
        assert await _wait_for(pilot, lambda: len(listing) == 0)

        wizard.query_one("#models-dir", Input).value = str(new_models)
        wizard.query_one("#add-models", Button).press()
        assert await _wait_for(pilot, lambda: len(listing) == 1)

        wizard.query_one("#next", Button).press()
        assert await _wait_for(pilot, lambda: switcher.current == "step-godot")

        wizard.query_one("#godot-root", Input).value = str(godot)
        wizard.query_one("#next", Button).press()  # Finish
        assert await _wait_for(pilot, lambda: isinstance(app.screen, DashboardScreen))

        assert await _wait_for(
            pilot, lambda: _models_rows(app.screen) == [f"{new_models}  ✓ found"]
        )


# -- section navigation ----------------------------------------------------


def _seeded_app(tmp_path, monkeypatch, directories=1):
    """A dashboard-booting app over a valid config with `directories` models dirs."""
    monkeypatch.setattr(discovery, "find_projects", lambda root, max_depth=4: [])
    cfg = tmp_path / "config.toml"
    godot = tmp_path / "godot"
    godot.mkdir()
    models = []
    for index in range(directories):
        directory = tmp_path / f"models-{index}"
        directory.mkdir()
        models.append(directory)
    _seed(cfg, models, godot)
    return BlenderBuddyApp(config_path=cfg)


async def test_dashboard_focuses_first_section_on_mount(tmp_path, monkeypatch):
    """Initial focus is deterministic — the first (top) section, not nothing."""
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        focused = app.screen.focused
        assert isinstance(focused, SectionCard)
        assert focused.id == "section-blender"


async def test_dashboard_focus_chain_is_exactly_the_sections(tmp_path, monkeypatch):
    """`down` steps through the three section cards and nothing else.

    Guards the navigation contract: a focusable widget sneaking onto the screen
    (a Button in a card, a scrolling wrapper) would add a stop the user has to
    arrow past to reach the next section.
    """
    app = _seeded_app(tmp_path, monkeypatch, directories=3)
    async with app.run_test() as pilot:
        await pilot.pause()
        visited = [app.screen.focused]
        for _ in range(3):
            await pilot.press("down")
            visited.append(app.screen.focused)

        assert all(isinstance(widget, SectionCard) for widget in visited)
        # Three stops, then back to the top — the chain holds no fourth widget.
        assert [widget.id for widget in visited] == [
            "section-blender",
            "section-models",
            "section-godot",
            "section-blender",
        ]


async def test_dashboard_focus_wraps_backwards(tmp_path, monkeypatch):
    """`up` from the first section wraps to the last, rather than losing focus."""
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("up")
        assert app.screen.focused.id == "section-godot"


async def test_dashboard_vim_keys_move_focus(tmp_path, monkeypatch):
    """`j`/`k` are bound alongside the arrows."""
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("j")
        assert app.screen.focused.id == "section-models"
        await pilot.press("k")
        assert app.screen.focused.id == "section-blender"


async def test_dashboard_enter_opens_each_sections_detail_screen(tmp_path, monkeypatch):
    """Each section opens its own detail screen, and `escape` comes back.

    Walks all three in one app so the full round trip — push, pop, and the focus
    still being where it was left — is exercised, not just a single hop.
    """
    app = _seeded_app(tmp_path, monkeypatch)
    expected = [
        ("section-blender", BlenderDetailScreen),
        ("section-models", ModelsScreen),
        ("section-godot", GodotDetailScreen),
    ]
    async with app.run_test() as pilot:
        await pilot.pause()
        for section_id, screen_class in expected:
            assert app.screen.focused.id == section_id
            await pilot.press("enter")
            # `cls=` binds this iteration's class — a bare closure over the loop
            # variable would read whatever it held when the lambda finally ran.
            assert await _wait_for(
                pilot, lambda cls=screen_class: isinstance(app.screen, cls)
            )

            await pilot.press("escape")
            assert await _wait_for(
                pilot, lambda: isinstance(app.screen, DashboardScreen)
            )
            assert app.screen.focused.id == section_id
            await pilot.press("down")


async def test_dashboard_restores_focus_after_settings_change(tmp_path, monkeypatch):
    """A config change recomposes the screen — the highlight must not move.

    `recompose()` destroys every widget, so without an explicit restore the
    user's highlight silently jumps back to the top after saving an edit.
    """
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("down")  # focus Models
        assert app.screen.focused.id == "section-models"

        replacement = tmp_path / "replacement"
        replacement.mkdir()
        app.settings = Settings(
            blender_executable=app.settings.blender_executable,
            blender_version=app.settings.blender_version,
            models_directories=(str(replacement),),
            godot_projects_root=app.settings.godot_projects_root,
        )

        assert await _wait_for(
            pilot, lambda: _models_rows(app.screen) == [f"{replacement}  ✓ found"]
        )
        assert app.screen.focused.id == "section-models"


async def test_dashboard_restores_focus_to_first_when_section_is_gone(
    tmp_path, monkeypatch
):
    """Falling back to the first section beats leaving focus nowhere.

    Sections are fixed today, so this drives the fallback by asking for an id
    that was never rendered — the same path a removed section would take.
    """
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        app.screen._focus_section("section-does-not-exist")
        assert app.screen.focused.id == "section-blender"


async def test_dashboard_navigation_is_inert_without_a_valid_config(tmp_path):
    """A corrupt config renders a prompt and no sections — so the navigation
    keys have nothing to act on and must not raise."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert not app.screen.query(SectionCard)
        assert app.screen.focused is None

        await pilot.press("down", "up", "j", "k", "enter")
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)
        assert app.screen.focused is None


async def test_dashboard_quit_still_works_from_a_focused_section(tmp_path, monkeypatch):
    """`q` must reach the app's global quit from a focused card.

    Unlike the wizard, these screens hold no Input, so the wizard's
    `q`-shadowing must not be copied onto them.
    """
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert isinstance(app.screen.focused, SectionCard)
        await pilot.press("q")
        assert await _wait_for(pilot, lambda: not app.is_running)


async def test_dashboard_footer_advertises_the_navigation_keys(tmp_path, monkeypatch):
    """The footer is the only place these keys are discoverable, so assert on
    what it draws from: the screen's active bindings, including the focused
    card's. `↑↓ Move` appears once, not as two separate rows."""
    app = _seeded_app(tmp_path, monkeypatch)
    async with app.run_test() as pilot:
        await pilot.pause()
        shown = [
            (binding.key_display or binding.key, binding.description)
            for _node, binding, enabled, _tooltip in app.screen.active_bindings.values()
            if binding.show and enabled
        ]
        assert ("↑↓", "Move") in shown
        assert [entry for entry in shown if entry[1] == "Move"] == [("↑↓", "Move")]
        assert ("enter", "Open") in shown
        assert ("s", "Setup") in shown
        assert ("q", "Quit") in shown


async def test_dashboard_footer_drops_open_without_a_valid_config(tmp_path):
    """No cards means no `enter` binding to advertise — the hint disappears with
    the thing it acts on rather than lingering as a dead key."""
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not valid toml {{{")

    app = BlenderBuddyApp(config_path=cfg)
    async with app.run_test() as pilot:
        await pilot.pause()
        descriptions = {
            binding.description
            for _node, binding, enabled, _tooltip in app.screen.active_bindings.values()
            if binding.show and enabled
        }
        assert "Open" not in descriptions
        assert "Setup" in descriptions
