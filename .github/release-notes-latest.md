# Latest (rolling build)

This is the **rolling `latest` build** — rebuilt and replaced automatically on every merge to `main`, so it always reflects the current tip of `main`. It is a *moving pointer*, not an archival version: the same `latest` download URL serves different bytes over time. It is published as a **prerelease** so it never takes the "Latest" badge reserved for future tagged `vX.Y.Z` releases.

Each asset is a per-OS archive of a self-contained bundle — no Python or `uv` install required. Download the archive for your platform, extract it once, and run the `blender-buddy` launcher inside.

## Downloads

| Platform | Asset |
|----------|-------|
| macOS (Apple Silicon) | `blender-buddy-dev-<sha>-macos-arm64.tar.gz` |
| Linux (x86_64) | `blender-buddy-dev-<sha>-linux-x86_64.tar.gz` |
| Windows (x86_64) | `blender-buddy-dev-<sha>-windows-x86_64.zip` |

**Intel Macs:** there is no separate Intel build — run the `macos-arm64` binary under **Rosetta 2** (macOS installs it on first launch of an Apple-Silicon binary, or run `softwareupdate --install-rosetta`).

## macOS (Apple Silicon)

These builds are **Developer ID signed and notarized by Apple**, and the notarization ticket is **stapled** — so they launch with no Gatekeeper prompt and no extra steps, even on a machine that is offline the first time you run them. Blender Buddy is a terminal app: extract the archive and run the launcher **inside the `.app`** from your terminal (don't double-click it in Finder).

```bash
tar xzf blender-buddy-dev-*-macos-arm64.tar.gz
./blender-buddy.app/Contents/MacOS/blender-buddy
```

<details>
<summary><b>If you see a security warning</b> (degraded fallback)</summary>

If a build ever ships without notarization — for example while a signing credential is being rotated — Gatekeeper will quarantine it. Clear the quarantine attribute once, then launch:

```bash
xattr -cr blender-buddy.app
./blender-buddy.app/Contents/MacOS/blender-buddy
```

</details>

## Linux

```bash
tar xzf blender-buddy-dev-*-linux-x86_64.tar.gz
./blender-buddy/blender-buddy
```

## Windows

Extract the `.zip`, then run `blender-buddy\blender-buddy.exe`. The binary is unsigned, so SmartScreen may warn on first launch — choose **More info → Run anyway**.

## Verifying your download

Every release includes `SHA256SUMS`. Download it alongside your archive, compute the archive's hash, and confirm it matches the corresponding line:

```bash
shasum -a 256 blender-buddy-dev-*-macos-arm64.tar.gz   # macOS / Linux
# then compare the printed hash against the matching row in SHA256SUMS
```
