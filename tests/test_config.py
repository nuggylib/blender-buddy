"""Unit tests for the config persistence layer (blender_buddy.config).

These are pure I/O tests against a temp dir — no Textual, no subprocess. They
cover the three load outcomes, the write-once-atomic round-trip, lossless
Windows-path storage, and the $BLENDER_BUDDY_CONFIG override seam.
"""

import tomllib

import pytest

from blender_buddy.config import paths, store
from blender_buddy.config.settings import SCHEMA_VERSION, Settings


def _settings(tmp_path) -> Settings:
    return Settings(
        blender_executable=str(tmp_path / "blender"),
        blender_version="4.5.0",
        models_directory=str(tmp_path / "models"),
        godot_projects_root=str(tmp_path / "godot"),
    )


# --- load() outcomes -------------------------------------------------------


def test_load_absent_when_file_missing(tmp_path):
    state, settings = store.load(tmp_path / "nope.toml")
    assert state == store.ABSENT
    assert settings is None


def test_load_valid_round_trips_settings(tmp_path):
    cfg = tmp_path / "config.toml"
    original = _settings(tmp_path)
    store.save(cfg, original)

    state, settings = store.load(cfg)
    assert state == store.VALID
    assert settings == original


def test_load_corrupt_on_garbage_toml(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text("this is not : valid = toml ===")
    state, settings = store.load(cfg)
    assert state == store.CORRUPT
    assert settings is None


def test_load_corrupt_on_missing_required_key(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f"schema_version = {SCHEMA_VERSION}\n"
        '[blender]\nexecutable = "/x"\n'
        '[models]\ndirectory = "/y"\n'
        # godot table omitted → missing required key
    )
    state, _ = store.load(cfg)
    assert state == store.CORRUPT


def test_load_corrupt_when_table_is_not_a_table(tmp_path):
    cfg = tmp_path / "config.toml"
    cfg.write_text(f'schema_version = {SCHEMA_VERSION}\nblender = "oops"\n')
    state, _ = store.load(cfg)
    assert state == store.CORRUPT


@pytest.mark.parametrize("version", [0, 2, 99, "1"])
def test_load_corrupt_on_unknown_schema_version(tmp_path, version):
    cfg = tmp_path / "config.toml"
    store.save(cfg, _settings(tmp_path))
    raw = cfg.read_text().replace(
        f"schema_version = {SCHEMA_VERSION}", f"schema_version = {version!r}"
    )
    cfg.write_text(raw)
    state, _ = store.load(cfg)
    assert state == store.CORRUPT


# --- save() atomicity & format --------------------------------------------


def test_save_creates_parent_dirs_and_writes_schema_version(tmp_path):
    cfg = tmp_path / "nested" / "deeper" / "config.toml"
    store.save(cfg, _settings(tmp_path))

    assert cfg.exists()
    with cfg.open("rb") as f:
        raw = tomllib.load(f)
    assert raw["schema_version"] == SCHEMA_VERSION


def test_save_leaves_no_temp_file_behind(tmp_path):
    cfg = tmp_path / "config.toml"
    store.save(cfg, _settings(tmp_path))
    assert list(tmp_path.glob("*.tmp")) == []


def test_save_overwrites_existing_config(tmp_path):
    cfg = tmp_path / "config.toml"
    store.save(cfg, _settings(tmp_path))
    updated = Settings("/new/blender", "5.0.0", "/new/models", "/new/godot")
    store.save(cfg, updated)

    state, settings = store.load(cfg)
    assert state == store.VALID
    assert settings == updated


def test_windows_path_round_trips_losslessly(tmp_path):
    """Backslash paths must survive save→load unchanged (serialization footgun)."""
    cfg = tmp_path / "config.toml"
    win = Settings(
        blender_executable=r"C:\Program Files\Blender Foundation\Blender\blender.exe",
        blender_version="4.5.0",
        models_directory=r"C:\Users\mando\BlenderModels",
        godot_projects_root=r"C:\Users\mando\GodotProjects",
    )
    store.save(cfg, win)

    state, settings = store.load(cfg)
    assert state == store.VALID
    assert settings == win
    assert settings.blender_executable == win.blender_executable


# --- config path resolution seam ------------------------------------------


def test_config_file_honors_env_override(tmp_path, monkeypatch):
    override = tmp_path / "custom" / "config.toml"
    monkeypatch.setenv("BLENDER_BUDDY_CONFIG", str(override))
    assert paths.config_file() == override


def test_config_file_expands_user_in_override(monkeypatch):
    monkeypatch.setenv("BLENDER_BUDDY_CONFIG", "~/bb.toml")
    resolved = paths.config_file()
    assert "~" not in str(resolved)
    assert resolved.name == "bb.toml"


def test_config_file_falls_back_to_platformdirs(monkeypatch):
    monkeypatch.delenv("BLENDER_BUDDY_CONFIG", raising=False)
    resolved = paths.config_file()
    assert resolved.name == "config.toml"
    assert paths.APP_NAME in str(resolved)
