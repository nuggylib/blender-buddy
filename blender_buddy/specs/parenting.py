"""Parenting patterns: `armature.parenting`, a parent-pattern → child-patterns map.

A pattern is a bone name whose dot-segments may be `{n}` placeholders, each
matching exactly one whole segment. The base is always literal. A placeholder
in the key is *bound* — its children reuse what it matched — and one that only
appears in a child is *free*. Patterns resolve against `required_bones`, so a
key never repeats a name the spec already holds.

Pure functions over strings and dicts, like `bones`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from blender_buddy.specs import bones

_PLACEHOLDER = re.compile(r"^\{\d+\}$")


def is_placeholder(part: str) -> bool:
    """Whether one dot-separated part of a pattern is a `{n}` placeholder."""
    return bool(_PLACEHOLDER.match(part))


def has_placeholder_segment(name: str) -> bool:
    """A bone with a literal `{n}` segment can't be told apart from a pattern."""
    return any(is_placeholder(part) for part in name.split(".")[1:])


def match(
    pattern: str, name: str, bound: Mapping[str, str] | None = None
) -> dict[str, str] | None:
    """The placeholder bindings that make `pattern` match `name`, or `None`."""
    pattern_parts = pattern.split(".")
    name_parts = name.split(".")
    if len(pattern_parts) != len(name_parts) or pattern_parts[0] != name_parts[0]:
        return None
    bindings = dict(bound or {})
    for part, segment in zip(pattern_parts[1:], name_parts[1:], strict=True):
        if is_placeholder(part):
            if bindings.setdefault(part, segment) != segment:
                return None
        elif part != segment:
            return None
    return bindings


def pairs(
    parenting: Mapping[str, Sequence[str]], required: Sequence[str]
) -> list[tuple[str, str]]:
    """Every distinct (parent, child) the map resolves to among `required`."""
    found: dict[tuple[str, str], None] = {}
    for key, patterns in parenting.items():
        for parent in required:
            bound = match(key, parent)
            if bound is None:
                continue
            for pattern in patterns:
                for child in required:
                    if match(pattern, child, bound) is not None:
                        found[(parent, child)] = None
    return list(found)


def resolve(
    parenting: Mapping[str, Sequence[str]], required: Sequence[str]
) -> dict[str, list[str]]:
    """Each child bone → its distinct parents. More than one is a conflict."""
    parents: dict[str, list[str]] = {}
    for parent, child in pairs(parenting, required):
        parents.setdefault(child, []).append(parent)
    return parents


def ancestors(bone: str, resolved: Mapping[str, Sequence[str]]) -> set[str]:
    """Every bone above `bone`. Contains `bone` itself only on a cycle."""
    found: set[str] = set()
    stack = list(resolved.get(bone, ()))
    while stack:
        parent = stack.pop()
        if parent not in found:
            found.add(parent)
            stack.extend(resolved.get(parent, ()))
    return found


def is_valid(parenting: Mapping[str, Sequence[str]], required: Sequence[str]) -> bool:
    """At most one parent per bone, and no bone above itself."""
    resolved = resolve(parenting, required)
    if any(len(parents) > 1 for parents in resolved.values()):
        return False
    return all(bone not in ancestors(bone, resolved) for bone in resolved)


def merge(
    parenting: Mapping[str, Sequence[str]], entries: Mapping[str, Sequence[str]]
) -> dict[str, list[str]]:
    """A copy of `parenting` with `entries` appended per key, deduped."""
    merged = {key: list(patterns) for key, patterns in parenting.items()}
    for key, patterns in entries.items():
        existing = merged.setdefault(key, [])
        existing.extend(p for p in dict.fromkeys(patterns) if p not in existing)
    return merged


def infer(
    parent: str,
    children: Iterable[str],
    required: Sequence[str],
    inverses: Mapping[str, str],
    parenting: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    """The entries that parent `children` to `parent` (and its mirrors).

    Per child, in `required` order: bind the variable segments it shares with
    the parent, then try freeing its other variable segments, then not. A
    pattern is kept only if what it matches for `parent` was all checked and
    the merged map stays valid; otherwise the exact names are used.
    """
    checked = set(children)
    table = {**inverses, **bones.BUILTIN_INVERSES}
    entries: dict[str, list[str]] = {}
    covered: set[str] = set()
    for child in required:
        if child not in checked or child in covered:
            continue
        for key, pattern in _candidates(parent, child, table):
            bound = match(key, parent)
            assert bound is not None
            mine = {b for b in required if match(pattern, b, bound) is not None}
            trial = merge(entries, {key: [pattern]})
            if mine <= checked and is_valid(merge(parenting, trial), required):
                entries, covered = trial, covered | mine
                break
        else:
            entries = merge(entries, {parent: [child]})
            covered.add(child)
    return entries


# --- internals -------------------------------------------------------------


def _candidates(
    parent: str, child: str, table: Mapping[str, str]
) -> list[tuple[str, str]]:
    """(key, child pattern) to try: shared segments bound, then free, then not."""
    key_parts = parent.split(".")
    child_parts = child.split(".")
    replaced: set[int] = set()
    count = 0
    start = 1
    for i, part in enumerate(key_parts[1:], start=1):
        if not _variable(part, table):
            continue
        j = next(
            (j for j in range(start, len(child_parts)) if child_parts[j] == part),
            None,
        )
        if j is None:
            continue
        count += 1
        key_parts[i] = child_parts[j] = f"{{{count}}}"
        replaced.add(j)
        start = j + 1
    key = ".".join(key_parts)
    bound_only = ".".join(child_parts)
    for j, part in enumerate(child_parts[1:], start=1):
        if j not in replaced and _variable(part, table):
            count += 1
            child_parts[j] = f"{{{count}}}"
    candidates = [(key, ".".join(child_parts)), (key, bound_only)]
    exact = (parent, child)
    return [c for c in dict.fromkeys(candidates) if c != exact]


def _variable(part: str, table: Mapping[str, str]) -> bool:
    """Whether segment `part` (no leading dot) has a non-self inverse."""
    inverse = table.get(f".{part}")
    return inverse is not None and inverse != f".{part}"
