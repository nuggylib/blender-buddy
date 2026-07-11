"""Guards the single source of truth for the version string.

``pyproject.toml`` is authoritative; ``blender_buddy.__init__`` carries a static
fallback for dev checkouts (CI overrides it with a generated ``_version.py`` at
build time). This test fails on drift between the two so they can't silently
diverge.
"""

import importlib.util
import tomllib
from pathlib import Path

import pytest

import blender_buddy

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def test_init_fallback_matches_pyproject():
    if importlib.util.find_spec("blender_buddy._version") is not None:
        pytest.skip("built checkout: _version.py overrides the fallback")

    pyproject_version = tomllib.loads(_PYPROJECT.read_text())["project"]["version"]
    assert blender_buddy.__version__ == pyproject_version
