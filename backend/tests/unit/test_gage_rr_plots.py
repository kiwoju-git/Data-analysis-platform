"""Independent saved six-panel summaries; no production ANOVA reference helper."""

import json
import math
import random
from copy import deepcopy

import numpy as np
import pytest
from pydantic import ValidationError

from app.api.v1.schemas.gage_rr_plots import GageRrPlotBundle, validate_gage_rr_plot_result
from app.statistics.gage_rr import calculate_gage_rr_anova
from app.statistics.gage_rr_data import GageRrColumn, prepare_gage_data
from app.statistics.gage_rr_plots import build_gage_rr_plot_bundle


def column(name, index):
    return GageRrColumn(
        name,
        index,
        name,
        "decimal" if index == 2 else "text",
        "unknown",
        "unspecified",
        "mm" if index == 2 else None,
    )


def observations(*, repeats=2, interaction=0, parts=10, zero_within=False):
    return [
        [
            f"part-{i:03}",
            f"operator-{j + 1}",
            str(
                50
                + 2 * i
                + 0.2 * j
                + interaction * (i - (parts - 1) / 2) * j
                + (0 if zero_within else (k - (repeats - 1) / 2) * 0.2)
            ),
            f"repeat-{k}",
        ]
        for i in range(parts)
        for j in (-1, 0, 1)
        for k in range(repeats)
    ]


def calculate(rows, *, policy="retain", explicit=False, source_row_numbers=None):
    return calculate_gage_rr_anova(
        rows,
        measurement_column=column("measurement", 2),
        part_column=column("part", 0),
        operator_column=column("operator", 1),
        replicate_column=column("replicate", 3) if explicit else None,
        replicate_mode="explicit_column" if explicit else "infer_from_rows",
        interaction_policy=policy,
        source_row_numbers=source_row_numbers,
    )


@pytest.mark.parametrize(
    "policy,mse,halfwidth,df",
    [("retain", 0.02, 0.3, 30), ("auto_pool", 0.0125, 3 * math.sqrt(0.0125 / 2), 48)],
)
def test_hand_checked_60_rows_plot_values_follow_selected_anova(policy, mse, halfwidth, df):
    result = calculate(observations(), policy=policy)
    bundle = result["plot_bundle"]
    GageRrPlotBundle.model_validate(bundle)
    assert result["schema_version"] == 3
    assert bundle["counts"]["n_used"] == 60
    assert bundle["dispersion"]["statistic"] == "range"
    assert bundle["dispersion"]["center"] == pytest.approx(0.2, abs=1e-12)
    assert bundle["dispersion"]["lower_limit"] == 0
    assert bundle["dispersion"]["upper_limit"] == pytest.approx(0.6534, abs=1e-12)
    assert bundle["dispersion"]["constants"]["D4"] == 3.267
    assert bundle["xbar"]["center"] == pytest.approx(59)
    assert bundle["xbar"]["repeatability_variance"] == pytest.approx(mse, abs=1e-12)
    assert bundle["xbar"]["upper_limit"] == pytest.approx(59 + halfwidth)
    assert bundle["xbar"]["lower_limit"] == pytest.approx(59 - halfwidth)
    error = next(row for row in result["anova_table"] if row["source"] == "repeatability")
    assert error["degrees_of_freedom"] == df
    assert error["sum_of_squares"] == pytest.approx(0.6, abs=1e-12)
    assert bundle["interaction"]["interaction_pooled"] is (policy == "auto_pool")
    assert bundle["interaction"]["points"][0]["mean"] == pytest.approx(49.8)
    assert bundle["cells"][0]["sample_sd"] == pytest.approx(math.sqrt(0.02))
    assert bundle["measurement"]["unit"] == "mm"
    assert "part-000" not in json.dumps(bundle)
    assert "operator-0" not in json.dumps(bundle)


def test_component_percentages_are_copied_not_scaled_or_normalized():
    result = calculate(observations())
    items = result["plot_bundle"]["components"]["items"]
    for item in items:
        expected = result["variance_components"][item["component"]]
        for key in (
            "percent_contribution",
            "percent_study_variation",
            "final_variance",
            "standard_deviation",
        ):
            assert item[key] == expected[key]
    assert sum(item["percent_study_variation"] for item in items) > 100


