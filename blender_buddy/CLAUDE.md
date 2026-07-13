# blender_buddy/

The Blender Buddy application package. Everything under this directory _is_
Blender Buddy and is packaged together into the published binary (flat layout —
this package sits at the repository root, not under `src/`).

## Files
- `app.py` — `BlenderBuddyApp` (the Textual `App`) and the `main()` entry point
  used by both the `blender-buddy` console script and `python -m blender_buddy`.
  `main(argv=None)` takes injectable args (unit-testable without `subprocess`)
  and exposes `--version`, `--check`, and `--setup` (re-run the setup wizard);
  bare invocation still launches the TUI.
  `_resource_path()` resolves bundled data files (e.g. `app.tcss`) both frozen
  (`sys._MEIPASS`) and from source — `CSS_PATH` uses it so the packaged binary
  finds its stylesheet.
  `BlenderBuddyApp(config_path=..., force_setup=...)`: `on_mount` routes off the
  config file — **valid** → dashboard, **absent** → first-time setup wizard
  (`_first_run`, saved only on completion), **corrupt** → dashboard + a
  non-blocking recovery notice (never auto-overwritten). The dashboard's `s`
  key and `force_setup` both re-open the wizard via `_open_setup` (edit mode
  when a valid config exists; a cancel keeps the prior config). `config_path` is
  the test/injection seam; both wizard flows run `push_screen_wait` inside a
  `@work` worker.
- `__main__.py` — enables `python -m blender_buddy`.
- `app.tcss` — application-level Textual stylesheet (loaded via `App.CSS_PATH`).
- `__init__.py` — package marker; holds `__version__`, imported from an optional
  CI-generated `_version.py` with a static `pyproject`-synced fallback.

## Build-time version (`_version.py`)
`__init__.py` imports `__version__` from `blender_buddy._version` if present,
else falls back to a literal kept in sync with `pyproject.toml` by
`tests/test_version.py`. `_version.py` is **gitignored** — CI writes the fully
resolved canary/dev string there before freezing a binary; it never exists in a
normal checkout. Do not commit or hand-edit it.

## Subpackages (categories)
- `tui/` — Textual screens and widgets.
- `config/` — persistence: the on-disk config first-time setup writes and every
  launch reads (`Settings`, path resolution, atomic load/save). No Textual, no I/O
  beyond the config file.
- `diagnostics/` — build/launch self-tests (`run_headless_check`, the `--check`
  smoke gate). Release-pipeline concerns kept out of `app.py`.
- `blender/` — Blender-executable detection and `--version` validation
  (`detect.py`); the live-scene connection/IPC client is still a stub.
- `godot/` — Godot project discovery: a bounded scan for `project.godot` under a
  chosen root. No Textual, no UI.

## Conventions
- Group new code by category into subpackages here rather than adding loose
  top-level modules. Create a new category subpackage when none fits, and give
  it its own `CLAUDE.md`.
