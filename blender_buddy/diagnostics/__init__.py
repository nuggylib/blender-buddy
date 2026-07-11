"""Build/launch diagnostics for the release pipeline.

Self-tests that verify a *packaged* Blender Buddy actually launches. These live
apart from ``app.py`` on purpose: they are packaging concerns (run by CI against
a frozen binary), not application behavior, and they carry their own knobs (e.g.
the smoke-test timeout) rather than pushing them onto ``BlenderBuddyApp``.
"""

from blender_buddy.diagnostics.smoke import run_headless_check

__all__ = ["run_headless_check"]
