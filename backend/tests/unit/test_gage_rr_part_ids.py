"""Part display identity regressions; grouping and ANOVA arithmetic stay unchanged."""

import hashlib
import json
import random
from copy import deepcopy
from pathlib import Path

import pytest

from app.api.v1.schemas.gage_rr_plots import validate_gage_rr_plot_result
from app.statistics.gage_part_order import natural_part_id_key
from app.statistics.gage_rr import calculate_gage_rr_anova
from app.statistics.gage_rr_data import GageRrColumn


def rows(part_ids=None):
    identities = part_ids or [str(index) for index in range(1, 11)]
    return [
        [part_id, f"private-operator-{operator}", str(50 + 2 * index + 0.2 * operator + error)]
        for index, part_id in enumerate(identities)
        for operator in (-1, 0, 1)
        for error in (-0.1, 0.1)
    ]


def calculate(data, policy="retain"):
    def column(name, index):
        return GageRrColumn(
            name, index, name, "decimal" if index == 2 else "text", "unknown", "unspecified", None
        )

    return calculate_gage_rr_anova(
        data,
        measurement_column=column("measurement", 2),
        part_column=column("part", 0),
        operator_column=column("operator", 1),
        replicate_column=None,
        replicate_mode="infer_from_rows",
        interaction_policy=policy,
    )


@pytest.mark.parametrize("policy", ["retain", "auto_pool"])
def test_numeric_original_ids_follow_natural_order_with_every_cell_and_raw_row(policy):
    data = rows()
    result = calculate(data, policy)
    bundle = result["plot_bundle"]
    assert [part.get("part_id") for part in bundle["parts"]] == [str(i) for i in range(1, 11)]
    assert [part["part_index"] for part in bundle["parts"]] == list(range(10))
    assert [part["mean"] for part in bundle["parts"]] == pytest.approx(list(range(50, 70, 2)))
    assert len(bundle["cells"]) == 30
    assert len(bundle["response_by_part"]["points"]) == 60
    ids = {part["part_index"]: part["part_id"] for part in bundle["parts"]}
    for point in bundle["response_by_part"]["points"]:
        original = data[point["source_row_number"] - 1]
        assert ids[point["part_index"]] == original[0]
        assert point["value"] == float(original[2])
    for group in (bundle["cells"], bundle["interaction"]["points"], bundle["xbar"]["points"]):
        for point in group:
            expected = (
                50 + 2 * (int(ids[point["part_index"]]) - 1) + 0.2 * (point["operator_index"] - 1)
            )
            assert point.get("mean", point.get("value")) == pytest.approx(expected)
    assert result["schema_version"] == 4 and bundle["schema_version"] == 2
    assert "private-operator" not in json.dumps(result)
    original = deepcopy(result)
    validate_gage_rr_plot_result(result)
    assert result == original


