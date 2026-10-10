# blender_buddy/tui/screens/

Full-page Textual `Screen` subclasses. Each screen is one landing view or page
in the app (analogous to a route in a web app).

## Contents
- `dashboard.py` — `DashboardScreen`, the landing view **and navigation hub**.
  Renders four stacked sections — **Blender → Specs → Models → Godot**. The
  three configured anchors each carry a live existence/validity marker; **Specs
  is config-free** — it reads no settings and renders a muted `#specs-value`
  line with no `✓`/`✗`, because its location is a path convention
  (`app.specs_dir`) rather than a configured anchor, so there is nothing to
  validate. That line is a live count (`No specs yet` / `N specs`) from
  `specs.store.count` — a single-directory glob with no parsing, so it runs
  inline in `compose` like the other cards' `is_dir()`. It is **also refreshed
  on `on_screen_resume`**, targeted at `#specs-value` alone: a spec created on
  the Specs page lands while the dashboard is suspended, a pop does not
  recompose, and a full `recompose` would re-trigger the Godot scan on every
  `escape`. The Models section renders **one row per configured directory**, in
  stored order, each with its own independent marker (the schema and the wizard
  both enforce at least one, so there is no empty state). It reads
  `self.app.settings` (app-level state) and never touches TOML or the filesystem
  beyond cheap stats: Blender validity via `detect.executable_state` (three
  states — valid / present-but-not-executable / missing — platform-aware, no
  subprocess), Models/Godot-root existence via `is_dir` inline. The one
  filesystem *walk* — the Godot project count — runs in a `@work` worker
  (`asyncio.to_thread(discovery.find_projects, …)`) showing "Scanning…" until it
  returns (zero projects is a valid `0`). It `watch`es the app's `settings`
  reactive and `recompose`s on change, so editing config via `s` refreshes the
  view without a restart. When `self.app.settings is None` (absent/corrupt
  config) it shows a "run setup" prompt in place of the three config-derived
  sections — prompt first, with the Specs card below it. Its `s` binding
  (`app.open_setup`) re-opens the setup wizard in edit mode.
  **Navigation:** each section is a focusable `SectionCard` (see
  `../widgets/CLAUDE.md`); `down`/`j` → `app.focus_next` and `up`/`k` →
  `app.focus_previous` step through them (wrapping at both ends), and `enter` on
  a card posts `SectionCard.Opened`, which `on_section_card_opened` turns into a
  `push_screen(target)`. The cards are the screen's **only** focus stops — a
  test asserts the chain is exactly the four sections, because anything else
  focusable here is a widget the user has to arrow past. `_focus_section()`
  focuses the first section on mount and, critically, **re-focuses the same
  section after `recompose()`**: a config edit tears down every widget, so
  without the save-and-restore the user's highlight silently jumps to the top
  after saving. With no valid config Specs is the only card, so the navigation
  keys act on it alone and the footer still advertises `enter Open`. Future
  work adds live validation results from a Blender-polling worker.
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
- `specs.py` — `SpecsScreen` (`specs` in `SCREENS`), the Specs page: the
  validation specs in `specs/`, one focusable `SpecRow` each. Follows
  `models.py`'s page shape — a `VerticalScroll` of rows (`can_focus=False`, so
  the rows are the only focus stops) plus a `FixPanel` **outside** the scroller.
  The listing parses JSON per file, so it runs in
  `@work(exclusive=True, group="specs-load")` via `asyncio.to_thread`, and every
  post-load `query_one` is `NoMatches`-guarded. Two problem states contribute a
  fix step — `UNREADABLE` (not valid JSON) and `MISMATCHED` (the file's
  `model_type` disagrees with its filename; the filename wins). **Zero specs is
  not a problem**: on a fresh install it is the normal state, so it renders a
  plain `#specs-empty` note and contributes no step — the opposite call from the
  Models screen's empty directory. `enter` on a row opens `spec_detail.py` for
  that spec, pushed as an **instance** (the screen is per spec), so no `enter`
  on this page is a dead key.
  **`n` creates:** `action_new_spec` runs a `@work(exclusive=True,
  group="new-spec")` worker that `push_screen_wait`s a `NewSpecModal` and, on a
  non-`None` return, notifies, `recompose`s, reloads, and hands focus to the
  **new** row rather than row one (`_focus_after_load`). `exclusive` is what
  stops a fast double `n` stacking two modals.
  It is the one detail screen with **no `#setup-prompt` branch** (see
  Conventions), and the reason is now stronger rather than weaker: it reads
  `self.app.specs_dir`, a path derived from the config *path* rather than its
  contents, so the page lists and works identically in every config state.
