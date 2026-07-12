# .github

GitHub-specific configuration for the repository.

## Contents

- `workflows/lint_and_test.yml` — Continuous integration ("Lint & Test" workflow). Runs the `ruff` lint/format gate and the
  `pytest` suite on every push to `main` and every pull request, using the project's `uv`
  toolchain via `astral-sh/setup-uv`.
- `workflows/build.yml` — "Build" workflow. Builds a standalone binary for three targets
  (`macos-14`/arm64, `ubuntu-latest`, `windows-latest`) on every PR and every
  push to `main`. macOS is **Apple Silicon only** — the Intel runner (`macos-13`) is a deprecated,
  scarce image that queues for many minutes (plan I8); Intel Mac users run the arm64 build under
  Rosetta 2. A `version` job resolves the embedded version string **once** (so all legs
  embed the same string for a commit); each build leg writes the gitignored `blender_buddy/_version.py`,
  runs `pyinstaller blender-buddy.spec` (onedir), gates on the `--version`/`--check` smoke test against
  the freshly built binary, ad-hoc signs the macOS binaries (arm64 canaries execute; **no** Developer
  ID / notarization here — that is Phase 3's `release.yml`), and packages the onedir tree per-OS
  (`.tar.gz` on Unix, `.zip` on Windows). On PRs each leg writes a one-click download link to the
  run **Summary** (via `upload-artifact`'s `artifact-url` + `$GITHUB_STEP_SUMMARY`) so a reviewer
  never has to expand logs — Actions artifacts have no public URL, so the link needs a signed-in
  session and dies with the 14-day retention. **Holds no secrets** — it runs on untrusted fork PRs.
- `workflows/release.yml` — "Release (rolling latest)" workflow. Triggered by `workflow_run` on the
  **Build** workflow completing (not `needs:`), so it stays decoupled from the secret-free, fork-facing
  `build.yml` — a cancelled or failed Build never releases. A single job `if:` guard narrows the many
  `workflow_run` firings to the one that should publish: `conclusion == 'success'` **and** the triggering
  Build's `event == 'push'` **and** `head_branch == 'main'` **and** `repository == 'nuggylib/blender-buddy'`.
  One Ubuntu `publish` job downloads the `release-<target>` archives from the triggering run by
  `run-id` (workflow_run artifacts do **not** auto-transfer), writes `SHA256SUMS`, force-moves the
  `latest` tag to the merged commit, and rolls the `latest` prerelease in place via
  `softprops/action-gh-release`. **Phase 3a: ad-hoc signing only** — the macOS binary was already
  ad-hoc signed + packaged by `build.yml`, so there is no macOS runner here and **no secrets**; the
  Developer ID sign + notarize `sign-macos` job lands in Phase 3b ahead of `publish`.
- `release-notes-latest.md` — Body for the rolling `latest` prerelease (`release.yml` passes it as
  `body_path`). Per-OS download/extract/run steps, the `xattr -cr` quarantine step (ad-hoc, **not yet
  notarized**), the Rosetta 2 note for Intel Macs, the moving-`latest` caveat, and `SHA256SUMS`
  verification. Keep it in sync with the README's "Download & Install" section.
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
- **Rolling `latest` release.** There is exactly one moving `latest` prerelease, rebuilt on every
  push to `main`. `release.yml` **force-moves the `latest` tag** to the merged commit and clobbers the
  same-named assets in place — `softprops/action-gh-release` updates the release object but never moves
  an existing tag, hence the manual `git tag -f latest && git push -f`. Keep it `--prerelease`
  (`make_latest: false`) so it never steals the "Latest" badge from a future tagged `vX.Y.Z`. **GitHub
  Immutable Releases must stay DISABLED** while `latest` is a moving tag (it forbids tag moves + asset
  mutation). Link the explicit `…/releases/download/latest/<file>` asset URL, not
  `…/releases/latest/download/…` (which follows the "Latest" badge, not this prerelease).
- **`workflow_run` token + artifacts.** A `workflow_run`-triggered workflow gets a **read-only** token
  by default and its `github.*` fields describe the *triggering* run (it always runs from the default
  branch). Grant `contents: write` (release + tag push) **and** `actions: read` (cross-run
  `download-artifact`) on the job, and pull the upstream artifacts by
  `run-id: ${{ github.event.workflow_run.id }}` + `github-token` — they do not auto-transfer.
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
