"""Persistence layer — the config file Blender Buddy reads and writes.

This is the app's first persistence layer. It holds the three machine-specific
anchors captured by first-time setup (Blender executable, models directory,
Godot projects root) and the machinery to load/save them.

Contains no Textual and no subprocess: every other feature depends on the plain
`Settings` dataclass this package produces, not on how it is stored.
"""
