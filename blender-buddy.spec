# blender-buddy.spec — PyInstaller build definition (committed at repo root).
#
# Build locally with:
#   uv run --frozen --group build pyinstaller blender-buddy.spec
# Produces a onedir tree at dist/blender-buddy/ with the launcher
# dist/blender-buddy/blender-buddy[.exe]. Smoke-test it with:
#   ./dist/blender-buddy/blender-buddy --check   # exit 0 == it launches
#
# On macOS it ALSO wraps that tree in dist/blender-buddy.app (see the BUNDLE at
# the bottom). The .app is the staplable container Developer ID notarization
# needs: a bare onedir launcher cannot carry a stapled notarization ticket, so
# without it the app can't launch cleanly offline on first run. It stays a
# console app (console=True) — a TUI must own a terminal, so it is launched from
# a shell (blender-buddy.app/Contents/MacOS/blender-buddy), never double-clicked.
#   ./dist/blender-buddy.app/Contents/MacOS/blender-buddy --check
#
# onedir (not onefile) is deliberate: it notarizes more cleanly on macOS, trips
# far fewer Windows Defender false positives (no unpack-to-temp), and is what CI
# hashes for reproducibility. CI packages the tree (the .app on macOS) per-OS
# into an archive.
#
# NO UPX: it triggers AV heuristics, slows startup, and breaks macOS code
# signatures. Never enable it here.

import sys

from PyInstaller.utils.hooks import collect_all, collect_data_files

datas, binaries, hiddenimports = [], [], []
for pkg in ("textual", "rich"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

# Ships app.tcss (and any future .tcss) under the preserved blender_buddy/
# prefix, which is what app._resource_path() joins against sys._MEIPASS.
datas += collect_data_files("blender_buddy")

a = Analysis(
    ["blender_buddy/__main__.py"],  # existing entry point — no wrapper needed
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "unittest", "pydoc"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir: binaries/datas are emitted by COLLECT
    name="blender-buddy",
    console=True,  # a TUI MUST own a terminal — never --windowed
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    upx=False,
    name="blender-buddy",
)

# macOS only: wrap the onedir tree in a .app bundle. BUNDLE is the PyInstaller-
# native way to produce a structurally valid bundle (correct Info.plist,
# Contents/MacOS layout, path rewrites) that `codesign`, `notarytool`, and
# `stapler` accept — release.yml Developer ID signs, notarizes, and staples it.
# On Linux/Windows this block is skipped and the onedir tree is the shipped tree.
# The bundle name has no spaces so shell/CI paths need no quoting; the human
# name lives in CFBundleName/CFBundleDisplayName.
if sys.platform == "darwin":
    app = BUNDLE(  # noqa: F821 — BUNDLE is injected into the spec namespace
        coll,
        name="blender-buddy.app",
        icon=None,
        bundle_identifier="dev.mcnuggies.blender-buddy",
        info_plist={
            "CFBundleName": "Blender Buddy",
            "CFBundleDisplayName": "Blender Buddy",
            "CFBundleExecutable": "blender-buddy",
            # It is a terminal app, not a GUI: launched from a shell, never a
            # double-click. Keep it out of the Dock / app-switcher surface.
            "LSBackgroundOnly": False,
            "NSHighResolutionCapable": True,
        },
    )
