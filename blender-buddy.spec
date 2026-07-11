# blender-buddy.spec — PyInstaller build definition (committed at repo root).
#
# Build locally with:
#   uv run --frozen --group build pyinstaller blender-buddy.spec
# Produces a onedir tree at dist/blender-buddy/ with the launcher
# dist/blender-buddy/blender-buddy[.exe]. Smoke-test it with:
#   ./dist/blender-buddy/blender-buddy --check   # exit 0 == it launches
#
# onedir (not onefile) is deliberate: it notarizes more cleanly on macOS, trips
# far fewer Windows Defender false positives (no unpack-to-temp), and is what CI
# hashes for reproducibility. CI packages the tree per-OS into an archive.
#
# NO UPX: it triggers AV heuristics, slows startup, and breaks macOS code
# signatures. Never enable it here.

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
