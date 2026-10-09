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
