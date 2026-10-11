"""Unit tests for bone-name segments and inverses (blender_buddy.specs.bones)."""

import pytest

from blender_buddy.specs import bones

FRONT_REAR = {".front": ".rear", ".rear": ".front"}
TOP_BOTTOM = {".top": ".bottom", ".bottom": ".top"}

# --- split / validate_name -------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("body", ("body", ())),
        ("arm.L", ("arm", (".L",))),
        ("susarm.front.top.L", ("susarm", (".front", ".top", ".L"))),
    ],
)
def test_split(name, expected):
    assert bones.split(name) == expected


@pytest.mark.parametrize("name", ["body", "wheel.front.L", "a" * bones.MAX_BYTES])
def test_validate_name_accepts_usable_names(name):
    assert bones.validate_name(name) is None


def test_validate_name_rejects_empty():
    assert bones.validate_name("") == "Enter a bone name."


def test_validate_name_counts_bytes_not_characters():
    assert bones.validate_name("a" * (bones.MAX_BYTES + 1)) is not None
    # 32 two-byte characters is 64 bytes, though only 32 characters.
    assert bones.validate_name("é" * 32) is not None


@pytest.mark.parametrize("name", ["a..b", ".L", "a.", "."])
def test_validate_name_rejects_empty_segments(name):
    assert "empty segment" in bones.validate_name(name)


# --- next_missing ----------------------------------------------------------


def test_next_missing_skips_builtins_and_known():
    assert bones.next_missing("body", {}) is None
    assert bones.next_missing("arm.L", {}) is None
    assert bones.next_missing("wheel.front.L", {}) == ".front"
    assert bones.next_missing("wheel.front.L", FRONT_REAR) is None


def test_next_missing_returns_segments_in_order():
    assert bones.next_missing("susarm.front.top.L", {}) == ".front"
    assert bones.next_missing("susarm.front.top.L", FRONT_REAR) == ".top"


def test_next_missing_is_lazy_so_one_answer_covers_its_inverse():
    known = bones.pairs(".front", ".rear")
    assert bones.next_missing("a.front.rear", known) is None


def test_next_missing_treats_self_mapping_as_known():
    assert bones.next_missing("a.tip", {".tip": ".tip"}) is None


# --- normalize_inverse / validate_inverse ----------------------------------


@pytest.mark.parametrize(
    ("answer", "expected"),
    [("rear", ".rear"), (".rear", ".rear"), ("  rear ", ".rear"), ("", ""), ("  ", "")],
)
def test_normalize_inverse(answer, expected):
    assert bones.normalize_inverse(answer) == expected


@pytest.mark.parametrize("answer", [".rear", "rear", "", "   "])
def test_validate_inverse_accepts(answer):
    assert bones.validate_inverse(".front", answer, {}) is None


@pytest.mark.parametrize("answer", [".a.b", "a.b", "."])
def test_validate_inverse_rejects_more_than_one_segment(answer):
    assert "single segment" in bones.validate_inverse(".front", answer, {})


@pytest.mark.parametrize("answer", [".L", "R"])
def test_validate_inverse_rejects_builtins(answer):
    assert "reserved" in bones.validate_inverse(".front", answer, {})


def test_validate_inverse_rejects_the_segment_itself():
    assert "blank" in bones.validate_inverse(".front", "front", {})


def test_validate_inverse_rejects_an_answer_paired_elsewhere():
    reason = bones.validate_inverse(".front", ".bottom", TOP_BOTTOM)
    assert reason == "'.bottom' is already paired with '.top'."


def test_validate_inverse_rejects_an_answer_recorded_as_self_mapped():
    reason = bones.validate_inverse(".front", ".tip", {".tip": ".tip"})
    assert "no inverse" in reason


# --- pairs -----------------------------------------------------------------


def test_pairs_writes_both_directions():
    assert bones.pairs(".front", "rear") == FRONT_REAR


@pytest.mark.parametrize("answer", ["", "  "])
def test_pairs_self_maps_a_blank_answer(answer):
    assert bones.pairs(".tip", answer) == {".tip": ".tip"}


# --- variants --------------------------------------------------------------


def test_variants_order_matches_product_order():
    assert bones.variants("wheel.front.L", FRONT_REAR) == [
        "wheel.front.R",
        "wheel.rear.L",
        "wheel.rear.R",
    ]


@pytest.mark.parametrize(
    ("name", "expected_count"),
    [("arm.L", 1), ("wheel.front.L", 3), ("susarm.front.top.L", 7)],
)
def test_variants_count_is_two_to_the_n_minus_one(name, expected_count):
    known = {**FRONT_REAR, **TOP_BOTTOM}
    result = bones.variants(name, known)
    assert len(result) == expected_count
    assert name not in result
    assert len(set(result)) == expected_count


def test_variants_full_chain():
    assert bones.variants("susarm.front.top.L", {**FRONT_REAR, **TOP_BOTTOM}) == [
        "susarm.front.top.R",
        "susarm.front.bottom.L",
        "susarm.front.bottom.R",
        "susarm.rear.top.L",
        "susarm.rear.top.R",
        "susarm.rear.bottom.L",
        "susarm.rear.bottom.R",
    ]


def test_variants_self_mapped_segments_add_nothing():
    assert bones.variants("a.tip.L", {".tip": ".tip"}) == ["a.tip.R"]
    assert bones.variants("a.tip", {".tip": ".tip"}) == []
    assert bones.variants("body", {}) == []


@pytest.mark.parametrize(
    ("name", "known"),
    [("wheel.front.L", {}), ("susarm.front.top.L", FRONT_REAR)],
)
def test_variants_refuses_a_partial_chain(name, known):
    with pytest.raises(ValueError):
        bones.variants(name, known)
