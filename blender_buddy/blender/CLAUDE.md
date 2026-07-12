# blender_buddy/blender/

Everything Blender-executable: **detecting and validating** the Blender binary
(implemented) and, in the future, **connecting** to a live Blender scene (still a
stub). Detection is what first-time setup needs; the connection bridge is a
later plan.

## Files
- `detect.py` — `candidate_paths()` scans standard per-platform install
  locations (macOS `Blender.app` → inner binary, Windows `Blender Foundation\*`
  glob, Linux prefixes + PATH). `probe_version(exe, timeout)` runs
  `<exe> --version` in a subprocess and returns a structured `ProbeResult`
  (`ProbeOutcome`: OK / NOT_FOUND / NOT_EXE / TIMEOUT / UNPARSEABLE, plus the
  parsed version and a human message).

## Intended responsibility (future — connection, not yet built)
- Connect to the active Blender scene and stream scene data (meshes, armatures,
  bones, vertex groups) for validation.
- Be polled by a Textual background worker so the dashboard can live-update as
  the user edits their model in Blender.

## Conventions
- **No Textual imports here.** This category is pure detection/validation and
  future protocol code; the rest of the app depends on the plain data structures
  it returns (`ProbeResult`), not on Blender itself.
- `probe_version()` blocks on a subprocess — always call it from a Textual
  worker with its timeout, never on the event loop. Every failure mode is a
  `ProbeResult`, never a raised exception and never a hang.
- flatpak/snap Blender wrappers are out of scope: they aren't plain executable
  paths, so `candidate_paths()` doesn't return them and they can't be probed.
