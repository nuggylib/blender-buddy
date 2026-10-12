# blender_buddy/godot/

Godot project discovery — locating the folders under a user-chosen root that
contain a `project.godot`. This is the read side the setup wizard uses to show
the user which projects live beneath the root they pick.

## Files
- `discovery.py` — `find_projects(root, max_depth=4)` walks the tree beneath
  `root` and returns the absolute, sorted list of directories holding a
  `project.godot`.

## Conventions
- **No Textual, no UI here.** The scan is pure filesystem logic; the wizard
  calls it from a Textual worker and renders the results itself.
- **Bounded and defensive.** The walk is depth-capped and tolerates
  `PermissionError`/`OSError` both per-directory (an unlistable dir is skipped)
  and per-entry (a readable-but-not-searchable `0o444` parent makes stat-ing a
  child raise — that child is skipped, its siblings kept). It never descends
  into symlinked directories (loop guard), and a project directory is not
  recursed into.
- **Locate only.** This PR lists projects for display; only the *root* is
  persisted. Indexing, export tracking, and `.blend`→`.glb` diffing are future
  work in this category.
- Zero results is a valid (warned) state upstream, not an error here.
