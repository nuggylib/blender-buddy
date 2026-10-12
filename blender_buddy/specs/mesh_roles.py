"""Mesh roles: `mesh_roles`, a role name → role-fields map.

A role's `vtx_grp` is a pattern in `parenting`'s syntax — a literal base whose
dot-segments may be `{n}` placeholders — and must match at least one of the
spec's `required_bones`. Placeholders are all free for now.

Pure functions over strings, like `bones`.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from blender_buddy.specs import bones, parenting


def validate_name(name: str, existing: Collection[str]) -> str | None:
    """Why `name` can't be a new role name, or `None`. Pass it trimmed."""
    if not name:
        return "Enter a role name."
    if name in existing:
        return f"'{name}' is already a mesh role."
    return None


def matches(pattern: str, required: Sequence[str]) -> list[str]:
    """The required bones `pattern` matches, in order."""
    return [bone for bone in required if parenting.match(pattern, bone) is not None]


def validate_vtx_grp(pattern: str, required: Sequence[str]) -> str | None:
    """Why `pattern` is unusable as a `vtx_grp`, or `None`. Pass it trimmed."""
    if not pattern:
        return "Enter a vertex group pattern."
    if len(pattern.encode("utf-8")) > bones.MAX_BYTES:
        return f"Vertex group names are limited to {bones.MAX_BYTES} bytes."
    if "" in pattern.split("."):
        return f"'{pattern}' has an empty segment."
    if not matches(pattern, required):
        return f"'{pattern}' matches no required bone."
    return None


def infer_vtx_grp(checked: Collection[str], required: Sequence[str]) -> str:
    """The pattern matching exactly `checked` among `required`, else `ValueError`."""
    names = [bone for bone in required if bone in checked]
    if not names:
        raise ValueError("Check at least one bone.")
    pattern = parenting.generalize(names)
    if pattern is None:
        first = names[0].split(".")
        other = next(
            name
            for name in names
            if len(name.split(".")) != len(first) or name.split(".")[0] != first[0]
        )
        raise ValueError(f"'{names[0]}' and '{other}' can't share one pattern.")
    if len(pattern.encode("utf-8")) > bones.MAX_BYTES:
        raise ValueError(f"Vertex group names are limited to {bones.MAX_BYTES} bytes.")
    if extra := [bone for bone in matches(pattern, required) if bone not in checked]:
        raise ValueError(f"'{pattern}' would also match {', '.join(extra)}.")
    return pattern
