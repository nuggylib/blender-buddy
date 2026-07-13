"""Locate and validate the Blender executable.

Pure detection logic — **no Textual, no UI**. `candidate_paths()` scans the
platform's standard install locations; `probe_version()` shells out to
`<exe> --version`. Call `probe_version()` from a Textual worker (never the event
loop): it blocks on a subprocess bounded by a timeout.
"""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ProbeOutcome(Enum):
    """The distinct results of probing a candidate Blender executable."""

    OK = "ok"  # ran and identified itself as Blender
    NOT_FOUND = "not-found"  # nothing at that path / not on PATH
    NOT_EXE = "not-exe"  # exists but can't be executed (perms, wrong format, a dir)
    TIMEOUT = "timeout"  # started but didn't respond in time
    UNPARSEABLE = "unparseable"  # ran, but output isn't Blender's `--version`


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of `probe_version`. `version` is set only when `outcome is OK`."""

    outcome: ProbeOutcome
    version: str = ""
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.outcome is ProbeOutcome.OK


def candidate_paths() -> list[Path]:
    """Return existing Blender executables at standard per-platform locations.

    macOS resolves `Blender.app` to its inner `Contents/MacOS/Blender` binary;
    Windows globs the versioned `Blender Foundation\\*` install dirs; Linux checks
    the common prefixes. `shutil.which("blender")` is appended on every platform.
    Order is preserved and duplicates removed, so the first entry is the best
    default. flatpak/snap wrappers are out of scope (not plain executable paths).
    """
    if sys.platform == "darwin":
        base = ["/Applications/Blender.app/Contents/MacOS/Blender"]
    elif sys.platform == "win32":
        # The version dir varies (Blender 4.5, 4.4, …) — glob real installs.
        base = [
            str(p)
            for p in Path(r"C:\Program Files\Blender Foundation").glob("*/blender.exe")
        ]
    else:
        base = ["/usr/bin/blender", "/usr/local/bin/blender"]

    found = [Path(p) for p in base if Path(p).exists()]
    which = shutil.which("blender")
    if which:
        found.append(Path(which))

    # De-duplicate while preserving order (which may repeat a base path);
    # dict keys are insertion-ordered, so first occurrence wins.
    return list(dict.fromkeys(found))


def probe_version(exe: str | Path, timeout: float = 10.0) -> ProbeResult:
    """Run `<exe> --version` and classify the result.

    Call this from a Textual worker, never the event loop — it blocks on a
    subprocess. Every failure mode is a structured `ProbeResult`, never a raised
    exception and never a hang (the timeout guarantees return).
    """
    try:
        proc = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return ProbeResult(ProbeOutcome.NOT_FOUND, message="No file at that path.")
    except (PermissionError, OSError):
        # IsADirectoryError, exec-format errors, permission denied, etc.
        return ProbeResult(
            ProbeOutcome.NOT_EXE, message="Not an executable Blender binary."
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(
            ProbeOutcome.TIMEOUT, message="Blender did not respond (timed out)."
        )

    if proc.returncode == 0:
        # Blender prints `Blender X.Y.Z` as a line; scan for it rather than
        # trusting line 0, so a leading banner can't be mistaken for the version.
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("Blender "):
                return ProbeResult(
                    ProbeOutcome.OK, version=line.removeprefix("Blender").strip()
                )

    return ProbeResult(ProbeOutcome.UNPARSEABLE, message="That program is not Blender.")
