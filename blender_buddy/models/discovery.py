"""Bounded, permission-tolerant scan for `.blend` files under a directory.

Pure filesystem logic — **no Textual, no UI**. Call `find_blend_files()` from a
Textual worker: on a large tree it can take a while, though the depth cap and
per-directory error tolerance keep it from running away or crashing.
"""

from pathlib import Path

BLEND_SUFFIX = ".blend"

# How many folders below the configured directory the scan reaches. Exported so
# the UI can tell the user where it stopped looking instead of hard-coding a
# number that would drift from this one.
DEFAULT_MAX_DEPTH = 4


def find_blend_files(directory: Path, max_depth: int = DEFAULT_MAX_DEPTH) -> list[Path]:
    """List every `.blend` file under `directory`.

    Bounded (`max_depth` levels below `directory`), permission-tolerant *below
    the root* (a descendant we can't list or can't stat is skipped, not fatal),
    and symlink-loop-guarded (symlinked directories are never descended into).
    Zero results is a valid outcome, not an error. Returns absolute paths,
    sorted for deterministic display.

    **Blender's save backups are excluded.** Every save writes `foo.blend1`
    (then `foo.blend2`, …) next to `foo.blend`, so a `*.blend*` match would
    report the same model two or three times. The test is an exact suffix match,
    case-insensitive — `.BLEND` is a real model, `.blend1` is not.

    A symlink *to* a `.blend` is kept: linking one model into several
    directories is a legitimate way to share it, and unlike a linked directory
    it cannot make the walk loop. A broken symlink fails `is_file()` and drops
    out on its own.

    **The root is the one unguarded listing** — an unreadable `directory` raises
    rather than returning `[]`. Callers need to tell "I could not read this" from
    "there is nothing here", because those are different problems with different
    fixes; collapsing them would report a permissions failure as an empty
    directory. A *missing* directory is likewise the caller's to check (cheaply,
    with `is_dir()`) before scanning.
    """
    directory = directory.expanduser().resolve()
    results: list[Path] = []
    stack: list[tuple[Path, int]] = [(directory, 0)]
    while stack:
        current, depth = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError:
            if current == directory:
                raise  # the root itself — the caller must be able to say so
            continue  # unlistable descendant — skip, don't abort the whole scan
        for entry in entries:
            try:
                # `is_dir()`/`is_file()`/`is_symlink()` stat the child; a
                # readable-but-not-searchable (0o444) parent makes that raise
                # per entry.
                if entry.is_dir():
                    if depth < max_depth and not entry.is_symlink():
                        stack.append((entry, depth + 1))  # symlinks → no loops
                elif entry.is_file() and entry.suffix.lower() == BLEND_SUFFIX:
                    results.append(entry)
            except OSError:
                continue  # unstattable entry — skip it, keep its siblings
    return sorted(results)
