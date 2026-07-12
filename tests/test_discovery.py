"""Unit tests for Godot project discovery (blender_buddy.godot.discovery).

Headless and pure — a temp directory tree exercises nesting, the depth cap, the
don't-recurse-into-a-project rule, symlink-loop safety, permission tolerance, and
the zero-results case.
"""

import os

import pytest

from blender_buddy.godot.discovery import find_projects


def _project(dir_path):
    """Make `dir_path` a Godot project by dropping a project.godot in it."""
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "project.godot").write_text("[application]\n")
    return dir_path.resolve()


def test_finds_nested_project(tmp_path):
    proj = _project(tmp_path / "games" / "asteroids")
    assert find_projects(tmp_path) == [proj]


def test_finds_multiple_sorted(tmp_path):
    a = _project(tmp_path / "a")
    b = _project(tmp_path / "b")
    assert find_projects(tmp_path) == sorted([a, b])


def test_zero_results_is_empty_not_error(tmp_path):
    (tmp_path / "just" / "some" / "dirs").mkdir(parents=True)
    assert find_projects(tmp_path) == []


def test_does_not_recurse_into_a_project(tmp_path):
    outer = _project(tmp_path / "outer")
    _project(tmp_path / "outer" / "addons" / "inner")  # nested sub-project
    # Only the outer project root is reported; the walk stops at a project.
    assert find_projects(tmp_path) == [outer]


def test_respects_max_depth(tmp_path):
    # root(0)/a(1)/b(2)/c(3)/proj(4) — beyond a max_depth of 2.
    deep = _project(tmp_path / "a" / "b" / "c" / "proj")
    assert find_projects(tmp_path, max_depth=2) == []
    assert deep in find_projects(tmp_path, max_depth=5)


def test_symlink_loop_is_guarded(tmp_path):
    proj = _project(tmp_path / "real")
    loop = tmp_path / "loop"
    loop.symlink_to(tmp_path, target_is_directory=True)  # points back at root
    # Terminates (no infinite loop) and never descends the symlink.
    assert find_projects(tmp_path) == [proj]


def test_symlinked_project_is_not_descended(tmp_path):
    external = _project(tmp_path / "external" / "game")
    link_parent = tmp_path / "root"
    link_parent.mkdir()
    (link_parent / "linked").symlink_to(tmp_path / "external", target_is_directory=True)
    # The project is only reachable through a symlink, so it is skipped.
    assert find_projects(link_parent) == []
    # ...but discoverable via its real path.
    assert external in find_projects(tmp_path / "external")


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root can read even a 0o000 directory",
)
def test_permission_denied_subdir_is_skipped(tmp_path):
    proj = _project(tmp_path / "reachable")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        result = find_projects(tmp_path)
    finally:
        locked.chmod(0o755)  # let pytest clean up the tmp tree
    assert result == [proj]
