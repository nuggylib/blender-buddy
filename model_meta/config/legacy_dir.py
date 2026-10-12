"""One-time move of the pre-rename ``blender-buddy`` config dir to ``model-meta``.

Runs at boot from ``app.main()`` — never from ``store.load``, which keeps its
single sanctioned write. Best-effort: any failure falls back to first-run setup.
"""

import os
from pathlib import Path

from platformdirs import user_config_path

from model_meta.config import paths

LEGACY_APP_NAME = "blender-buddy"


def migrate(legacy: Path | None = None, current: Path | None = None) -> None:
    """Rename the legacy config dir to the current one if only the legacy exists.

    Skipped when ``$MODEL_META_CONFIG`` is set. Never merges or overwrites: an
    existing current dir wins and the legacy dir is left alone.
    """
    if os.environ.get("MODEL_META_CONFIG"):
        return
    legacy = legacy or user_config_path(LEGACY_APP_NAME, paths.APP_AUTHOR)
    current = current or user_config_path(paths.APP_NAME, paths.APP_AUTHOR)
    if current.exists() or not legacy.is_dir():
        return
    try:
        # Same parent on every OS, so this is a single atomic move.
        legacy.rename(current)
    except OSError:
        pass
