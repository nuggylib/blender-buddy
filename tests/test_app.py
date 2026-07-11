"""Smoke test for the Blender Buddy app skeleton.

Uses Textual's headless ``run_test()`` pilot harness (no TTY required), the
pattern every future UI test inherits. ``asyncio_mode = "auto"`` (pyproject)
lets these async tests run without a per-test marker.
"""

from blender_buddy.app import BlenderBuddyApp
from blender_buddy.tui.screens.dashboard import DashboardScreen


async def test_app_boots_dashboard_and_quits():
    app = BlenderBuddyApp()
    async with app.run_test(size=(80, 24)) as pilot:
        assert isinstance(app.screen, DashboardScreen)
        await pilot.press("q")
    # Exiting the context asserts a clean shutdown; verify the exit code too.
    assert app.return_code == 0