def test_operator_boxplot_uses_every_measurement_not_cell_means():
    rows = observations()
    bundle = calculate(rows)["plot_bundle"]
    for index, box in enumerate(bundle["response_by_operator"]["boxes"]):
        values = np.array([float(row[2]) for row in rows if row[1] == f"operator-{index}"])
        assert box["n"] == 20
        assert [box["q1"], box["median"], box["q3"]] == pytest.approx(
            np.quantile(values, [0.25, 0.5, 0.75], method="linear")
        )
        assert box["mean"] == pytest.approx(values.mean())
        assert box["lower_whisker"] == values.min()
        assert box["upper_whisker"] == values.max()
        means = values.reshape(10, 2).mean(axis=1)
        assert box["q1"] != pytest.approx(np.quantile(means, 0.25), abs=1e-5)


@pytest.mark.parametrize("repeats", [3, 9])
def test_range_and_s_constants_match_independent_formula(repeats):
    from scipy.special import gamma

    bundle = calculate(observations(repeats=repeats))["plot_bundle"]
    plot = bundle["dispersion"]
    if repeats == 3:
        assert plot["statistic"] == "range"
        assert plot["center"] == pytest.approx(0.4)
        assert plot["upper_limit"] == pytest.approx(2.574 * 0.4)
    else:
        deviations = np.arange(9) * 0.2 - 0.8
        c4 = math.sqrt(2 / 8) * gamma(9 / 2) / gamma(8 / 2)
        spread = 3 * math.sqrt(1 - c4**2) / c4
        assert plot["statistic"] == "sample_sd"
        assert plot["center"] == pytest.approx(np.std(deviations, ddof=1))
        assert plot["constants"]["c4"] == pytest.approx(c4, rel=1e-13)
        assert plot["lower_limit"] == pytest.approx((1 - spread) * np.std(deviations, ddof=1))
        assert plot["upper_limit"] == pytest.approx((1 + spread) * np.std(deviations, ddof=1))
    GageRrPlotBundle.model_validate(bundle)


def test_strong_interaction_unchanged_actual_cell_means_and_zero_within_notice():
    strong = calculate(observations(interaction=2), policy="auto_pool")
    assert strong["interaction_selection"]["pooled"] is False
    assert strong["plot_bundle"]["interaction"]["points"][0]["mean"] == pytest.approx(58.8)
    zero = calculate(observations(zero_within=True), policy="auto_pool")["plot_bundle"]
    assert zero["dispersion"]["center"] == zero["dispersion"]["upper_limit"] == 0
    assert zero["dispersion"]["status"] == "available"
    assert zero["dispersion"]["warning_codes"] == ["within_cell_variation_zero"]
    assert zero["xbar"]["upper_limit"] == zero["xbar"]["lower_limit"] == 59
    assert zero["xbar"]["points"][0]["outside_repeatability_limits"] is True


@pytest.mark.parametrize("invalid_c4", [1.01, 0.0, float("inf")])
def test_s_chart_rejects_invalid_constant_without_hiding_anova(monkeypatch, invalid_c4):
    monkeypatch.setattr("app.statistics.gage_rr_plots.exp", lambda _: invalid_c4)
    result = calculate(observations(repeats=9))
    plot = result["plot_bundle"]["dispersion"]
    assert plot["status"] == "unavailable"
    assert plot["unavailable_reason"] == "invalid_dispersion_constant"
    assert plot["lower_limit"] is None and plot["upper_limit"] is None
    assert plot["constants"]["c4"] is None
    assert result["anova_table"]
    GageRrPlotBundle.model_validate(result["plot_bundle"])
    json.dumps(result, allow_nan=False)


def test_s_chart_only_accepts_roundoff_at_unit_constant_boundary(monkeypatch):
    monkeypatch.setattr("app.statistics.gage_rr_plots.exp", lambda _: math.nextafter(1.0, 2.0))
    plot = calculate(observations(repeats=9))["plot_bundle"]["dispersion"]
    assert plot["status"] == "available"
    assert plot["constants"]["c4"] == 1.0
    assert plot["lower_limit"] == plot["center"] == plot["upper_limit"]


