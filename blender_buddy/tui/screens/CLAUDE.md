# blender_buddy/tui/screens/

Full-page Textual `Screen` subclasses. Each screen is one landing view or page
in the app (analogous to a route in a web app).

## Contents
- `dashboard.py` — `DashboardScreen`, the landing view **and navigation hub**.
  Renders the three
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
  `s` binding (`app.open_setup`) re-opens the setup wizard in edit mode.
  **Navigation:** each section is a focusable `SectionCard` (see
  `../widgets/CLAUDE.md`); `down`/`j` → `app.focus_next` and `up`/`k` →
  `app.focus_previous` step through them (wrapping at both ends), and `enter` on
  a card posts `SectionCard.Opened`, which `on_section_card_opened` turns into a
  `push_screen(target)`. The cards are the screen's **only** focus stops — a
  test asserts the chain is exactly the three sections, because anything else
  focusable here is a widget the user has to arrow past. `_focus_section()`
  focuses the first section on mount and, critically, **re-focuses the same
  section after `recompose()`**: a config edit tears down every widget, so
  without the save-and-restore the user's highlight silently jumps to the top
  after saving. With no valid config there are no cards, so the navigation keys
  are harmless no-ops. Future work adds live validation results from a
  Blender-polling worker.
- `models.py` — `ModelsScreen`, the Models detail view. One group per configured
  directory, in stored order, each ending in **one of four states**, and that
  distinction is the point of the page: a directory that *exists* but holds no
  models reads as a healthy `✓ found` on the dashboard, which is exactly how a
  mis-pointed directory hides. So **missing** (`is_dir()` inline), **unreadable**
  (the scan raised `OSError`), **empty** (`0 models`), and **populated** each
  render differently, and each problem state contributes a step to the
  `#fix-panel` block (a `FixPanel`, workflow step 7). That block sits **outside**
  the scroller so a long model list can't push it off screen, and shows only the
  problems the scan actually found — a healthy page shows nothing and the list
  takes the full height. The scan is delegated to the `models`
  category inside `@work(exclusive=True, group="models-scan")` via
  `asyncio.to_thread`, per directory, sequentially — few directories, ordered
  output, and `exclusive` means a recompose-driven rescan cancels the one in
  flight rather than racing it. Rows are `ModelRow`s labeled with the model's
  path *relative to* its configured directory, so a model in a subfolder keeps
  that context; they are the screen's only focus stops, which is why the
  `VerticalScroll` wrapper passes `can_focus=False` (`ScrollableContainer` opts
  in by default and would otherwise be a stop the user arrows past). Group
  shells are keyed by **position** (`#models-state-{i}`, `#models-files-{i}`),
  not by path — a path is not a usable widget id. `enter` on a row is a
  deliberately inert seam: `on_model_row_selected` confirms the choice and says
  validation is not wired up yet, because there is no spec to validate against
  and no live Blender connection to validate through.
- `blender_detail.py`, `godot_detail.py` — the other two detail screens
  (`blender-detail`, `godot-detail` in `SCREENS`). Still **placeholders**: they
  render the configured value they own plus a `#placeholder-note`. They exist so
  navigation is uniform and no `enter` is a dead key; `models.py` is the pattern
  each should follow when it grows real content.
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
- **Keep slow/blocking work out of the event loop and out of the screen.** No
  screen owns a `subprocess`, a filesystem *walk*, or TOML: they call the
  `blender` (`detect.probe_version`), `godot` (`discovery.find_projects`), and
  `models` (`discovery.find_blend_files`) categories inside Textual `@work`
  workers (via `asyncio.to_thread`) so the UI never freezes; the app, not the
  screen, persists results. Cheap inline stats (`is_dir`, `mkdir`) and the fast
  `candidate_paths()` prefill are fine.
- **A worker that writes to widgets must tolerate them being gone.** A
  recompose or a `pop_screen` can land while the scan is in flight, so every
  post-scan `query_one` is guarded against `NoMatches` (see `dashboard.py`'s
  `_scan_godot` and `models.py`'s `_update`). Pair that with
  `@work(exclusive=True, group=…)` so a rescan cancels its predecessor rather
  than racing it.
- **A detail screen reads app-level state, it does not take constructor args.**
  That is what keeps every screen pushable by name from `SCREENS`, and why each
  must tolerate `self.app.settings is None` by rendering a `#setup-prompt`
  rather than raising — `--setup` cancellation ordering can reach them that way.
- **Bind one key per `Binding`, not comma-joined keys, whenever the footer
  matters.** Textual expands `Binding("down,j", …)` into a separate binding per
  key, each carrying the same `description` and `key_display` — so a shown pair
  draws its footer entry twice. Bind the aliases separately with `show=False`
  and let one entry speak for the action.
- A screen that must not honor the app's global `q`-quit binding shadows it with
  its own `q` binding (a hidden no-op action). A focused `Input` already swallows
  a typed `q` as text, but a focused `Button` would let `q` bubble to the app —
  the screen-level binding closes that gap regardless of what holds focus.
