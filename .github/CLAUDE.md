# .github

GitHub-specific configuration for the repository.

## Contents

- `workflows/lint_and_test.yml` — Continuous integration ("Lint & Test" workflow). Runs the `ruff` lint/format gate and the
  `pytest` suite on every push to `main` and every pull request, using the project's `uv`
  toolchain via `astral-sh/setup-uv`.

## Conventions

- CI must mirror the local dev commands documented in the root `README.md`
  (`uv sync`, `uv run pytest`, `uv run ruff ...`) so "green locally" means "green in CI."
- Use `uv sync --locked` in CI so a stale `uv.lock` fails the build instead of silently
  resolving different dependencies.
- Pin actions to a specific release, not a moving major tag. `astral-sh/setup-uv`'s v8
  series does **not** publish a floating `v8` tag (only `v8.x.y`), so pin the exact
  version (e.g. `@v8.3.2`) and bump deliberately.