def test_shuffle_explicit_inferred_and_long_private_identities_preserve_summaries():
    rows = observations()
    for row in rows:
        row[0] = "sensitive-part-" + "X" * 130 + row[0]
        row[1] = "sensitive-operator-" + "Y" * 130 + row[1]
    expected = calculate(rows)["plot_bundle"]
    indices = list(range(len(rows)))
    random.Random(17).shuffle(indices)
    actual = calculate(
        [rows[index] for index in indices],
        explicit=True,
        source_row_numbers=[index + 1 for index in indices],
    )["plot_bundle"]
    assert actual["cells"] == expected["cells"]
    assert actual["response_by_part"] == expected["response_by_part"]
    assert actual["response_by_operator"] == expected["response_by_operator"]
    assert actual["interaction"] == expected["interaction"]
    assert actual["counts"] == expected["counts"]
    assert "sensitive" not in json.dumps(actual)
    assert actual["counts"]["part_count"] == 10


def prepare(rows):
    return prepare_gage_data(
        rows,
        measurement_column=column("measurement", 2),
        part_column=column("part", 0),
        operator_column=column("operator", 1),
    )


def test_display_cap_is_cell_stratified_and_never_changes_full_summaries():
    rows = observations(parts=1000)
    result = calculate(rows)
    full = result["plot_bundle"]
    small = build_gage_rr_plot_bundle(
        prepare(rows),
        measurement_column=column("measurement", 2),
        variance_components=result["variance_components"],
        interaction_pooled=False,
        raw_point_limit=31,
    )
    assert full["counts"]["raw_point_count"] == 6000
    assert full["counts"]["displayed_raw_point_count"] == 5000
    assert full["counts"]["truncated"]
    assert (
        len({(p["part_index"], p["operator_index"]) for p in full["response_by_part"]["points"]})
        == 3000
    )
    for key in (
        "cells",
        "parts",
        "operators",
        "measurement_range",
        "components",
        "dispersion",
        "xbar",
        "interaction",
    ):
        assert small[key] == full[key]
    for left, right in zip(
        small["response_by_operator"]["boxes"], full["response_by_operator"]["boxes"], strict=True
    ):
        assert {
            key: value
            for key, value in left.items()
            if key not in ("outliers", "displayed_outlier_count")
        } == {
            key: value
            for key, value in right.items()
            if key not in ("outliers", "displayed_outlier_count")
        }
    GageRrPlotBundle.model_validate(full)
    GageRrPlotBundle.model_validate(small)


def test_box_outlier_counts_use_raw_measurements_and_original_rows():
    rows = observations(parts=20)
    rows[-1][2] = "1000"
    result = calculate(rows)
    box = result["plot_bundle"]["response_by_operator"]["boxes"][-1]
    assert box["outlier_count"] == box["displayed_outlier_count"] == 1
    assert box["outliers"][0]["source_row_number"] == len(rows)
    assert box["outliers"][0]["value"] == 1000
    assert box["upper_whisker"] < box["upper_fence"] < 1000
    capped = build_gage_rr_plot_bundle(
        prepare(rows),
        measurement_column=column("measurement", 2),
        variance_components=result["variance_components"],
        interaction_pooled=False,
        raw_point_limit=1,
    )
    capped_box = capped["response_by_operator"]["boxes"][-1]
    assert capped_box["outlier_count"] == 1
    assert capped_box["displayed_outlier_count"] == 0
    assert capped_box["q1"] == box["q1"]
    assert capped["measurement_range"]["maximum"] == 1000
    GageRrPlotBundle.model_validate(capped)


def test_complete_case_sample_counts_and_r8_boundary():
    rows = observations(repeats=8)
    rows.insert(10, ["part-000", "operator-0", ""])
    bundle = calculate(rows)["plot_bundle"]
    assert bundle["counts"]["n_total"] == 241
    assert bundle["counts"]["n_used"] == 240
    assert bundle["counts"]["n_excluded"] == 1
    assert bundle["dispersion"]["statistic"] == "range"
    assert bundle["dispersion"]["upper_limit"] == pytest.approx(1.864 * 1.4)
    assert 11 not in {point["source_row_number"] for point in bundle["response_by_part"]["points"]}


