"""Unit tests for source-model discovery (blender_buddy.models.discovery).

Headless and pure — a temp directory tree exercises the backup-file exclusion,
nesting, the depth cap, symlink handling, permission tolerance, the
root-vs-descendant error split, and the zero-results case.
"""

import os

import pytest

from blender_buddy.models.discovery import find_blend_files


def _blend(path):
    """Create `path` as a (fake) .blend file, parents included."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"BLENDER-v450")
    return path.resolve()


def test_finds_blend_files_sorted(tmp_path):
    truck = _blend(tmp_path / "truck.blend")
    sedan = _blend(tmp_path / "sedan.blend")
    assert find_blend_files(tmp_path) == sorted([sedan, truck])


def test_finds_nested_blend_file(tmp_path):
    nested = _blend(tmp_path / "vehicles" / "civilian" / "sedan.blend")
    assert find_blend_files(tmp_path) == [nested]


def test_zero_results_is_empty_not_error(tmp_path):
    (tmp_path / "just" / "some" / "dirs").mkdir(parents=True)
    assert find_blend_files(tmp_path) == []


def test_excludes_blender_save_backups(tmp_path):
    """`.blend1`/`.blend2` sit next to the file they back up — counting them
    would report every model two or three times."""
    sedan = _blend(tmp_path / "sedan.blend")
    _blend(tmp_path / "sedan.blend1")
    _blend(tmp_path / "sedan.blend2")
    _blend(tmp_path / "sedan.blend30")
    assert find_blend_files(tmp_path) == [sedan]


def test_suffix_match_is_case_insensitive(tmp_path):
    shouty = _blend(tmp_path / "SEDAN.BLEND")
    assert find_blend_files(tmp_path) == [shouty]


def test_ignores_non_blend_files(tmp_path):
    sedan = _blend(tmp_path / "sedan.blend")
    _blend(tmp_path / "notes.txt")
    _blend(tmp_path / "sedan.fbx")
    _blend(tmp_path / "blend")  # no suffix at all
    assert find_blend_files(tmp_path) == [sedan]


def test_directory_named_like_a_model_is_not_a_result(tmp_path):
    """A directory called `foo.blend` is a directory, not a model."""
    (tmp_path / "bundle.blend").mkdir()
    inner = _blend(tmp_path / "bundle.blend" / "sedan.blend")
    assert find_blend_files(tmp_path) == [inner]


def test_respects_max_depth(tmp_path):
    # root(0)/a(1)/b(2)/c(3)/sedan.blend — the file sits in c, at depth 3.
    deep = _blend(tmp_path / "a" / "b" / "c" / "sedan.blend")
    assert find_blend_files(tmp_path, max_depth=2) == []
    assert find_blend_files(tmp_path, max_depth=3) == [deep]


def test_symlinked_file_is_kept(tmp_path):
    """Linking one model into several directories is a legitimate way to share
    it, and a linked *file* cannot make the walk loop."""
    real = _blend(tmp_path / "library" / "sedan.blend")
    vehicles = tmp_path / "vehicles"
    vehicles.mkdir()
    (vehicles / "sedan.blend").symlink_to(real)

    # Asserted on the link's own identity rather than an equal path: the scan
    # resolves the root it was handed, so a /var -> /private/var style tmp dir
    # would make a literal path comparison fail for the wrong reason.
    (found,) = find_blend_files(vehicles)
    assert found.name == "sedan.blend"
    assert found.is_symlink()


def test_broken_symlink_is_skipped(tmp_path):
    (tmp_path / "gone.blend").symlink_to(tmp_path / "never-existed.blend")
    assert find_blend_files(tmp_path) == []


def test_symlink_loop_is_guarded(tmp_path):
    sedan = _blend(tmp_path / "real" / "sedan.blend")
    loop = tmp_path / "loop"
    loop.symlink_to(tmp_path, target_is_directory=True)  # points back at root
    # Terminates (no infinite loop) and never descends the symlink.
    assert find_blend_files(tmp_path) == [sedan]


def test_symlinked_directory_is_not_descended(tmp_path):
    _blend(tmp_path / "external" / "sedan.blend")
    root = tmp_path / "root"
    root.mkdir()
    (root / "linked").symlink_to(tmp_path / "external", target_is_directory=True)
    # The model is only reachable through a symlinked directory, so it is skipped.
    assert find_blend_files(root) == []


def test_missing_root_raises(tmp_path):
    """A missing directory is the caller's to check cheaply with `is_dir()`; if
    it does scan one, it gets an error rather than a silent empty list."""
    with pytest.raises(OSError):
        find_blend_files(tmp_path / "never-created")


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root can read even a 0o000 directory",
)
def test_unreadable_root_raises(tmp_path):
    """ "I could not read this" must not be reported as "there is nothing here" —
    they are different problems with different fixes."""
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o000)  # not listable — iterdir() itself raises
    try:
        with pytest.raises(OSError):
            find_blend_files(locked)
    finally:
        locked.chmod(0o755)  # let pytest clean up the tmp tree


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root can read even a 0o000 directory",
)
def test_permission_denied_subdir_is_skipped(tmp_path):
    """Unlike the root, a descendant we cannot read is skipped, not fatal."""
    sedan = _blend(tmp_path / "reachable" / "sedan.blend")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        result = find_blend_files(tmp_path)
    finally:
        locked.chmod(0o755)  # let pytest clean up the tmp tree
    assert result == [sedan]


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores the missing search bit on a 0o444 directory",
)
def test_readable_but_not_searchable_subdir_is_skipped(tmp_path):
    # 0o444: listable (iterdir succeeds) but not searchable, so stat()-ing any
    # child raises PermissionError. The scan must skip it, not crash.
    sedan = _blend(tmp_path / "reachable" / "sedan.blend")
    unsearchable = tmp_path / "unsearchable"
    _blend(unsearchable / "hidden.blend")
    unsearchable.chmod(0o444)
    try:
        result = find_blend_files(tmp_path)
    finally:
        unsearchable.chmod(0o755)  # let pytest clean up the tmp tree
    assert result == [sedan]
