# Blender Buddy

Blender Buddy is a custom tool built by the McNuggies game dev team. It's sole purpose is
verifying Blender assets are fully prepared for export into a game.

This tool is ideal for games with many models of the same class and have a similar (or 
even identical) setup. It was built for use with Godot.

## Features

1. **Custom Spec Generation**
   - _Generate a spec for your model_
   - _Describe the base setup for your model file_
   - _Advises standard naming convention_
   - _Specs drive validation logic_
2. **Armature Validation**
   - _Verify armature exists_
   - _Verify armature has expected bones_
   - _Verify bone parenting is correct_
2. **Mesh Validation**
   - _Verify expected meshes are present_
   - _Verify meshes are linked to the correct bone_
   - _Verify vertex group weights are correct_

## Download & Install

No Python or `uv` install required — grab a prebuilt binary from the rolling
[`latest`](https://github.com/nuggylib/blender-buddy/releases/tag/latest) release.
Each merge to `main` rebuilds and replaces it, so `latest` is a **moving pointer**
to the current tip of `main` (the same URL serves different bytes over time), not
an archival version. It is published as a prerelease.

Download the archive for your platform, extract it once, and run the
`blender-buddy` launcher inside.

**macOS (Apple Silicon).** Builds are Developer ID signed, notarized by Apple, and
stapled, so they launch with no Gatekeeper prompt and no extra steps — even offline
on first run. Blender Buddy is a terminal app: extract, then run the launcher inside
the `.app` from your terminal (don't double-click it in Finder).

```bash
tar xzf blender-buddy-dev-*-macos-arm64.tar.gz
./blender-buddy.app/Contents/MacOS/blender-buddy
```

If a build ever ships un-notarized (e.g. during a credential rotation) Gatekeeper
will quarantine it; clear the attribute once with
`xattr -cr blender-buddy.app`, then launch as above.

**Intel Macs:** there is no separate Intel build — run the `macos-arm64` binary
under Rosetta 2 (`softwareupdate --install-rosetta` if it isn't installed yet).

**Linux (x86_64).**

```bash
tar xzf blender-buddy-dev-*-linux-x86_64.tar.gz
./blender-buddy/blender-buddy
```

**Windows (x86_64).** Extract the `.zip`, then run
`blender-buddy\blender-buddy.exe`. The binary is unsigned, so SmartScreen may warn
on first launch — choose **More info → Run anyway**.

Each release ships a `SHA256SUMS` manifest; download it next to your archive and
compare `shasum -a 256 <archive>` against the matching line to verify integrity.

## First-run setup

The first time you launch Blender Buddy it runs a short setup wizard to capture the three locations it needs:

1. **Blender executable** — auto-detected on standard installs; the wizard runs `blender --version` to confirm it. flatpak/snap wrappers aren't auto-detected — enter the path manually.
2. **Models directory** — where your source `.blend` files live. If it doesn't exist yet, the wizard offers to create it.
3. **Godot projects root** — a single folder under which Blender Buddy lists every project (any directory containing a `project.godot`).

Your answers are saved once, atomically, so a valid config always boots straight to the dashboard. Quitting mid-wizard writes nothing and re-runs setup next launch. To change a value later, press `s` on the dashboard or launch `blender-buddy --setup` to re-open the wizard pre-populated.

The config file lives in the platform's per-user config directory:

| Platform | Location |
|----------|----------|
| macOS    | `~/Library/Application Support/blender-buddy/config.toml` |
| Linux    | `~/.config/blender-buddy/config.toml` (honors `$XDG_CONFIG_HOME`) |
| Windows  | `%LOCALAPPDATA%\mcnuggies\blender-buddy\config.toml` |

Set `$BLENDER_BUDDY_CONFIG` to a full file path to override the location (used by the test suite so it never touches your real config).

## Development

Blender Buddy uses [uv](https://docs.astral.sh/uv/) for dependency and
environment management. Requires Python 3.11+ (uv will fetch it automatically).

```bash
# Install dependencies (runtime + dev) into a local virtual environment
uv sync

# Launch the TUI
uv run blender-buddy
# ...or equivalently
uv run python -m blender_buddy

# Run the test suite
uv run pytest

# Lint and format
uv run ruff check .
uv run ruff format .
```

During UI development, `uv run textual run --dev blender_buddy.app:BlenderBuddyApp`
enables live CSS editing, and `uv run textual console` (in a second terminal)
captures log output.

### Building a standalone binary

CI produces the downloadable per-OS builds, but you can build one locally to
verify packaging:

```bash
# Build the onedir bundle (uses the committed blender-buddy.spec)
uv run --frozen --group build pyinstaller blender-buddy.spec

# Smoke-test the frozen binary: --check boots the app headlessly, exit 0 == OK
./dist/blender-buddy/blender-buddy --check
./dist/blender-buddy/blender-buddy --version
```

The build writes to `dist/` and `build/` (both gitignored). `--check` is the
same launch gate CI runs against every build before it ships.

