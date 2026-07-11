# blender_buddy/blender/

Connection and IPC with a live Blender scene. **Stub only** — no implementation
yet.

## Intended responsibility (future)
- Connect to the active Blender scene and stream scene data (meshes, armatures,
  bones, vertex groups) for validation.
- Be polled by a Textual background worker so the dashboard can live-update as
  the user edits their model in Blender.

## Conventions
- Keep all Blender-specific I/O and protocol code here; the rest of the app
  should depend on plain data structures this package produces, not on Blender
  itself.
