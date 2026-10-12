"""Unit tests for parenting patterns (blender_buddy.specs.parenting)."""

import pytest

from blender_buddy.specs import parenting

INVERSES = {
    ".front": ".rear",
    ".rear": ".front",
    ".top": ".bottom",
    ".bottom": ".top",
    ".body": ".wheel",
    ".wheel": ".body",
}
CORNERS = ["front.L", "front.R", "rear.L", "rear.R"]
SUSARMS = [
    f"susarm.{c.split('.')[0]}.{h}.{c.split('.')[1]}"
    for c in CORNERS
    for h in ("top", "bottom")
]
REQUIRED = [
    "root",
    *(f"wheel.{c}" for c in CORNERS),
    *(f"axle.{c}" for c in CORNERS),
    *SUSARMS,
    *(f"shockmount.body.{c}" for c in CORNERS),
    *(f"shockmount.wheel.{c}" for c in CORNERS),
]


def _infer(parent, children, existing=None):
    return parenting.infer(parent, children, REQUIRED, INVERSES, existing or {})


# --- match -----------------------------------------------------------------


def test_match_literal():
    assert parenting.match("root", "root") == {}
    assert parenting.match("root", "rooty") is None


def test_match_binds_one_whole_segment_per_placeholder():
    assert parenting.match("axle.{1}.{2}", "axle.front.L") == {
        "{1}": "front",
        "{2}": "L",
    }


def test_match_needs_the_same_segment_count():
    assert parenting.match("axle.{1}", "axle.front.L") is None
    assert parenting.match("axle.{1}.{2}", "axle.L") is None


def test_match_honours_bound_values():
    assert (
        parenting.match("wheel.{1}.{2}", "wheel.front.L", {"{1}": "front"}) is not None
    )
    assert parenting.match("wheel.{1}.{2}", "wheel.rear.L", {"{1}": "front"}) is None


def test_match_repeated_placeholder_must_agree():
    assert parenting.match("a.{1}.{1}", "a.x.x") == {"{1}": "x"}
    assert parenting.match("a.{1}.{1}", "a.x.y") is None


def test_match_base_is_always_literal():
    assert parenting.match("{1}.L", "arm.L") is None


def test_has_placeholder_segment():
    assert parenting.has_placeholder_segment("arm.{1}")
    assert not parenting.has_placeholder_segment("arm.L")


# --- resolve / ancestors / is_valid / merge ---------------------------------


def test_resolve_pairs_each_mirror_with_its_own_child():
    resolved = parenting.resolve({"axle.{1}.{2}": ["wheel.{1}.{2}"]}, REQUIRED)
    assert resolved == {f"wheel.{c}": [f"axle.{c}"] for c in CORNERS}


def test_resolve_free_placeholders_match_independently():
    resolved = parenting.resolve({"root": ["susarm.{1}.{2}.{3}"]}, REQUIRED)
    assert sorted(resolved) == sorted(SUSARMS)


def test_resolve_ignores_other_syntaxes():
    assert parenting.resolve({"axle.*": ["wheel.*"]}, REQUIRED) == {}


def test_ancestors_walks_up():
    resolved = {"wheel.front.L": ["axle.front.L"], "axle.front.L": ["root"]}
    assert parenting.ancestors("wheel.front.L", resolved) == {"axle.front.L", "root"}
    assert parenting.ancestors("root", resolved) == set()


def test_is_valid_rejects_two_parents_and_cycles():
    assert parenting.is_valid({"root": ["axle.front.L"]}, REQUIRED)
    assert not parenting.is_valid(
        {"root": ["axle.front.L"], "wheel.front.L": ["axle.front.L"]}, REQUIRED
    )
    assert not parenting.is_valid(
        {"root": ["axle.front.L"], "axle.front.L": ["root"]}, REQUIRED
    )
    assert not parenting.is_valid({"root": ["root"]}, REQUIRED)


def test_merge_appends_dedupes_and_copies():
    existing = {"root": ["a"]}
    merged = parenting.merge(existing, {"root": ["a", "b", "b"], "x": ["y"]})
    assert merged == {"root": ["a", "b"], "x": ["y"]}
    assert existing == {"root": ["a"]}


# --- infer: the plan's worked examples --------------------------------------


def test_infer_mirrors_the_parent():
    entries = _infer("axle.front.L", ["wheel.front.L", "shockmount.wheel.front.L"])
    assert entries == {"axle.{1}.{2}": ["wheel.{1}.{2}", "shockmount.wheel.{1}.{2}"]}
    assert len(parenting.pairs(entries, REQUIRED)) == 8


def test_infer_binds_by_value_not_position():
    entries = _infer("susarm.front.top.L", ["shockmount.wheel.front.L"])
    assert entries == {"susarm.{1}.top.{2}": ["shockmount.wheel.{1}.{2}"]}
    assert len(parenting.pairs(entries, REQUIRED)) == 4


def test_infer_collapses_a_whole_family():
    assert _infer("root", SUSARMS) == {"root": ["susarm.{1}.{2}.{3}"]}


def test_infer_keeps_a_partial_family_exact():
    entries = _infer("root", ["susarm.front.top.L", "susarm.rear.bottom.R"])
    assert entries == {"root": ["susarm.front.top.L", "susarm.rear.bottom.R"]}


def test_infer_falls_back_to_exact_on_a_mirror_conflict():
    entries = _infer("axle.front.L", ["wheel.front.L"], {"root": ["wheel.rear.R"]})
    assert entries == {"axle.front.L": ["wheel.front.L"]}


# --- infer: edges ------------------------------------------------------------


def test_infer_falls_back_to_exact_on_a_would_be_cycle():
    existing = {"axle.rear.R": ["wheel.rear.R"]}
    entries = _infer("wheel.front.L", ["axle.front.L"], existing)
    assert entries == {"wheel.front.L": ["axle.front.L"]}


def test_infer_groups_children_under_mixed_keys():
    entries = _infer("axle.front.L", ["root", "wheel.front.L"])
    assert entries == {"axle.front.L": ["root"], "axle.{1}.{2}": ["wheel.{1}.{2}"]}


def test_infer_leaves_unmapped_segments_literal():
    required = ["hub.x.L", "cap.x.L", "hub.x.R", "cap.x.R"]
    entries = parenting.infer("hub.x.L", ["cap.x.L"], required, {}, {})
    assert entries == {"hub.x.{1}": ["cap.x.{1}"]}


@pytest.mark.parametrize("existing", [{}, {"axle.{1}.{2}": ["wheel.{1}.{2}"]}])
def test_infer_merges_into_an_existing_key(existing):
    entries = _infer("axle.front.L", ["shockmount.wheel.front.L"], existing)
    merged = parenting.merge(existing, entries)
    assert list(merged) == ["axle.{1}.{2}"]
    assert merged["axle.{1}.{2}"][-1] == "shockmount.wheel.{1}.{2}"
