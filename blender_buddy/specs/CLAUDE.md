# blender_buddy/specs/

Validation specs — the documents models are checked against. One JSON file per
model type, living in `specs/` beside the config file. This category owns the
document's vocabulary, the rules for naming one, and reading/writing them on
disk. **No Textual, no UI.**

## Files
- `schema.py` — the document's vocabulary (`TEXTURE_MAPS`, `MODIFIERS`) and
  `skeleton(model_type)`, the complete empty-valued document a new spec is
  written as.
- `naming.py` — `normalize(raw)` and `validate(raw)`: the rules a model-type
  name must satisfy to be both a filename and a stored value.
- `store.py` — the filesystem: `create(specs_dir, model_type)` writes a new
  skeleton (raising `FileExistsError` rather than overwriting),
  `list_specs(specs_dir)` classifies every spec as `OK` / `UNREADABLE` /
  `MISMATCHED`, and `count(specs_dir)` tallies them without parsing any.

## `create` uses O_EXCL, not `config/store.py`'s atomic replace
`config/store.py` writes to a temp file and `os.replace`s it. `create`
deliberately does not: a replace would *overwrite* the existing file, defeating
the one guarantee this function exists to make. `open(path, "x")` makes "reject
if it exists" the filesystem's job and closes the TOCTOU window an `exists()`
check would leave open. The cost is that a crash mid-write can leave a
truncated **new** file — which `list_specs` already reports as `UNREADABLE`
with a fix step, a visible and fixable state rather than silent corruption.

`list_specs` and `count` are read-only and **never create the directory**; only
`create` does, lazily, so a fresh install has no empty `specs/` folder sitting
in its config directory. `list_specs` catches per *file*, never per directory:
one malformed spec must not blank the list.

## `model_type` is a dynamic enum
There is no hardcoded list of model types. The user types a name, it is
normalized, and it becomes **both** the filename stem and the `model_type` value
inside the file. The supported model types *are* `specs/*.json`, so adding one
never needs a release. The **stem is the identity** — if the two ever disagree,
the filename wins and the file is reported as mismatched.

## The constants are vocabulary, not yet enforced
`TEXTURE_MAPS` (all 19 of Godot's `BaseMaterial3D.TextureParam`, lowercased
without the `TEXTURE_` prefix) and `MODIFIERS` (a curated 20 Blender modifier
identifiers, not Blender's full ~55, which drifts every release) are the schema
*definition*. **Nothing validates against them.** A spec written today can hold
any string in those arrays and no code objects. They exist so the skeleton and a
later validator key off one list instead of two. Do not describe them as
shipped validation.

## Conventions
- **Validate before joining a path.** `naming._ALLOWED` is the security
  boundary — it is what rejects `../escape`, `a/b`, and every path separator.
  Nothing builds a path from an unvalidated name.
- Normalization lowercases, so `Vehicle` and `vehicle` collide. That is
  intended; messages quote the **normalized** name so the collision is legible.