- `spec_detail.py` — `SpecDetailScreen`, the per-spec detail view opened by
  `enter` on a `SpecRow`. A **stub**, like `blender_detail.py`: a `#spec-title`
  naming the spec and a `#placeholder-note`, reusing their ids and classes so it
  needs no CSS of its own. It takes the spec's `model_type` — the filename stem,
  the spec's identity — as a **constructor argument** and is **not** in
  `SCREENS` (see Conventions). The stem is the identity, so there is nothing to
  read from the file to title the page, which is why the screen touches no
  filesystem at all; it reads no settings either, so it has no `#setup-prompt`
  branch. It takes the name alone, not the `Path` — with no filename line and no
  file read, a path would be an argument nothing uses, and `SpecRow.Selected`
  carries both when something needs it. Nothing on the page is focusable.
- `blender_detail.py`, `godot_detail.py` — the other two detail screens
  (`blender-detail`, `godot-detail` in `SCREENS`). Still **placeholders**: they
  render the configured value they own plus a `#placeholder-note`. They exist so
  navigation is uniform and no `enter` is a dead key; `models.py` is the pattern
  each should follow when it grows real content.
- `new_spec_modal.py` — `NewSpecModal(ModalScreen[Path | None])`, the one
  question a new spec needs: a model-type name. Returns the created file's path
  via `dismiss()`, or `None` on cancel. The codebase's **first `ModalScreen`**
  (the wizard is a plain `Screen[…]`), so it owns its overlay layout in
  `DEFAULT_CSS` — `align: center middle` plus a bordered panel — the way the
  wizard does.
  It takes **no constructor arguments**: it reads `self.app.specs_dir`, which is
  the whole point — a second entry point to the create flow is one
  `push_screen_wait` inside a worker, not a reimplementation.
  Key contract: **Enter in the Input creates** — the opposite call from the
  wizard's models box, where Enter Adds and never advances, because there the
  field feeds a list and here it *is* the whole form. `Input.Changed` previews
  the resulting filename (`→ specs/space-ship.json`) and clears a stale error,
  so the normalization is visible before the user commits to it. `q` is shadowed
  with a no-op for the usual reason (a focused `Button` would bubble it to the
  app's quit). Every failure — invalid name, duplicate, unwritable directory —
  keeps the modal up with a message in `#spec-status` and the Input's text
  intact, and writes nothing. The write itself is one small file done inline,
  like `app._save`: no worker needed.
  It composes its **own `Footer`**, which a `ModalScreen` needs and a plain
  pushed screen does not: a modal is transparent, so the page underneath keeps
  painting *its* bindings — the Specs page's `n New spec` and `q Quit`, neither
  of which does anything while the modal is up.
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
- One screen per file, named `<Name>Screen`. The value-returning screens are the
  deliberate exceptions — `SetupWizard` and `NewSpecModal` are flows that return
  a result, not landing views, and are named for what they are.
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
  `specs.py` is the deliberate exception: it reads no settings at all — only
  `self.app.specs_dir`, a path derived from the config *path* — so it has no
  `None` branch to write and lists and creates identically in every config
  state. The rule's *purpose* (never raise on that push) holds; its mechanism
  has nothing to do.
  `spec_detail.py` is the other named exemption, and it takes the opposite route:
  it is *per spec*, with no app-level "current spec" to read, so it takes the
  spec as a constructor argument and is **not** registered in `SCREENS` — the
  `SetupWizard` / `NewSpecModal` shape, minus the return value. Adding a
  `current_spec` to app state would be persisting a selected spec, which nothing
  asks for. The rule's purpose holds because nothing in `SCREENS` names it.
- **Screens read `self.app.specs_dir`, never `config.paths` directly** — the
  same rule that keeps them off `self.app._config_path`. It also means
  `$BLENDER_BUDDY_CONFIG` needs no sibling `$BLENDER_BUDDY_SPECS`: point the
  config somewhere and the specs follow.
- **Bind one key per `Binding`, not comma-joined keys, whenever the footer
  matters.** Textual expands `Binding("down,j", …)` into a separate binding per
  key, each carrying the same `description` and `key_display` — so a shown pair
  draws its footer entry twice. Bind the aliases separately with `show=False`
  and let one entry speak for the action.
- A screen that must not honor the app's global `q`-quit binding shadows it with
  its own `q` binding (a hidden no-op action). A focused `Input` already swallows
  a typed `q` as text, but a focused `Button` would let `q` bubble to the app —
  the screen-level binding closes that gap regardless of what holds focus.
