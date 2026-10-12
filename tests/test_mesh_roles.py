"""Unit tests for mesh-role validation (blender_buddy.specs.mesh_roles)."""

import pytest

from blender_buddy.specs import bones, mesh_roles

REQUIRED = [
    "root",
    "susarm.front.top.L",
    "susarm.front.top.R",
    "susarm.rear.top.L",
    "susarm.rear.bottom.L",
]


# --- validate_name ---------------------------------------------------------


def test_validate_name_accepts_a_new_name():
    assert mesh_roles.validate_name("susarm_upper", ["body"]) is None


def test_validate_name_rejects_blank():
    assert mesh_roles.validate_name("", []) == "Enter a role name."


def test_validate_name_rejects_a_duplicate():
    assert (
        mesh_roles.validate_name("body", ["body"]) == "'body' is already a mesh role."
    )


def test_validate_name_compares_exactly():
    assert mesh_roles.validate_name("Body", ["body"]) is None


# --- matches ---------------------------------------------------------------


def test_matches_an_exact_name():
    assert mesh_roles.matches("root", REQUIRED) == ["root"]


def test_matches_placeholders_across_segments_in_order():
    assert mesh_roles.matches("susarm.{1}.top.{2}", REQUIRED) == [
        "susarm.front.top.L",
        "susarm.front.top.R",
        "susarm.rear.top.L",
    ]


def test_matches_needs_the_same_segment_count():
    assert mesh_roles.matches("susarm.{1}", REQUIRED) == []


def test_matches_keeps_the_base_literal():
    assert mesh_roles.matches("{1}.front.top.L", REQUIRED) == []


# --- validate_vtx_grp ------------------------------------------------------


def test_validate_vtx_grp_accepts_a_matching_pattern():
    assert mesh_roles.validate_vtx_grp("susarm.{1}.top.{2}", REQUIRED) is None


def test_validate_vtx_grp_rejects_blank():
    assert mesh_roles.validate_vtx_grp("", REQUIRED) == "Enter a vertex group pattern."


def test_validate_vtx_grp_rejects_over_the_byte_limit():
    pattern = "a" * (bones.MAX_BYTES + 1)
    assert mesh_roles.validate_vtx_grp(pattern, [pattern]) == (
        f"Vertex group names are limited to {bones.MAX_BYTES} bytes."
    )


def test_validate_vtx_grp_rejects_an_empty_segment():
    assert (
        mesh_roles.validate_vtx_grp("susarm..L", REQUIRED)
        == "'susarm..L' has an empty segment."
    )


def test_validate_vtx_grp_rejects_a_pattern_matching_nothing():
    assert (
        mesh_roles.validate_vtx_grp("wheel.{1}", REQUIRED)
        == "'wheel.{1}' matches no required bone."
    )


# --- infer_vtx_grp ---------------------------------------------------------


def _reason(checked, required=REQUIRED):
    with pytest.raises(ValueError) as error:
        mesh_roles.infer_vtx_grp(checked, required)
    return str(error.value)


def test_infer_vtx_grp_one_bone_is_its_exact_name():
    assert mesh_roles.infer_vtx_grp(["susarm.rear.top.L"], REQUIRED) == (
        "susarm.rear.top.L"
    )


def test_infer_vtx_grp_frees_the_segments_that_differ():
    checked = ["susarm.front.top.R", "susarm.front.top.L"]
    assert mesh_roles.infer_vtx_grp(checked, REQUIRED) == "susarm.front.top.{1}"


def test_infer_vtx_grp_follows_required_order():
    checked = ["susarm.rear.top.L", "susarm.front.top.L"]
    assert mesh_roles.infer_vtx_grp(checked, REQUIRED) == "susarm.{1}.top.L"


def test_infer_vtx_grp_needs_a_checked_bone():
    assert _reason([]) == "Check at least one bone."


def test_infer_vtx_grp_rejects_a_mixed_base_or_length():
    assert _reason(["root", "susarm.front.top.L"]) == (
        "'root' and 'susarm.front.top.L' can't share one pattern."
    )


def test_infer_vtx_grp_rejects_over_the_byte_limit():
    required = ["a" + ".x" * 31, "a" + ".y" * 31]
    assert _reason(required, required) == (
        f"Vertex group names are limited to {bones.MAX_BYTES} bytes."
    )


def test_infer_vtx_grp_names_the_bones_it_would_also_match():
    assert _reason(["susarm.front.top.R", "susarm.rear.top.L"]) == (
        "'susarm.{1}.top.{2}' would also match susarm.front.top.L."
    )
