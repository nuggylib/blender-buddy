# blender_buddy/config/

The app's persistence layer — the on-disk config that first-time setup writes and
every later launch reads. This is the first persistence category in the project.

## Files
- `settings.py` — the `Settings` frozen dataclass (the three captured anchors plus
  the recorded Blender version) and `SCHEMA_VERSION`, the migration anchor written
  on every save.
- `paths.py` — `config_file()` resolves where the config lives: `$BLENDER_BUDDY_CONFIG`
  wins (the test/injection seam), else the `platformdirs` per-user config dir.
- `store.py` — `load(path)` returns `(ABSENT | VALID | CORRUPT, Settings | None)` and
  never raises into the caller; `save(path, settings)` writes once, atomically
  (temp file + `os.replace`).

## Conventions
- **No Textual, no subprocess, no filesystem walking here.** This category produces
  and persists plain data; UI and I/O live in their own categories (`tui/`,
  `blender/`, `godot/`). The wizard screen calls into this package, not vice versa.
- **Never auto-overwrite a CORRUPT config** — surface it and let the user choose to
  re-run setup (which overwrites deliberately).
- **Write-once-atomic only.** Never write the config incrementally; a half-written
  file that parses would read as "setup done" and boot the app broken.
- Stored paths are already-normalized absolute strings; normalization happens at
  capture time, not in this package.
