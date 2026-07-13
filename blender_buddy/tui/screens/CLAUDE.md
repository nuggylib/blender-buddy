# blender_buddy/tui/screens/

Full-page Textual `Screen` subclasses. Each screen is one landing view or page
in the app (analogous to a route in a web app).

## Contents
- `dashboard.py` — `DashboardScreen`, the landing view. Currently a placeholder;
  future work makes it display live validation results from a Blender-polling
  worker and lets the user open per-category detail screens. Its `s` binding
  (`app.open_setup`) re-opens the setup wizard in edit mode.
- `setup_wizard.py` — `SetupWizard(Screen[Settings | None])`, the first-time
  setup flow. A 3-step Back/Next `ContentSwitcher` (Blender executable → models
  directory → Godot root) that returns a `Settings` via `dismiss()`, or `None`
  on cancel. Pass `existing=Settings` to open pre-populated in *edit mode*.

## Conventions
- One screen per file, named `<Name>Screen` (the wizard is the deliberate
  exception — it is a modal returning a value, not a landing view).
- Register landing screens in `BlenderBuddyApp.SCREENS` and navigate with
  `push_screen` / `pop_screen`; push value-returning screens with
  `push_screen_wait` from inside a `@work` worker.
- **Keep slow/blocking work out of the event loop and out of the screen.** The
  wizard owns no `subprocess`, filesystem *walk*, or TOML: it calls the
  `blender` (`detect.probe_version`) and `godot` (`discovery.find_projects`)
  categories inside Textual `@work` workers (via `asyncio.to_thread`) so the UI
  never freezes; the app, not the screen, persists the result. Cheap inline
  stats (`is_dir`, `mkdir`) and the fast `candidate_paths()` prefill are fine.
- A screen that must not honor the app's global `q`-quit binding simply omits a
  `q` binding and relies on a focused `Input` swallowing the keypress.
