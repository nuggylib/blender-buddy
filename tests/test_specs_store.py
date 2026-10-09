"""Unit tests for the specs category (blender_buddy.specs).

Pure data and filesystem tests against `tmp_path` — no Textual. The vocabulary,
the name rules (including the path-traversal strings the rules exist to stop),
and create/list behavior against a real directory.
"""

import pytest

from blender_buddy.specs import naming, schema

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
