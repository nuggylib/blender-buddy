# blender_buddy/diagnostics/

Build/launch diagnostics: self-tests that verify a **packaged** Blender Buddy
actually launches. These are release-pipeline concerns, deliberately kept out of
`app.py` so the application module carries no CI/packaging machinery.

## Files
- `smoke.py` — `run_headless_check()`, the headless launch gate. Mounts the app
  through Textual's pilot (forcing `app.tcss` to parse and the import graph to
  resolve) and raises on failure. Owns its own `_CHECK_TIMEOUT_SECONDS`.
- `__init__.py` — re-exports `run_headless_check`.

## Conventions
- `app.py`'s `main()` dispatches `blender-buddy --check` here via a lazy import
  (avoids an import cycle: this module imports `BlenderBuddyApp` lazily too).
- Knobs that belong to a check (timeouts, sizes) live with the check, not on
  `BlenderBuddyApp`.
- Anything here must be awaitable directly from tests under
  `asyncio_mode = "auto"` — don't wrap coroutines in `asyncio.run()` at module
  or function boundaries the tests call into.
