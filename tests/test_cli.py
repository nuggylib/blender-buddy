"""Covers the non-interactive CLI surface the release pipeline depends on:
``blender-buddy --version`` and ``blender-buddy --check``, plus the ``--setup``
flag's routing into the app (without spinning up a real TTY).
"""

import pytest

import blender_buddy
import blender_buddy.app
from blender_buddy.app import main
from blender_buddy.diagnostics import run_headless_check


def test_version_flag_echoes_version(capsys):
    # argparse's action="version" prints then exits 0.
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert blender_buddy.__version__ in capsys.readouterr().out


async def test_check_mounts_headlessly_and_succeeds():
    # Awaited directly (not via main()'s asyncio.run) so it composes with the
    # loop pytest-asyncio already provides. Regression guard for the app.tcss
    # bundling fix: a stylesheet or hidden-import failure raises here.
    await run_headless_check()


class _FakeApp:
    """Stand-in for BlenderBuddyApp so we can assert wiring without a TTY."""

    def __init__(self, force_setup: bool = False) -> None:
        self.force_setup = force_setup
        self.ran = False

    def run(self) -> None:
        self.ran = True


def test_setup_flag_launches_app_in_setup_mode(monkeypatch):
    created = {}
    monkeypatch.setattr(
        blender_buddy.app,
        "BlenderBuddyApp",
        lambda **kwargs: created.setdefault("app", _FakeApp(**kwargs)),
    )
    main(["--setup"])
    assert created["app"].force_setup is True
    assert created["app"].ran is True


def test_bare_invocation_does_not_force_setup(monkeypatch):
    created = {}
    monkeypatch.setattr(
        blender_buddy.app,
        "BlenderBuddyApp",
        lambda **kwargs: created.setdefault("app", _FakeApp(**kwargs)),
    )
    main([])
    assert created["app"].force_setup is False
    assert created["app"].ran is True
