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

    result = calculate_one_way_anova(rows, _response_column(), _group_column())

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


def test_one_way_anova_rejects_invalid_inputs_without_fallback_statistic() -> None:
    with pytest.raises(OneWayAnovaError, match="invalid_one_way_anova_type"):
        calculate_one_way_anova(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"]],
            _response_column(),
            _group_column(),
            anova_type="welch",
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
