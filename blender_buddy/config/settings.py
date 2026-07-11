"""The persisted settings shape and its schema version.

``SCHEMA_VERSION`` is written from the first save; bumping it is the anchor a
future migration keys off of. All paths are stored as already-normalized
absolute strings (normalization happens at capture time, not here).
"""

from dataclasses import dataclass

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Settings:
    """The three anchors first-time setup captures, plus recorded Blender version."""

    blender_executable: str
    blender_version: str
    models_directory: str
    godot_projects_root: str

    def to_toml_dict(self) -> dict:
        """Serialize to the nested mapping ``tomli_w`` writes to disk."""
        return {
            "schema_version": SCHEMA_VERSION,
            "blender": {
                "executable": self.blender_executable,
                "version": self.blender_version,
            },
            "models": {"directory": self.models_directory},
            "godot": {"projects_root": self.godot_projects_root},
        }
