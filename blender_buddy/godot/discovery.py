"""Bounded, permission-tolerant scan for Godot projects under a root.

Pure filesystem logic — **no Textual, no UI**. Call `find_projects()` from a
Textual worker: on a large tree it can take a while, though the depth cap and
per-directory error tolerance keep it from running away or crashing.
"""

from pathlib import Path

PROJECT_MARKER = "project.godot"


def find_projects(root: Path, max_depth: int = 4) -> list[Path]:
    """List every directory under `root` that contains a `project.godot`.

    Bounded (`max_depth` levels below `root`), permission-tolerant (an
    unreadable directory is skipped, not fatal), and symlink-loop-guarded
    (symlinked directories are never descended into this PR). A directory that
    is itself a Godot project is not recursed into — nested sub-projects below a
    project root are intentionally ignored. Zero results is a valid outcome, not
    an error. Returns absolute paths, sorted for deterministic display.
    """
    root = root.expanduser().resolve()
    results: list[Path] = []
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            entries = list(directory.iterdir())
        except (PermissionError, OSError):
            continue  # unreadable dir — skip, don't abort the whole scan
        if any(e.name == PROJECT_MARKER for e in entries):
            results.append(directory)
            continue  # a project root — don't descend into it
        if depth < max_depth:
            stack.extend(
                (e, depth + 1)
                for e in entries
                if e.is_dir() and not e.is_symlink()  # skip symlinks → no loops
            )
    return sorted(results)
