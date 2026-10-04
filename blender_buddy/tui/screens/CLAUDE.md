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
- `models.py`, `blender_detail.py`, `godot_detail.py` — the per-section detail
  screens the dashboard's cards open (`models`, `blender-detail`,
  `godot-detail` in `SCREENS`). All three are **placeholders for now**: they
  render the configured value(s) they own plus a `#placeholder-note`, and bind
  `escape` → `app.pop_screen` and `s` → `app.open_setup`. They exist so
  navigation is uniform immediately and no `enter` is a dead key. `models.py`
  is the next one to grow real content — grouped `.blend` listings per
  configured directory, with a four-state per-directory rendering (missing /
  unreadable / empty / populated) and fix-it steps at the bottom. It is
  deliberately thin until the scan that can tell those states apart exists,
  rather than being written twice.
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
