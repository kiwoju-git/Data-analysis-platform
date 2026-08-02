from __future__ import annotations

import json
from pathlib import Path

import pytest
from scipy import stats  # type: ignore[import-untyped]

from app.statistics.one_way_anova import (
    OneWayAnovaError,
    OneWayAnovaGroupColumn,
    OneWayAnovaResponseColumn,
    calculate_one_way_anova,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "reference" / "fixtures"


def test_one_way_anova_is_hand_checkable_for_balanced_groups() -> None:
    rows = [
        ["8", "A"],
        ["9", "A"],
        ["6", "A"],
        ["7", "A"],
        ["10", "B"],
        ["12", "B"],
        ["9", "B"],
        ["11", "B"],
        ["13", "C"],
        ["14", "C"],
        ["12", "C"],
        ["15", "C"],
    ]

    result = calculate_one_way_anova(rows, _response_column(), _group_column())

    assert result["summary_type"] == "one_way_anova"
    assert result["method"] == "standard_one_way_anova"
    assert result["n_total"] == 12
    assert result["n_used"] == 12
    assert [group["group_label"] for group in result["groups"]] == ["A", "B", "C"]
    assert [group["n"] for group in result["groups"]] == [4, 4, 4]
    assert [group["mean"] for group in result["groups"]] == [7.5, 10.5, 13.5]
    anova_table = result["anova_table"]
    assert anova_table["ss_between"] == pytest.approx(72.0, abs=1e-12)
    assert anova_table["ss_within"] == pytest.approx(15.0, abs=1e-12)
    assert anova_table["ss_total"] == pytest.approx(87.0, abs=1e-12)
    assert anova_table["df_between"] == 2
    assert anova_table["df_within"] == 9
    assert anova_table["ms_between"] == pytest.approx(36.0, abs=1e-12)
    assert anova_table["ms_within"] == pytest.approx(1.6666666666666667, abs=1e-12)
    assert result["test"]["f_statistic"] == pytest.approx(21.6, abs=1e-12)
    assert result["test"]["p_value"] == pytest.approx(0.000366922233939463, abs=1e-12)
    assert result["test"]["effect_size"]["eta_squared"] == pytest.approx(
        0.8275862068965517,
        abs=1e-12,
    )
    assert result["test"]["effect_size"]["omega_squared"] == pytest.approx(
        0.7744360902255639,
        abs=1e-12,
    )
    assert result["posthoc"]["performed"] is True
    assert len(result["posthoc"]["comparisons"]) == 3
    assert result["posthoc"]["comparisons"][0]["adjusted_p_value"] == pytest.approx(
        0.0231730044120374,
        abs=1e-12,
    )
    assert "one_way_anova_not_auto_switched" in result["warnings"]
    assert "tukey_kramer_after_standard_anova" in result["warnings"]


def test_one_way_anova_matches_reference_fixture_and_scipy_f_oneway() -> None:
    input_payload = json.loads((FIXTURE_DIR / "one_way_anova_input.json").read_text())
    reference_payload = json.loads(
        (FIXTURE_DIR / "one_way_anova_scipy_reference.json").read_text(),
    )
    references = {reference["case_id"]: reference for reference in reference_payload["cases"]}

    for case in input_payload["cases"]:
        expected = references[case["case_id"]]
        result = calculate_one_way_anova(
            case["rows"],
            _response_column(),
            _group_column(),
            alpha=case["alpha"],
            confidence_level=case["confidence_level"],
            posthoc_policy="after_significant",
        )
        grouped_values: dict[str, list[float]] = {}
        for response, group in case["rows"]:
            grouped_values.setdefault(group, []).append(float(response))
        scipy_result = stats.f_oneway(*grouped_values.values())

        assert result["method"] == expected["method"]
        assert [group["group_label"] for group in result["groups"]] == expected["group_labels"]
        assert [group["n"] for group in result["groups"]] == expected["group_ns"]
        for group, expected_mean in zip(
            result["groups"],
            expected["group_means"],
            strict=True,
        ):
            assert group["mean"] == pytest.approx(expected_mean, abs=1e-12)
        anova_table = result["anova_table"]
        assert anova_table["ss_between"] == pytest.approx(expected["ss_between"], abs=1e-12)
        assert anova_table["ss_within"] == pytest.approx(expected["ss_within"], abs=1e-12)
        assert anova_table["ss_total"] == pytest.approx(expected["ss_total"], abs=1e-12)
        assert anova_table["df_between"] == expected["df_between"]
        assert anova_table["df_within"] == expected["df_within"]
        assert anova_table["ms_between"] == pytest.approx(expected["ms_between"], abs=1e-12)
        assert anova_table["ms_within"] == pytest.approx(expected["ms_within"], abs=1e-12)
        assert result["test"]["f_statistic"] == pytest.approx(
            expected["f_statistic"],
            abs=1e-12,
        )
        assert result["test"]["f_statistic"] == pytest.approx(
            float(scipy_result.statistic),
            abs=1e-12,
        )
        assert result["test"]["p_value"] == pytest.approx(expected["p_value"], abs=1e-12)
        assert result["test"]["p_value"] == pytest.approx(
            float(scipy_result.pvalue),
            abs=1e-12,
        )
        assert result["test"]["effect_size"]["eta_squared"] == pytest.approx(
            expected["eta_squared"],
            abs=1e-12,
        )
        assert result["test"]["effect_size"]["omega_squared"] == pytest.approx(
            expected["omega_squared"],
            abs=1e-12,
        )
        assert result["posthoc"]["performed"] is expected["posthoc_performed"]
        if result["posthoc"]["performed"]:
            assert result["posthoc"]["q_critical"] == pytest.approx(
                expected["tukey_q_critical"],
                abs=1e-12,
            )
            for comparison, expected_comparison in zip(
                result["posthoc"]["comparisons"],
                expected["comparisons"],
                strict=True,
            ):
                assert comparison["group_1_label"] == expected_comparison["group_1_label"]
                assert comparison["group_2_label"] == expected_comparison["group_2_label"]
                assert comparison["mean_difference"] == pytest.approx(
                    expected_comparison["mean_difference"],
                    abs=1e-12,
                )
                assert comparison["q_statistic"] == pytest.approx(
                    expected_comparison["q_statistic"],
                    abs=1e-12,
                )
                assert comparison["raw_p_value"] == pytest.approx(
                    expected_comparison["raw_p_value"],
                    abs=1e-12,
                )
                assert comparison["adjusted_p_value"] == pytest.approx(
                    expected_comparison["adjusted_p_value"],
                    abs=1e-12,
                )
                assert comparison["confidence_interval"]["lower"] == pytest.approx(
                    expected_comparison["ci_lower"],
                    abs=1e-12,
                )
                assert comparison["confidence_interval"]["upper"] == pytest.approx(
                    expected_comparison["ci_upper"],
                    abs=1e-12,
                )
        else:
            assert result["posthoc"]["reason"] == expected["posthoc_reason"]
            assert result["posthoc"]["comparisons"] == []


def test_one_way_anova_reports_exclusions_and_skips_posthoc_when_not_significant() -> None:
    rows = [
        ["1", "A"],
        ["2", "A"],
        ["", "A"],
        ["1.1", "B"],
        ["bad", "B"],
        ["2.1", "B"],
        ["1.2", "C"],
        ["2.2", "C"],
        ["3.2", ""],
    ]

    result = calculate_one_way_anova(
        rows,
        _response_column(),
        _group_column(),
        posthoc_policy="after_significant",
    )

    assert result["n_total"] == 9
    assert result["n_used"] == 6
    assert result["n_excluded_missing_response"] == 1
    assert result["n_excluded_missing_group"] == 1
    assert result["n_excluded_non_numeric_response"] == 1
    assert result["posthoc"]["performed"] is False
    assert result["posthoc"]["reason"] == "overall_not_significant"
    assert "missing_values_excluded" in result["warnings"]
    assert "non_numeric_values_excluded" in result["warnings"]
    assert "posthoc_skipped_overall_not_significant" in result["warnings"]


def test_one_way_anova_keeps_negative_omega_squared_and_skips_posthoc() -> None:
    rows = [
        ["1", "A"],
        ["3", "A"],
        ["1.9", "B"],
        ["2.1", "B"],
        ["1.8", "C"],
        ["2.2", "C"],
    ]

    result = calculate_one_way_anova(
        rows,
        _response_column(),
        _group_column(),
        posthoc_policy="after_significant",
    )

    assert result["test"]["p_value"] == pytest.approx(1.0, abs=1e-12)
    effect_size = result["test"]["effect_size"]
    assert effect_size["eta_squared"] == pytest.approx(0.0, abs=1e-12)
    assert effect_size["omega_squared"] == pytest.approx(-0.5, abs=1e-12)
    assert "omega_squared=(SS_between-df_between*MSE)/(SS_total+MSE)" in effect_size["definition"]
    assert result["posthoc"]["performed"] is False
    assert result["posthoc"]["reason"] == "overall_not_significant"


def test_one_way_anova_warns_on_group_size_imbalance_when_posthoc_runs() -> None:
    rows = [
        ["1", "A"],
        ["2", "A"],
        ["8", "B"],
        ["9", "B"],
        ["10", "B"],
        ["11", "B"],
        ["12", "B"],
        ["13", "B"],
        ["14", "B"],
        ["15", "B"],
        ["9", "C"],
        ["10", "C"],
        ["11", "C"],
        ["12", "C"],
        ["13", "C"],
        ["14", "C"],
        ["15", "C"],
        ["16", "C"],
    ]

    result = calculate_one_way_anova(rows, _response_column(), _group_column())

    assert [group["n"] for group in result["groups"]] == [2, 8, 8]
    assert result["test"]["p_value"] == pytest.approx(0.00011112410768158681, abs=1e-15)
    assert result["posthoc"]["performed"] is True
    assert "group_size_imbalance" in result["warnings"]
    assert "tukey_kramer_after_standard_anova" in result["warnings"]


def test_one_way_anova_rejects_invalid_inputs_without_fallback_statistic() -> None:
    with pytest.raises(OneWayAnovaError, match="invalid_one_way_anova_type"):
        calculate_one_way_anova(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"]],
            _response_column(),
            _group_column(),
            anova_type="not-supported",
        )

    with pytest.raises(
        OneWayAnovaError,
        match="one_way_anova_requires_at_least_two_groups",
    ):
        calculate_one_way_anova(
            [["1", "A"], ["2", "A"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(OneWayAnovaError, match="one_way_anova_group_n_too_small"):
        calculate_one_way_anova(
            [["1", "A"], ["2", "A"], ["3", "B"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(OneWayAnovaError, match="one_way_anova_all_values_identical"):
        calculate_one_way_anova(
            [["1", "A"], ["1", "A"], ["1", "B"], ["1", "B"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(OneWayAnovaError, match="one_way_anova_zero_residual_variance"):
        calculate_one_way_anova(
            [["1", "A"], ["1", "A"], ["2", "B"], ["2", "B"]],
            _response_column(),
            _group_column(),
        )


def test_welch_anova_matches_hand_formula_and_games_howell_reference() -> None:
    rows = [
        *[[str(value), "A"] for value in [1, 2, 3, 4]],
        *[[str(value), "B"] for value in [2, 4, 8, 10, 12]],
        *[[str(value), "C"] for value in [7, 8, 9, 10, 11, 12]],
    ]

    result = calculate_one_way_anova(
        rows,
        _response_column(),
        _group_column(),
        anova_type="welch",
        posthoc_method="games_howell",
    )

    groups = [[1, 2, 3, 4], [2, 4, 8, 10, 12], [7, 8, 9, 10, 11, 12]]
    ns = [len(group) for group in groups]
    means = [sum(group) / len(group) for group in groups]
    variances = [stats.tvar(group) for group in groups]
    weights = [n / variance for n, variance in zip(ns, variances, strict=True)]
    weight_sum = sum(weights)
    weighted_mean = sum(
        weight * mean for weight, mean in zip(weights, means, strict=True)
    ) / weight_sum
    adjustment = sum(
        ((1 - (weight / weight_sum)) ** 2) / (n - 1)
        for weight, n in zip(weights, ns, strict=True)
    )
    expected_f = (
        sum(
            weight * ((mean - weighted_mean) ** 2)
            for weight, mean in zip(weights, means, strict=True)
        )
        / 2
    ) / (1 + (2 * (3 - 2) / ((3**2) - 1)) * adjustment)
    expected_df = ((3**2) - 1) / (3 * adjustment)

    assert result["schema_version"] == 2
    assert result["anova_table"] is None
    assert result["test"]["f_statistic"] == pytest.approx(expected_f, abs=1e-12)
    assert result["test"]["df_numerator"] == 2
    assert result["test"]["df_denominator"] == pytest.approx(expected_df, abs=1e-12)
    assert result["test"]["p_value"] == pytest.approx(
        stats.f.sf(expected_f, 2, expected_df),
        abs=1e-12,
    )
    assert result["test"]["effect_size"] is None
    comparisons = result["posthoc"]["comparisons"]
    assert len(comparisons) == 3
    first = comparisons[0]
    variance_term = (variances[0] / ns[0]) + (variances[1] / ns[1])
    expected_comparison_df = (variance_term**2) / (
        ((variances[0] / ns[0]) ** 2) / (ns[0] - 1)
        + ((variances[1] / ns[1]) ** 2) / (ns[1] - 1)
    )
    expected_q = abs(means[0] - means[1]) / ((variance_term / 2) ** 0.5)
    assert first["df"] == pytest.approx(expected_comparison_df, abs=1e-12)
    assert first["q_statistic"] == pytest.approx(expected_q, abs=1e-12)
    assert first["adjusted_p_value"] == pytest.approx(
        stats.studentized_range.sf(expected_q, 3, expected_comparison_df),
        abs=1e-12,
    )


def test_dunnett_compares_only_treatments_to_selected_control_reproducibly() -> None:
    rows = [
        *[[str(value), "A"] for value in [1, 2, 3, 4]],
        *[[str(value), "B"] for value in [4, 5, 6, 7]],
        *[[str(value), "C"] for value in [5, 6, 7, 8]],
    ]
    kwargs = {
        "posthoc_method": "dunnett",
        "control_group_label": "A",
        "dunnett_rng_seed": 4242,
    }

    first = calculate_one_way_anova(rows, _response_column(), _group_column(), **kwargs)
    second = calculate_one_way_anova(rows, _response_column(), _group_column(), **kwargs)

    comparisons = first["posthoc"]["comparisons"]
    assert len(comparisons) == 2
    assert [(item["group_1_label"], item["group_2_label"]) for item in comparisons] == [
        ("B", "A"),
        ("C", "A"),
    ]
    assert all(item["control_group_label"] == "A" for item in comparisons)
    assert first["posthoc"] == second["posthoc"]


@pytest.mark.parametrize(
    ("anova_type", "posthoc_method"),
    [
        ("standard", "games_howell"),
        ("welch", "tukey_kramer"),
        ("welch", "dunnett"),
    ],
)
def test_anova_rejects_incompatible_comparison_methods(
    anova_type: str,
    posthoc_method: str,
) -> None:
    with pytest.raises(OneWayAnovaError, match="one_way_anova_posthoc_incompatible"):
        calculate_one_way_anova(
            [["1", "A"], ["2", "A"], ["3", "B"], ["5", "B"]],
            _response_column(),
            _group_column(),
            anova_type=anova_type,
            posthoc_method=posthoc_method,
            control_group_label="A" if posthoc_method == "dunnett" else None,
        )


def test_welch_rejects_zero_group_variance() -> None:
    with pytest.raises(
        OneWayAnovaError,
        match="one_way_anova_welch_zero_group_variance",
    ):
        calculate_one_way_anova(
            [["1", "A"], ["1", "A"], ["2", "B"], ["4", "B"]],
            _response_column(),
            _group_column(),
            anova_type="welch",
            posthoc_method="none",
        )


def _response_column() -> OneWayAnovaResponseColumn:
    return OneWayAnovaResponseColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _group_column() -> OneWayAnovaGroupColumn:
    return OneWayAnovaGroupColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="string",
        measurement_level="nominal",
        role="group",
        unit=None,
    )
