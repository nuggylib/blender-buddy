"""Blender Buddy — a TUI for building Godot-ready game models in Blender."""

try:
    # Written by CI at build time (gitignored); resolves the full canary/dev
    # version string that gets frozen into a release binary.
    from blender_buddy._version import __version__  # type: ignore[import-not-found]
except ImportError:
    # Dev fallback; kept in sync with pyproject.toml by tests/test_version.py.
    __version__ = "0.1.0"
