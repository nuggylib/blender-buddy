"""Read and write the spec files in a specs directory.

`create` is the only thing here that touches the filesystem for writing, and it
refuses to overwrite. `list_specs` and `count` are read-only and never create
the directory — a fresh install has no empty `specs/` folder sitting in its
config directory until the user makes a spec.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from blender_buddy.specs import naming, schema

SPEC_GLOB = f"*{naming.SUFFIX}"


class SpecState(Enum):
    """What reading one spec file concluded."""

    OK = auto()
    UNREADABLE = auto()  # unparseable JSON, not an object, or an OSError
    MISMATCHED = auto()  # `model_type` disagrees with the filename stem


@dataclass(frozen=True)
class SpecEntry:
    """One spec on disk. `model_type` is the filename stem — the identity."""

    path: Path
    model_type: str
    state: SpecState


def create(specs_dir: Path, model_type: str) -> Path:
    """Write a new skeleton spec. Raises `FileExistsError` / `OSError`."""
    specs_dir.mkdir(parents=True, exist_ok=True)
    path = specs_dir / f"{model_type}{naming.SUFFIX}"
    # "x" is O_EXCL: the collision check and the create are one atomic step, so
    # two creates racing can never clobber. Deliberately *not* the temp-file +
    # os.replace dance `config/store.py` uses — a replace would overwrite the
    # existing file, defeating exactly the guarantee we want here. A crash
    # mid-write can only leave a malformed *new* file, which `list_specs`
    # already reports as UNREADABLE.
    with path.open("x", encoding="utf-8") as f:
        json.dump(schema.skeleton(model_type), f, indent=2)
        f.write("\n")
    return path


def list_specs(specs_dir: Path) -> list[SpecEntry]:
    """Every spec in `specs_dir`, sorted by name. A missing dir is `[]`.

    Read-only: the directory is never created. Failures are caught **per file**
    so one malformed spec can never blank the list.
    """
    return [_read(path) for path in _spec_paths(specs_dir)]


def count(specs_dir: Path) -> int:
    """How many spec files there are, without parsing any of them.

    A single-directory glob — cheap enough for a dashboard card to call inline.
    """
    return len(_spec_paths(specs_dir))


# --- internals -------------------------------------------------------------


def _spec_paths(specs_dir: Path) -> list[Path]:
    """The spec files in `specs_dir`, sorted by stem. A missing dir is `[]`."""
    try:
        paths = [path for path in specs_dir.glob(SPEC_GLOB) if path.is_file()]
    except OSError:
        return []
    return sorted(paths, key=lambda path: path.stem)


def _read(path: Path) -> SpecEntry:
    """Classify one spec file. The stem is the identity either way."""
    model_type = path.stem
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return SpecEntry(path, model_type, SpecState.UNREADABLE)
    if not isinstance(raw, dict):
        # Valid JSON, wrong type — an array or a bare string is not a spec.
        return SpecEntry(path, model_type, SpecState.UNREADABLE)
    if raw.get("model_type") != model_type:
        return SpecEntry(path, model_type, SpecState.MISMATCHED)
    return SpecEntry(path, model_type, SpecState.OK)
