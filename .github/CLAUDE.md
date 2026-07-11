# .github

GitHub-specific configuration for the repository.

## Contents

- `workflows/lint_and_test.yml` — Continuous integration ("Lint & Test" workflow). Runs the `ruff` lint/format gate and the
  `pytest` suite on every push to `main` and every pull request, using the project's `uv`
  toolchain via `astral-sh/setup-uv`.
- `workflows/qa_signoff.yml` — "QA Sign-off" workflow. Fails a PR until the author ticks the
  **Author** checkbox in the `## QA Sign-off` section of the PR body — the developer's explicit
  "I ran the QA Steps and they pass" acknowledgement. It reads the body from the event payload
  (no API token) and greps for a checked `**Author:**` line.
- `pull_request_template.md` — Default pull request description template. Pre-fills every new PR with a
  **Summary** (plus a flat **Changelog** list), numbered **manual QA Steps**, and a **QA Sign-off**
  checkbox the author ticks after running those steps. GitHub auto-populates the PR body from this file.

## Conventions

- CI must mirror the local dev commands documented in the root `README.md`
  (`uv sync`, `uv run pytest`, `uv run ruff ...`) so "green locally" means "green in CI."
- Use `uv sync --locked` in CI so a stale `uv.lock` fails the build instead of silently
  resolving different dependencies.
- Pin actions to a specific release, not a moving major tag. `astral-sh/setup-uv`'s v8
  series does **not** publish a floating `v8` tag (only `v8.x.y`), so pin the exact
  version (e.g. `@v8.3.2`) and bump deliberately.
- Treat the PR body as untrusted input. Pass `github.event.pull_request.body` through an
  `env:` variable, never interpolate it directly into a `run:` script (prevents shell
  injection via a crafted description) — see `workflows/qa_signoff.yml`.
- The `**Author:**` marker text is a contract shared between `pull_request_template.md` and
  the `qa_signoff.yml` grep. Change them together, or the check fails closed on every PR.
- **Making QA Sign-off required:** the check reports the context `QA Sign-off` (the job's
  `name:`). A status check can only be marked required after it has reported at least once,
  so add it to `main`'s protection **after** the introducing PR has run it. Apply the
  setting once via the GitHub API rather than click-ops, e.g.:

  ```bash
  gh api --method POST repos/nuggylib/blender-buddy/rulesets --input - <<'JSON'
  {
    "name": "Require QA sign-off on main",
    "target": "branch",
    "enforcement": "active",
    "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
    "rules": [
      { "type": "required_status_checks",
        "parameters": { "strict_required_status_checks_policy": false,
          "required_status_checks": [ { "context": "QA Sign-off", "integration_id": 15368 } ] } }
    ]
  }
  JSON
  ```

  Confirm the exact context string on a completed run's Checks tab first (GitHub can render
  it as `workflow / job`), and use classic branch protection instead if the repo uses that
  model — do not configure both.
