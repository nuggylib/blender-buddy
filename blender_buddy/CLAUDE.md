# blender_buddy/

The Blender Buddy application package. Everything under this directory _is_
Blender Buddy and is packaged together into the published binary (flat layout —
this package sits at the repository root, not under `src/`).

## Files
- `app.py` — `BlenderBuddyApp` (the Textual `App`) and the `main()` entry point
  used by both the `blender-buddy` console script and `python -m blender_buddy`.
- `__main__.py` — enables `python -m blender_buddy`.
- `app.tcss` — application-level Textual stylesheet (loaded via `App.CSS_PATH`).
- `__init__.py` — package marker; holds `__version__`.

## Subpackages (categories)
- `tui/` — Textual screens and widgets.
- `blender/` — (stub) future connection/IPC with a live Blender scene.

## Conventions
- Group new code by category into subpackages here rather than adding loose
  top-level modules. Create a new category subpackage when none fits, and give
  it its own `CLAUDE.md`.
