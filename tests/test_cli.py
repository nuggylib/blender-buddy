"""Covers the non-interactive CLI surface the release pipeline depends on:
``blender-buddy --version`` and ``blender-buddy --check``.
"""

import pytest

import blender_buddy
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
