"""Unit tests for Blender executable detection (blender_buddy.blender.detect).

Headless and pure — no Textual. `candidate_paths` is exercised by monkeypatching
the platform and `shutil.which`; `probe_version` runs a real subprocess against a
tiny fake executable, so the shell-script cases are skipped on Windows.
"""

import os
import sys
from pathlib import Path

import pytest

from blender_buddy.blender import detect
from blender_buddy.blender.detect import ProbeOutcome

posix_only = pytest.mark.skipif(
    sys.platform == "win32", reason="fake exe is a POSIX shell script"
)
not_root = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores the exec bit, so a non-executable file still runs",
)


def _make_exe(path, body):
    path.write_text("#!/bin/sh\n" + body + "\n")
    path.chmod(0o755)
    return path


# --- candidate_paths() -----------------------------------------------------


def test_candidate_paths_appends_which_result(monkeypatch, tmp_path):
    fake = tmp_path / "blender"
    fake.write_text("")
    monkeypatch.setattr(detect.sys, "platform", "linux")
    monkeypatch.setattr(detect.shutil, "which", lambda name: str(fake))
    assert fake in detect.candidate_paths()


def test_candidate_paths_empty_when_nothing_found(monkeypatch):
    monkeypatch.setattr(detect.sys, "platform", "linux")
    monkeypatch.setattr(detect.shutil, "which", lambda name: None)
    # Standard Linux prefixes are absent in the test environment.
    assert detect.candidate_paths() == []


def test_candidate_paths_dedupes_which_against_base(monkeypatch, tmp_path):
    fake = tmp_path / "blender.exe"
    fake.write_text("")
    monkeypatch.setattr(detect.sys, "platform", "win32")
    monkeypatch.setattr(detect.Path, "glob", lambda self, pattern: [fake])
    monkeypatch.setattr(detect.shutil, "which", lambda name: str(fake))
    # `which` returns the same path the glob already found — one entry, not two.
    assert detect.candidate_paths() == [fake]


def test_candidate_paths_macos_resolves_app_binary(monkeypatch):
    monkeypatch.setattr(detect.sys, "platform", "darwin")
    monkeypatch.setattr(detect.Path, "exists", lambda self: True)
    monkeypatch.setattr(detect.shutil, "which", lambda name: None)
    # macOS resolves Blender.app to its inner Contents/MacOS/Blender binary.
    assert detect.candidate_paths() == [
        Path("/Applications/Blender.app/Contents/MacOS/Blender")
    ]


# --- probe_version() outcomes ----------------------------------------------


@posix_only
def test_probe_ok_parses_version(tmp_path):
    exe = _make_exe(tmp_path / "blender", 'echo "Blender 4.5.0"')
    result = detect.probe_version(str(exe))
    assert result.outcome is ProbeOutcome.OK
    assert result.ok
    assert result.version == "4.5.0"


@posix_only
def test_probe_accepts_path_object(tmp_path):
    # candidate_paths() hands back Path objects — probe_version takes them as-is.
    exe = _make_exe(tmp_path / "blender", 'echo "Blender 4.5.0"')
    result = detect.probe_version(exe)  # a Path, not str(exe)
    assert result.outcome is ProbeOutcome.OK
    assert result.version == "4.5.0"


@posix_only
def test_probe_ok_ignores_leading_banner(tmp_path):
    # A line before the version must not be mistaken for it.
    exe = _make_exe(tmp_path / "blender", 'echo "startup noise"; echo "Blender 4.5.0"')
    result = detect.probe_version(str(exe))
    assert result.outcome is ProbeOutcome.OK
    assert result.version == "4.5.0"


def test_probe_not_found_when_path_missing(tmp_path):
    result = detect.probe_version(str(tmp_path / "does-not-exist"))
    assert result.outcome is ProbeOutcome.NOT_FOUND
    assert not result.ok


@posix_only
@not_root
def test_probe_not_exe_for_non_executable_file(tmp_path):
    plain = tmp_path / "notblender"
    plain.write_text("just text")  # no exec bit
    result = detect.probe_version(str(plain))
    assert result.outcome is ProbeOutcome.NOT_EXE


@posix_only
def test_probe_unparseable_when_output_isnt_blender(tmp_path):
    exe = _make_exe(tmp_path / "notblender", 'echo "GNU bash, version 5"')
    result = detect.probe_version(str(exe))
    assert result.outcome is ProbeOutcome.UNPARSEABLE


@posix_only
def test_probe_unparseable_on_nonzero_exit(tmp_path):
    exe = _make_exe(tmp_path / "blender", 'echo "Blender 4.5.0"; exit 1')
    result = detect.probe_version(str(exe))
    assert result.outcome is ProbeOutcome.UNPARSEABLE


@posix_only
def test_probe_timeout_when_it_hangs(tmp_path):
    exe = _make_exe(tmp_path / "blender", "sleep 5")
    result = detect.probe_version(str(exe), timeout=0.3)
    assert result.outcome is ProbeOutcome.TIMEOUT
