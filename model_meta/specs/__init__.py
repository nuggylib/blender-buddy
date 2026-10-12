"""Validation specs: the documents models are checked against.

A spec names what a model of some type must look like — its armature, its mesh
roles and their texture maps, which Blender modifiers are safe. One JSON file
per model type lives beside the config, and the files themselves *are* the list
of supported types.

This category owns the document's vocabulary, the rules for naming one, and
reading/writing them on disk. It validates nothing about a model yet, and holds
no Textual and no UI.
"""
