# blender_buddy/tui/screens/

Full-page Textual `Screen` subclasses. Each screen is one landing view or page
in the app (analogous to a route in a web app).

## Contents
- `dashboard.py` — `DashboardScreen`, the landing view. Renders the three
  configured anchors as stacked sections — **Blender (top) → Models (middle) →
  Godot (bottom)** — each with a live existence/validity marker. The Models
  section renders **one row per configured directory**, in stored order, each
  with its own independent marker (the schema and the wizard both enforce at
  least one, so there is no empty state). It reads
  `self.app.settings` (app-level state) and never touches TOML or the filesystem
  beyond cheap stats: Blender validity via `detect.executable_state` (three
  states — valid / present-but-not-executable / missing — platform-aware, no
  subprocess), Models/Godot-root existence via `is_dir` inline. The one
  filesystem *walk* — the Godot project count — runs in a `@work` worker
  (`asyncio.to_thread(discovery.find_projects, …)`) showing "Scanning…" until it
  returns (zero projects is a valid `0`). It `watch`es the app's `settings`
  reactive and `recompose`s on change, so editing config via `s` refreshes the
  view without a restart. When `self.app.settings is None` (absent/corrupt
  config) it shows a single "run setup" prompt, not empty section shells. Its
  `s` binding (`app.open_setup`) re-opens the setup wizard in edit mode. Future
  work adds live validation results from a Blender-polling worker and
  per-category detail screens.
- `setup_wizard.py` — `SetupWizard(Screen[Settings | None])`, the first-time
  setup flow. A 3-step Back/Next `ContentSwitcher` (Blender executable → models
  directories → Godot root) that returns a `Settings` via `dismiss()`, or `None`
  on cancel. Pass `existing=Settings` to open pre-populated in *edit mode*.
  **Step 2 is an add/remove list** (the codebase's only `ListView`): an `Input` +
  **Add** feeds a `ListView`, and **Remove** deletes the highlighted row. Per-Add
  validation reuses the single-directory rules — normalize, accept a directory,
  reject a file, offer **Create directory** for a missing one — and dedups,
  scoped to the path in the box at Add time so a rejected Add never disturbs the
  rows already added. Key contract: **Enter in the models box Adds**, it does not
  advance; **Next gates on the list being non-empty**, not on the box; and text
  typed but never Added blocks Next with a hint rather than being silently
  dropped or silently auto-added. Edit mode fills the list from
  `existing.models_directories` and leaves the box **blank** (prefilling it would
  invite a duplicate and trip the unadded-text guard on a no-op edit).

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
- A screen that must not honor the app's global `q`-quit binding shadows it with
  its own `q` binding (a hidden no-op action). A focused `Input` already swallows
  a typed `q` as text, but a focused `Button` would let `q` bubble to the app —
  the screen-level binding closes that gap regardless of what holds focus.
