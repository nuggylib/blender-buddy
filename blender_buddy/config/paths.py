"""Resolve where the config file lives.

``$BLENDER_BUDDY_CONFIG`` (a full file path) overrides the per-user location.
This is the seam tests use so they never touch the developer's real
``platformdirs`` config directory.
"""

import os
from pathlib import Path

from platformdirs import user_config_path

APP_NAME = "blender-buddy"
APP_AUTHOR = "mcnuggies"


def config_file() -> Path:
    """Return the config file path.

    Honors ``$BLENDER_BUDDY_CONFIG`` if set; otherwise falls back to the
    platform's per-user config directory (macOS ``~/Library/Application
    Support/…``, Linux ``~/.config/…``, Windows ``%LOCALAPPDATA%\\…``).
    """
    override = os.environ.get("BLENDER_BUDDY_CONFIG")
    if override:
        return Path(override).expanduser()
    return user_config_path(APP_NAME, APP_AUTHOR) / "config.toml"
