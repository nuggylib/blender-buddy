# model_meta/specs/

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
- `bones.py` — pure bone-name logic: `split`, `validate_name` (63-byte
  Blender limit, no empty segments), `next_missing`, `validate_inverse`,
  `pairs` (blank answer → self-mapping), and `variants`, which **raises on any
  unmapped segment** so a partial checklist can't be built. `.L`/`.R` are
  `BUILTIN_INVERSES` in code, never written to a spec and never remappable.
  Source-agnostic: typed or scene-inferred names go through the same calls.
- `parenting.py` — pure `armature.parenting` logic. A pattern is a bone name
  whose segments may be `{n}`, each matching one whole segment (base always
  literal). Key placeholders are **bound** (children reuse the value); child-only
  ones are **free**. `match`, `generalize` (`{n}` wherever names differ),
  `pairs`/`resolve` (against `required_bones`), `ancestors`, `is_valid` (≤1
  parent, no cycles), `merge` (append-dedupe per key).
  `infer(parents, children, …)` is **what you check is what you get**:
  each child pairs with the one checked parent whose distinguishing segments it
  holds (else `ValueError`); the key placeholders the positions where checked
  parents differ (and must match exactly them); child patterns bind those
  values, free the most segments that still vary, and are kept only if they
  resolve to exactly the intended pairs and keep `is_valid`. Anything else is
  written as **exact names**. Other syntaxes (`*`, regex) just match literally.
- `mesh_roles.py` — pure `mesh_roles` logic. `validate_name` (trimmed,
  non-empty, unique by exact compare) and `infer_vtx_grp(checked, required)`:
  the `parenting`-syntax pattern (`generalize`, 63-byte limit) that `matches`
  **exactly** the checked bones, else `ValueError` naming why (incl. any extra
  bones it would match). Every `{n}` is free for now.
- `store.py` — the filesystem: `create(specs_dir, model_type)` writes a new
  skeleton (raising `FileExistsError` rather than overwriting),
  `list_specs(specs_dir)` classifies every spec as `OK` / `UNREADABLE` /
  `MISMATCHED`, and `count(specs_dir)` tallies them without parsing any.
  `read(path)` returns one document, raising `OSError` / `ValueError` when it
  is unreadable, not an object, or has a malformed `object_name` /
  `required_bones` / `bone_name_inverses` / `parenting`, or a `mesh_roles` that
  isn't a map of objects with string `vtx_grp`s (`armature_name()` /
  `required_bones()` / `bone_name_inverses()` / `parenting_map()` /
  `mesh_roles()` default them for older specs). `update_armature(path,
  add_bones=, set_inverses=, drop_inverses=, object_name=, add_parenting=)`
  re-reads, patches **only**
  those keys (bones deduped, drops before sets, `object_name=None` leaves the
  name alone, parenting merged via `parenting.merge`), and writes
  atomically — hand edits to anything else survive.
  `add_mesh_role(path, name, vtx_grp)` re-reads, raises `ValueError` on a
  taken name, and writes only `mesh_roles[name] = {"vtx_grp": …}` the same way.

## Updates replace atomically; `create` uses O_EXCL
`update_armature` and `add_mesh_role` write a sibling `.tmp` and `os.replace`
it, like `config/store.py`: replacing *is* the point of an update, and a crash never
leaves a half-written spec. `create` deliberately does not: a replace would
*overwrite* the existing file, defeating
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
