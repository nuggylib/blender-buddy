"""Load and save the config file.

``load`` never raises into the caller: it maps every failure to a state so boot
routing can decide (run wizard / boot dashboard / show recovery notice). ``save``
writes once, atomically, so a crash mid-write can never leave a half-written file
that later reads as "setup is done".
"""

import os
import tomllib
from pathlib import Path

import tomli_w

from blender_buddy.config.settings import SCHEMA_VERSION, Settings

# load() outcomes.
ABSENT = "absent"
VALID = "valid"
CORRUPT = "corrupt"

# Required (table, key) pairs a valid config must contain.
REQUIRED = (
    ("blender", "executable"),
    ("models", "directory"),
    ("godot", "projects_root"),
)


def load(path: Path) -> tuple[str, Settings | None]:
    """Read the config, returning ``(state, settings)``.

    - ``(ABSENT, None)``  — no file yet; run first-time setup.
    - ``(VALID, Settings)`` — parses, known ``schema_version``, all keys present.
    - ``(CORRUPT, None)`` — unreadable, wrong/unknown version, or missing keys;
      the caller shows a recovery notice and never auto-overwrites.
    """
    try:
        with path.open("rb") as f:  # binary mode required by tomllib
            raw = tomllib.load(f)
    except FileNotFoundError:
        return ABSENT, None
    except (tomllib.TOMLDecodeError, OSError):
        return CORRUPT, None

    if raw.get("schema_version") != SCHEMA_VERSION:
        return CORRUPT, None
    if any(
        not isinstance(raw.get(table), dict) or key not in raw[table]
        for table, key in REQUIRED
    ):
        return CORRUPT, None

    return VALID, Settings(
        blender_executable=raw["blender"]["executable"],
        blender_version=raw["blender"].get("version", ""),
        models_directory=raw["models"]["directory"],
        godot_projects_root=raw["godot"]["projects_root"],
    )


def save(path: Path, settings: Settings) -> None:
    """Write the config once, atomically.

    Creates the parent directory, writes to a temp file in the same directory,
    then ``os.replace`` (atomic on POSIX and Windows). On failure nothing is
    replaced, so no partial config is left behind.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:  # binary mode required by tomli_w
        tomli_w.dump(settings.to_toml_dict(), f)
    os.replace(tmp, path)
