"""Guards the single source of truth for the version string.

``pyproject.toml`` is authoritative; ``model_meta.__init__`` carries a static
fallback for dev checkouts (CI overrides it with a generated ``_version.py`` at
build time). This test fails on drift between the two so they can't silently
diverge.
"""

import importlib.util
import tomllib
from pathlib import Path

import pytest

import model_meta

_PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"


def test_init_fallback_matches_pyproject():
    if importlib.util.find_spec("model_meta._version") is not None:
        pytest.skip("built checkout: _version.py overrides the fallback")

    pyproject_version = tomllib.loads(_PYPROJECT.read_text())["project"]["version"]
    assert model_meta.__version__ == pyproject_version
