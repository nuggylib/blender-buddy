"""Model Meta — a TUI for Godot-compatible 3D model specs and scene validation."""

try:
    # Written by CI at build time (gitignored); resolves the full canary/dev
    # version string that gets frozen into a release binary.
    from model_meta._version import __version__  # type: ignore[import-not-found]
except ImportError:
    # Dev fallback; kept in sync with pyproject.toml by tests/test_version.py.
    __version__ = "0.1.0"
