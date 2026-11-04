"""Part display identity regressions; grouping and ANOVA arithmetic stay unchanged."""

import json
import random
from copy import deepcopy
from math import floor, gamma, sqrt, ulp
from pathlib import Path

import pytest
from scipy.integrate import quad

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


@pytest.mark.parametrize("policy", ["retain", "auto_pool"])
def test_plot_order_isolated_from_statistical_payload_in_same_runtime(policy, monkeypatch):
    # Compare the display policies in one runtime, not a Windows float JSON hash
    # against a different Python/libm/SciPy build. This is an isolation regression,
    # not an independent reference or a copy of the previous calculation engine.
    natural = calculate(rows(), policy)
    monkeypatch.setattr("app.statistics.gage_rr_plots.natural_part_id_key", lambda value: value)
    lexical = calculate(rows(), policy)
    assert [part["part_id"] for part in natural["plot_bundle"]["parts"]][:3] == ["1", "2", "3"]
    assert [part["part_id"] for part in lexical["plot_bundle"]["parts"]][:3] == ["1", "10", "2"]
    keys = (
        "sample",
        "design",
        "anova_table",
        "full_anova_table",
        "reduced_anova_table",
        "interaction_selection",
        "variance_components",
    )

    def encoded(result):
        return json.dumps(
            {key: result[key] for key in keys},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()

    assert encoded(natural) == encoded(lexical)


@pytest.mark.parametrize("policy", ["retain", "auto_pool"])
def test_identity_fixture_matches_independent_balanced_anova_algebra(policy):
    # y=50+2*i+0.2*j+e, i=0..9, j=-1..1, e=+-0.1. Orthogonal effects give
    # SS=(6*4*82.5, 20*0.04*2, 0, 60*0.01). No production helper is a reference.
    result = calculate(rows(), policy)
    ss = {
        "part": 1980.0,
        "operator": 1.6,
        "part_operator": 0.0,
        "repeatability": 0.6,
        "total": 1982.2,
    }
    dfs = {"part": 9, "operator": 2, "part_operator": 18, "repeatability": 30, "total": 59}
    # At most 60 additions of squared deviations below 2048; this conservative
    # absolute roundoff budget remains below the existing 1e-10 ANOVA reference gate.
    ss_roundoff = 60 * ulp(2048.0)
    full = {row["source"]: row for row in result["full_anova_table"]}
    for source, row in full.items():
        assert row["degrees_of_freedom"] == dfs[source]
        assert row["sum_of_squares"] == pytest.approx(ss[source], rel=0, abs=ss_roundoff)
        if source != "total":
            assert row["mean_square"] == pytest.approx(
                ss[source] / dfs[source], rel=0, abs=ss_roundoff / dfs[source]
            )
    assert full["part_operator"]["sum_of_squares"] == 0
    assert full["part_operator"]["p_value"] == 1
    assert full["part"]["p_value"] is None and full["operator"]["p_value"] is None
    pooled = policy == "auto_pool"
    error = 0.6 / (48 if pooled else 30)
    comparison = error if pooled else 0.0
    expected = {
        "repeatability": error,
        "operator": (0.8 - comparison) / 20,
        "part_operator": 0.0 if pooled else -0.01,
        "part_to_part": (220 - comparison) / 6,
    }
    expected["reproducibility"] = expected["operator"]
    expected["total_gage_rr"] = error + expected["operator"]
    expected["total_variation"] = expected["total_gage_rr"] + expected["part_to_part"]
    components = result["variance_components"]
    for name, raw in expected.items():
        item = components[name]
        final = max(raw, 0)
        for key, value in {
            "raw_variance": raw,
            "final_variance": final,
            "standard_deviation": sqrt(final),
            "study_variation": 6 * sqrt(final),
            "percent_contribution": 100 * final / expected["total_variation"],
            "percent_study_variation": 100 * sqrt(final / expected["total_variation"]),
        }.items():
            assert item[key] == pytest.approx(value, rel=1e-12, abs=1e-14)
        assert item["clamped_to_zero"] is (raw < 0)
    assert components["ndc"] == floor(
        1.41 * sqrt(expected["part_to_part"] / expected["total_gage_rr"])
    )
    final = {row["source"]: row for row in result["anova_table"]}
    assert final["repeatability"]["degrees_of_freedom"] == (48 if pooled else 30)
    assert final["repeatability"]["mean_square"] == pytest.approx(error, rel=1e-12)
    if pooled:
        assert final["part"]["f_statistic"] == pytest.approx(17600, rel=1e-12)
        assert final["operator"]["f_statistic"] == pytest.approx(64, rel=1e-12)
        # F(2,48) survival has this closed form. F(9,48) uses independently
        # integrated beta density, scaled to [0,1] to resolve its small tail.
        x = 48 / (48 + 9 * 17600)
        integral, _ = quad(lambda u: u**23 * (1 - x * u) ** 3.5, 0, 1, epsabs=1e-14, epsrel=1e-13)
        part_p = x**24 * integral * gamma(28.5) / (gamma(24) * gamma(4.5))
        assert final["part"]["p_value"] == pytest.approx(part_p, rel=1e-12, abs=0)
        assert final["operator"]["p_value"] == pytest.approx((3 / 11) ** 24, rel=1e-12, abs=0)
    fixture = Path(__file__).resolve().parents[3] / "tests/fixtures/gage_rr_part_ids.json"
    saved = json.loads(fixture.read_bytes())[policy]
    for key in ("sample", "design", "interaction_selection"):
        assert result[key] == saved[key]


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
