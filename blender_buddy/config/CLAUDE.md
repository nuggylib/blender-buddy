# blender_buddy/config/

The app's persistence layer — the on-disk config that first-time setup writes and
every later launch reads. This is the first persistence category in the project.

## Files
- `settings.py` — the `Settings` frozen dataclass (the captured anchors plus the
  recorded Blender version) and `SCHEMA_VERSION`, the migration anchor written on
  every save. `models_directories` is a **tuple** (not a list): the dataclass is
  frozen, and a mutable field would undercut that. `to_toml_dict` converts it to
  a list so `tomli_w` writes a TOML array.
- `paths.py` — `config_file()` resolves where the config lives: `$BLENDER_BUDDY_CONFIG`
  wins (the test/injection seam), else the `platformdirs` per-user config dir.
- `store.py` — `load(path)` returns `(ABSENT | VALID | CORRUPT, Settings | None)` and
  never raises into the caller; `save(path, settings)` writes once, atomically
  (temp file + `os.replace`).

## Schema versions
- **v1** — `[models] directory`: exactly one source-models path.
- **v2** (current) — `[models] directories`: a non-empty array of them. A missing,
  empty, non-list, or non-string-entry `directories` is `CORRUPT` — a config with
  zero model directories is meaningless, so it is not quietly tolerated.

`load` accepts both. A **v1** file is upgraded in memory (its single directory
wrapped in a one-item tuple) and re-saved as v2, so existing users gain
multi-directory support with no re-setup. v1 is matched *before* the
unknown-version gate, which would otherwise reject every pre-v2 config; and a v1
file is itself validated first — a missing or non-string `[models] directory` is
`CORRUPT`, never a garbage one-entry migration. Any other version (0, 3, `"1"`, …)
stays `CORRUPT`.

### The sanctioned exception to load-is-read-only
`load` performs **exactly one** bounded, atomic write — the v1→v2 migration — and
no other mutation. It is best-effort: an `OSError` during that write is swallowed
and the upgraded `Settings` are still returned (unpersisted), because `load` must
never raise into the caller and an unwritable config is no reason to refuse to
boot. The write retries next launch, which is safe because the in-memory upgrade
is idempotent. Overwriting a *valid* v1 file this way is the intended upgrade, not
the corrupt-clobber the "never auto-overwrite" rule guards against, so it takes no
backup. Do not add further writes to `load`.

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
