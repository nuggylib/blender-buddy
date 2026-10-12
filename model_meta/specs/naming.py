"""Rules for a spec's model-type name.

The name is a filename *and* a value stored inside the file, so the rules are
strict and every failure is a message rather than a silent transformation.
`normalize` is deliberately conservative — lowercase, trim, collapse internal
whitespace to hyphens, nothing else. Everything it does not handle `validate`
rejects with a reason, so characters never silently vanish from what was typed.

`_ALLOWED` is the security boundary: it is what rejects `../escape`, `a/b`, and
every path separator before a name is ever joined onto a directory.
"""

from __future__ import annotations

import re

SUFFIX = ".json"
MAX_LENGTH = 64
_ALLOWED = re.compile(r"^[a-z0-9]+(?:[-_][a-z0-9]+)*$")
# Reserved device names on Windows, which paths.py already targets.
_RESERVED = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)


def normalize(raw: str) -> str:
    """Lowercase, trim, and collapse internal whitespace to hyphens."""
    return re.sub(r"\s+", "-", raw.strip().lower())


def validate(raw: str) -> str | None:
    """The reason `raw` is unusable as a spec name, or `None` if it is fine."""
    name = normalize(raw)
    if not name:
        return "Enter a name for the model type."
    if len(name) > MAX_LENGTH:
        return f"Keep the name to {MAX_LENGTH} characters or fewer."
    if not _ALLOWED.match(name):
        return "Use letters, numbers, hyphens and underscores only."
    if name in _RESERVED:
        return f"'{name}' is a reserved filename on Windows — pick another."
    return None
