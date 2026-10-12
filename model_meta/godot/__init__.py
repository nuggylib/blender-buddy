"""Godot project discovery.

Finds the folders under a user-chosen root that contain a `project.godot`. This
category only *locates* projects; indexing, export tracking, and asset diffing
are future work. No Textual, no UI — the scan runs off the event loop.
"""