@pytest.mark.parametrize(
    "policy,baseline_sha",
    [
        ("retain", "37c2dabf1e30dfa2a7675da32c08cf4bd35a52a916044b7ff3c9704998902356"),
        ("auto_pool", "c84b1548650c8ba517d8a2bfc7f196a2d2ea9915ef06bd5c9269d810db4b1648"),
    ],
)
def test_statistical_payload_is_byte_identical_to_pre_identity_fix(policy, baseline_sha):
    # Captured from BASE21ccddc on the same deterministic inputs before this display fix.
    # This is a regression fingerprint, not an independent statistical reference.
    result = calculate(rows(), policy)
    keys = (
        "sample",
        "design",
        "anova_table",
        "full_anova_table",
        "reduced_anova_table",
        "interaction_selection",
        "variance_components",
    )
    encoded = json.dumps(
        {key: result[key] for key in keys}, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    assert hashlib.sha256(encoded).hexdigest() == baseline_sha


@pytest.mark.parametrize(
    "values,expected",
    [
        (["10", "2", "1", "01"], ["01", "1", "2", "10"]),
        (["P10", "P2", "P1"], ["P1", "P2", "P10"]),
        (["a2b10", "a02b2", "a2b2"], ["a02b2", "a2b2", "a2b10"]),
        (["부품10", "부품2", "부품1"], ["부품1", "부품2", "부품10"]),
        (["A2", "a1", "A10"], ["A2", "A10", "a1"]),
        (["2", "１", "1"], ["1", "2", "１"]),
    ],
)
def test_natural_order_uses_ascii_digit_runs_without_group_identity_coercion(values, expected):
    assert sorted(values, key=natural_part_id_key) == expected


def test_long_digit_runs_do_not_require_integer_or_float_parsing():
    shorter, longer = "9" * 5000, "1" + "0" * 5000
    assert sorted([longer, shorter], key=natural_part_id_key) == [shorter, longer]


def test_full_stripped_ids_survive_shuffle_and_never_relabel_groups():
    ids = [
        "1",
        "01",
        " P10 ",
        "P2",
        "부품" + "X" * 130 + "10",
        "부품" + "X" * 130 + "2",
        '<svg onload="alert(1)">10</svg>',
        "original...",
    ]
    data = rows(ids)
    result = calculate(data)
    shuffled = deepcopy(data)
    random.Random(17).shuffle(shuffled)
    other = calculate(shuffled)
    expected = sorted([value.strip() for value in ids], key=natural_part_id_key)
    assert [part["part_id"] for part in result["plot_bundle"]["parts"]] == expected
    assert other["plot_bundle"]["parts"] == result["plot_bundle"]["parts"]
    assert result["design"]["part_count"] == len(ids)
    assert "private-operator" not in json.dumps(result)
    assert "gage_rr_operator_replicate_labels_redacted" in result["warnings"]
    assert "gage_rr_labels_redacted" not in result["warnings"]
    validate_gage_rr_plot_result(result)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda b: b["parts"][0].pop("part_id"),
        lambda b: b["parts"][0].update(part_id=None),
        lambda b: b["parts"][0].update(part_id=""),
        lambda b: b["parts"][0].update(part_id=" 1 "),
        lambda b: b["parts"][0].update(part_id=1),
        lambda b: b["parts"][0].update(part_id=True),
        lambda b: b["parts"][0].update(part_id=b["parts"][1]["part_id"]),
        lambda b: b["parts"][0].update(part_id="99"),
        lambda b: b["calculation_metadata"].update(policy_version="gage_rr_six_panel_v1"),
        lambda b: b["calculation_metadata"].update(part_order="sorted_full_stripped_identity"),
        lambda b: b["calculation_metadata"].update(
            identifier_policy="zero_based_indices_original_labels_redacted"
        ),
        lambda b: b.update(schema_version=1),
    ],
)
def test_current_schema_rejects_missing_ambiguous_or_mismatched_identity(mutation):
    result = calculate(rows())
    mutation(result["plot_bundle"])
    with pytest.raises(ValueError):
        validate_gage_rr_plot_result(result)


def test_saved_legacy_result_bytes_and_missing_ids_remain_unchanged():
    fixture = Path(__file__).resolve().parents[3] / "tests/fixtures/gage_rr_six_panel.json"
    original_bytes = fixture.read_bytes()
    result = json.loads(original_bytes)["retain"]
    assert result["schema_version"] == 3 and result["plot_bundle"]["schema_version"] == 1
    assert all("part_id" not in part for part in result["plot_bundle"]["parts"])
    for version in (1, 2, 3):
        saved = deepcopy(result)
        saved["schema_version"] = version
        if version < 3:
            saved.pop("plot_bundle")
        snapshot = json.dumps(saved, sort_keys=True)
        validate_gage_rr_plot_result(saved)
        assert json.dumps(saved, sort_keys=True) == snapshot
    assert fixture.read_bytes() == original_bytes
    result["plot_bundle"]["parts"][0]["part_id"] = "fabricated"
    with pytest.raises(ValueError):
        validate_gage_rr_plot_result(result)


def test_result_version_must_match_bundle_version():
    result = calculate(rows())
    result["schema_version"] = 3
    with pytest.raises(ValueError, match="gage_plot_result_schema_mismatch"):
        validate_gage_rr_plot_result(result)