def test_observed_whisker_need_not_equal_interpolated_quartile():
    rows = [
        ["a", "a", "0"],
        ["a", "a", "100"],
        ["b", "a", "100"],
        ["b", "a", "100"],
        ["a", "b", "10"],
        ["a", "b", "11"],
        ["b", "b", "12"],
        ["b", "b", "13"],
    ]
    bundle = calculate(rows)["plot_bundle"]
    box = bundle["response_by_operator"]["boxes"][0]
    assert box["q1"] == 75
    assert box["lower_whisker"] == 100
    assert box["outlier_count"] == 1
    GageRrPlotBundle.model_validate(bundle)


def test_nonfinite_plot_summaries_are_explicit_null_without_nan_json():
    ordinary = calculate(observations())
    rows = [
        [f"p{p}", f"o{o}", str(value)]
        for p in range(2)
        for o in range(2)
        for value in (-1e308, 1e308)
    ]
    bundle = build_gage_rr_plot_bundle(
        prepare(rows),
        measurement_column=column("measurement", 2),
        variance_components=ordinary["variance_components"],
        interaction_pooled=False,
    )
    assert bundle["dispersion"]["status"] == "unavailable"
    assert bundle["dispersion"]["points"][0]["value"] is None
    assert bundle["response_by_operator"]["status"] == "unavailable"
    json.dumps(bundle, allow_nan=False)
    GageRrPlotBundle.model_validate(bundle)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda p: p["components"]["items"][0].update(percent_contribution=float("nan")),
        lambda p: p["components"]["items"][0].update(component="repeatability"),
        lambda p: p["components"]["items"][0].update(percent_contribution=None),
        lambda p: p["components"]["items"][0].update(percent_contribution=-1),
        lambda p: p["components"]["items"][0].update(final_variance=-1),
        lambda p: p["cells"][0].update(range=-1),
        lambda p: p["dispersion"].update(lower_limit=-1),
        lambda p: p["xbar"].update(repeatability_variance=-1),
        lambda p: p["xbar"].update(
            status="unavailable", unavailable_reason="raw private exception"
        ),
        lambda p: p["xbar"].update(upper_limit=None),
        lambda p: p["parts"][0].update(n=1),
        lambda p: p["response_by_operator"]["boxes"][0].update(q1=1000),
        lambda p: p["response_by_part"]["points"][0].update(part_index=999),
        lambda p: p["response_by_part"]["points"][0].update(value=True),
    ],
)
def test_malformed_available_bundle_is_rejected(mutation):
    bundle = calculate(observations())["plot_bundle"]
    mutation(bundle)
    with pytest.raises(ValidationError):
        GageRrPlotBundle.model_validate(bundle)


def test_result_relationship_validation_is_read_only_and_legacy_has_no_defaults():
    result = calculate(observations())
    original = json.dumps(result, sort_keys=True)
    validate_gage_rr_plot_result(result)
    assert json.dumps(result, sort_keys=True) == original
    changed = deepcopy(result)
    changed["plot_bundle"]["components"]["items"][0]["percent_contribution"] += 1
    with pytest.raises(ValueError, match="components_mismatch"):
        validate_gage_rr_plot_result(changed)
    for version in (1, 2):
        legacy = deepcopy(result)
        legacy["schema_version"] = version
        del legacy["plot_bundle"]
        payload = json.dumps(legacy, sort_keys=True)
        validate_gage_rr_plot_result(legacy)
        assert json.dumps(legacy, sort_keys=True) == payload


def test_plot_builder_is_called_once_with_the_already_prepared_observations(monkeypatch):
    calls = []

    def observed_builder(prepared, **kwargs):
        calls.append(prepared)
        return build_gage_rr_plot_bundle(prepared, **kwargs)

    monkeypatch.setattr("app.statistics.gage_rr.build_gage_rr_plot_bundle", observed_builder)
    result = calculate(iter(observations()), policy="auto_pool")
    assert len(calls) == 1
    assert len(calls[0].observations) == result["sample"]["n_used"] == 60
    assert result["plot_bundle"]["calculation_metadata"]["selected_interaction_policy"] == "pooled"
