# .github

GitHub-specific configuration for the repository.

## Contents

- `workflows/lint_and_test.yml` — Continuous integration ("Lint & Test" workflow). Runs the `ruff` lint/format gate and the
  `pytest` suite on every push to `main` and every pull request, using the project's `uv`
  toolchain via `astral-sh/setup-uv`.
- `workflows/build.yml` — "Build" workflow. Builds a standalone binary for all four targets
  (`macos-14`/arm64, `macos-13`/x86_64, `ubuntu-latest`, `windows-latest`) on every PR and every
  push to `main`. A `version` job resolves the embedded version string **once** (so all four legs
  embed the same string for a commit); each build leg writes the gitignored `blender_buddy/_version.py`,
  runs `pyinstaller blender-buddy.spec` (onedir), gates on the `--version`/`--check` smoke test against
  the freshly built binary, ad-hoc signs the macOS binaries (arm64 canaries execute; **no** Developer
  ID / notarization here — that is Phase 3's `release.yml`), and packages the onedir tree per-OS
  (`.tar.gz` on Unix, `.zip` on Windows). **Holds no secrets** — it runs on untrusted fork PRs.
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
- **`build.yml` pins every action to a full 40-char commit SHA** with a trailing `# vX.Y.Z`
  comment (a version *tag* is mutable — a compromised action re-tag would then run in CI).
  This is the stronger form of the pinning rule above; prefer it for new workflows and let a
  Dependabot bump move the SHA. (`lint_and_test.yml`/`qa_signoff.yml` still pin by tag — a safe
  follow-up is to migrate them to SHAs too.)
- **Artifact naming.** `build.yml` uploads canary artifacts on PRs
  (`blender-buddy-canary-pr<N>-<shortsha>-<target>`, 14-day retention, so a longer review keeps a
  live link) and stable release-named artifacts on pushes to `main` (`release-<target>`, 1-day
  retention, consumed by `release.yml`). Filename slugs use only `-` (never `+`/`.`, which break in
  URLs and download tooling); the embedded `--version` string keeps SemVer form
  (`0.1.0-canary.pr42+a1b2c3d`).
- On a `pull_request` event, `github.sha` is the ephemeral **merge** commit — use
  `github.event.pull_request.head.sha` for anything identifying the PR's actual code.
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
