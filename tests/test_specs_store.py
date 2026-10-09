"""Unit tests for the specs category (blender_buddy.specs).

Pure data and filesystem tests against `tmp_path` — no Textual. The vocabulary,
the name rules (including the path-traversal strings the rules exist to stop),
and create/list behavior against a real directory.
"""

import json

import pytest

from blender_buddy.specs import naming, schema, store

# --- vocabulary ------------------------------------------------------------


def test_texture_maps_holds_every_godot_channel():
    """All 19 `BaseMaterial3D.TextureParam` members, lowercased and unprefixed."""
    assert len(schema.TEXTURE_MAPS) == 19
    assert len(set(schema.TEXTURE_MAPS)) == 19
    assert "albedo" in schema.TEXTURE_MAPS
    assert "subsurface_transmittance" in schema.TEXTURE_MAPS
    assert "orm" in schema.TEXTURE_MAPS
    # The prefix is stripped and nothing shouts — these are JSON values.
    assert all(name == name.lower() for name in schema.TEXTURE_MAPS)
    assert not any(name.startswith("texture_") for name in schema.TEXTURE_MAPS)


def test_modifiers_holds_the_curated_set():
    """Blender's identifiers verbatim (upper snake case), curated to 20."""
    assert len(schema.MODIFIERS) == 20
    assert len(set(schema.MODIFIERS)) == 20
    assert "ARMATURE" in schema.MODIFIERS
    assert "WEIGHTED_NORMAL" in schema.MODIFIERS
    assert all(name == name.upper() for name in schema.MODIFIERS)


# --- skeleton --------------------------------------------------------------


def test_skeleton_is_complete_and_empty():
    """Every key present with an empty value: a valid-shaped spec from the
    first write, and a document that explains the schema by existing."""
    document = schema.skeleton("vehicle")

    assert document["model_type"] == "vehicle"
    assert set(document) == {"model_type", "armature", "mesh_roles", "modifiers"}
    assert document["armature"] == {
        "object_name": "",
        "required_bones": [],
        "parenting": {},
    }
    assert document["mesh_roles"] == {}
    assert document["modifiers"] == {
        "required": {"skinned_meshes": []},
        "allowed": [],
        "warn": [],
        "fail": [],
    }


def test_skeleton_does_not_share_mutable_state_between_calls():
    """Built fresh each call — a shared default would leak one spec's edits into
    the next file written in the same session."""
    first = schema.skeleton("vehicle")
    first["armature"]["required_bones"].append("root")
    assert schema.skeleton("character")["armature"]["required_bones"] == []


# --- normalize -------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("vehicle", "vehicle"),
        ("Vehicle", "vehicle"),
        ("  vehicle  ", "vehicle"),
        ("space ship", "space-ship"),
        ("space   ship", "space-ship"),
        ("Space\tShip", "space-ship"),
        ("rig_v2", "rig_v2"),
    ],
)
def test_normalize_lowercases_trims_and_collapses_whitespace(raw, expected):
    assert naming.normalize(raw) == expected


# --- validate --------------------------------------------------------------


@pytest.mark.parametrize("raw", ["vehicle", "space-ship", "rig_v2", "Space Ship", "a"])
def test_validate_accepts_usable_names(raw):
    assert naming.validate(raw) is None


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "\t\n"],
    ids=["empty", "spaces", "whitespace"],
)
def test_validate_rejects_an_empty_name(raw):
    assert naming.validate(raw) == "Enter a name for the model type."


def test_validate_rejects_an_over_length_name():
    reason = naming.validate("v" * (naming.MAX_LENGTH + 1))
    assert reason is not None
    assert str(naming.MAX_LENGTH) in reason
    # The boundary itself is fine.
    assert naming.validate("v" * naming.MAX_LENGTH) is None


@pytest.mark.parametrize(
    "raw",
    [
        "../x",
        "../../etc/passwd",
        "a/b",
        "a\\b",
        "/absolute",
        "my.spec",
        "-lead",
        "trail-",
        "_lead",
        "double--hyphen",
        "spec!",
        "spec name!",
    ],
)
def test_validate_rejects_out_of_charset_names(raw):
    """One pattern, one message — and it is what stops a name from ever being
    read as a path. Validation runs before any path is joined."""
    assert naming.validate(raw) == "Use letters, numbers, hyphens and underscores only."


@pytest.mark.parametrize("raw", ["con", "CON", "nul", "LPT1", "com9", "aux", "prn"])
def test_validate_rejects_windows_reserved_names(raw):
    reason = naming.validate(raw)
    assert reason is not None
    assert "reserved" in reason
    assert raw.lower() in reason  # quotes the normalized name


# --- create ----------------------------------------------------------------


