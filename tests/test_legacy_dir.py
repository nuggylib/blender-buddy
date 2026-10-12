"""Unit tests for the one-time blender-buddy → model-meta config dir move."""

from pathlib import Path

import pytest

from model_meta.config import legacy_dir


@pytest.fixture(autouse=True)
def _no_override(monkeypatch):
    monkeypatch.delenv("MODEL_META_CONFIG", raising=False)


def _seed_legacy(root: Path) -> Path:
    legacy = root / "blender-buddy"
    (legacy / "specs").mkdir(parents=True)
    (legacy / "config.toml").write_text("schema_version = 2\n")
    (legacy / "specs" / "car.json").write_text("{}")
    return legacy


def test_moves_legacy_dir_when_current_absent(tmp_path):
    legacy = _seed_legacy(tmp_path)
    current = tmp_path / "model-meta"

    legacy_dir.migrate(legacy, current)

    assert not legacy.exists()
    assert (current / "config.toml").read_text() == "schema_version = 2\n"
    assert (current / "specs" / "car.json").read_text() == "{}"


def test_leaves_both_alone_when_current_exists(tmp_path):
    legacy = _seed_legacy(tmp_path)
    current = tmp_path / "model-meta"
    current.mkdir()

    legacy_dir.migrate(legacy, current)

    assert (legacy / "config.toml").exists()
    assert list(current.iterdir()) == []


def test_noop_when_legacy_absent(tmp_path):
    current = tmp_path / "model-meta"

    legacy_dir.migrate(tmp_path / "blender-buddy", current)

    assert not current.exists()


def test_skipped_when_config_override_set(tmp_path, monkeypatch):
    monkeypatch.setenv("MODEL_META_CONFIG", str(tmp_path / "x" / "config.toml"))
    legacy = _seed_legacy(tmp_path)
    current = tmp_path / "model-meta"

    legacy_dir.migrate(legacy, current)

    assert legacy.exists()
    assert not current.exists()


def test_rename_failure_does_not_raise(tmp_path, monkeypatch):
    legacy = _seed_legacy(tmp_path)

    def _boom(self, target):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "rename", _boom)

    legacy_dir.migrate(legacy, tmp_path / "model-meta")

    assert legacy.exists()
