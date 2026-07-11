# .github

GitHub-specific configuration for the repository.

## Contents

- `workflows/ci.yml` — Continuous integration. Runs the `ruff` lint/format gate and the
  `pytest` suite on every push to `main` and every pull request, using the project's `uv`
  toolchain via `astral-sh/setup-uv`.

## Conventions

- CI must mirror the local dev commands documented in the root `README.md`
  (`uv sync`, `uv run pytest`, `uv run ruff ...`) so "green locally" means "green in CI."
- Use `uv sync --locked` in CI so a stale `uv.lock` fails the build instead of silently
  resolving different dependencies.
- Pin actions to a major version tag (e.g. `@v8`); bump deliberately.