def test_create_writes_a_parseable_skeleton(tmp_path):
    specs = tmp_path / "specs"
    specs.mkdir()

    path = store.create(specs, "vehicle")

    assert path == specs / "vehicle.json"
    text = path.read_text(encoding="utf-8")
    assert json.loads(text) == schema.skeleton("vehicle")
    assert text.endswith("}\n")  # trailing newline, so it diffs cleanly
    assert "\n  " in text  # indent=2, not one dense line


def test_create_makes_the_specs_dir_when_absent(tmp_path):
    """`create` is the only thing that creates the directory, lazily."""
    specs = tmp_path / "nested" / "specs"
    assert not specs.exists()

    store.create(specs, "vehicle")
    assert (specs / "vehicle.json").is_file()


def test_create_refuses_to_overwrite_an_existing_spec(tmp_path):
    """O_EXCL, not a replace: the existing file must be byte-identical after."""
    specs = tmp_path / "specs"
    path = store.create(specs, "vehicle")
    before = path.read_bytes()

    with pytest.raises(FileExistsError):
        store.create(specs, "vehicle")

    assert path.read_bytes() == before


# --- list_specs ------------------------------------------------------------


def _write(specs_dir, name, payload):
    """Hand-write a spec file; `payload` is raw text or a JSON-able object."""
    specs_dir.mkdir(parents=True, exist_ok=True)
    path = specs_dir / f"{name}.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_list_specs_returns_entries_sorted_by_name(tmp_path):
    specs = tmp_path / "specs"
    for name in ("vehicle", "character", "prop"):
        store.create(specs, name)

    entries = store.list_specs(specs)
    assert [entry.model_type for entry in entries] == ["character", "prop", "vehicle"]
    assert {entry.state for entry in entries} == {store.SpecState.OK}
    assert entries[0].path == specs / "character.json"


def test_list_specs_flags_a_model_type_filename_disagreement(tmp_path):
    """The stem is the identity, so the file's own `model_type` losing to it is
    reported rather than silently preferred."""
    specs = tmp_path / "specs"
    _write(specs, "vehicle", schema.skeleton("spaceship"))

    (entry,) = store.list_specs(specs)
    assert entry.state is store.SpecState.MISMATCHED
    assert entry.model_type == "vehicle"


def test_list_specs_flags_a_missing_model_type_key(tmp_path):
    specs = tmp_path / "specs"
    _write(specs, "vehicle", {"mesh_roles": {}})

    (entry,) = store.list_specs(specs)
    assert entry.state is store.SpecState.MISMATCHED


@pytest.mark.parametrize(
    "payload",
    ["{not json at all", "[]", '"a string"', "null", ""],
    ids=["malformed", "array", "string", "null", "empty"],
)
def test_list_specs_flags_unreadable_files(tmp_path, payload):
    """Unparseable *and* valid-JSON-wrong-type both land as UNREADABLE — the
    fix is the same (open it or delete it) either way."""
    specs = tmp_path / "specs"
    _write(specs, "vehicle", payload)

    (entry,) = store.list_specs(specs)
    assert entry.state is store.SpecState.UNREADABLE


def test_list_specs_keeps_the_good_entries_beside_a_bad_one(tmp_path):
    """One malformed file must never blank the list — the catch is per file."""
    specs = tmp_path / "specs"
    store.create(specs, "vehicle")
    store.create(specs, "character")
    _write(specs, "broken", "{nope")

    entries = store.list_specs(specs)
    assert [entry.model_type for entry in entries] == [
        "broken",
        "character",
        "vehicle",
    ]
    assert [entry.state for entry in entries] == [
        store.SpecState.UNREADABLE,
        store.SpecState.OK,
        store.SpecState.OK,
    ]


def test_list_specs_on_a_missing_dir_returns_empty_and_creates_nothing(tmp_path):
    """Read-only: a fresh install gets no empty folder in its config dir."""
    specs = tmp_path / "specs"

    assert store.list_specs(specs) == []
    assert not specs.exists()


def test_list_specs_ignores_non_json_files(tmp_path):
    specs = tmp_path / "specs"
    store.create(specs, "vehicle")
    (specs / "notes.txt").write_text("scratch", encoding="utf-8")
    (specs / "backup.json.bak").write_text("{}", encoding="utf-8")
    (specs / "nested.json").mkdir()  # a directory named like a spec

    assert [entry.model_type for entry in store.list_specs(specs)] == ["vehicle"]


# --- count -----------------------------------------------------------------


def test_count_counts_without_parsing(tmp_path):
    specs = tmp_path / "specs"
    store.create(specs, "vehicle")
    _write(specs, "broken", "{nope")  # unparseable still counts as a spec file

    assert store.count(specs) == 2


def test_count_of_a_missing_dir_is_zero(tmp_path):
    specs = tmp_path / "specs"
    assert store.count(specs) == 0
    assert not specs.exists()
