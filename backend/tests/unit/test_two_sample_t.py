import json
from pathlib import Path

import pytest

from app.statistics.two_sample_t import (
    TwoSampleTError,
    TwoSampleTGroupColumn,
    TwoSampleTResponseColumn,
    calculate_two_sample_t,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/two_sample_t_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/two_sample_t_scipy_reference.json")


def test_two_sample_t_is_hand_checkable_for_group_summaries() -> None:
    result = calculate_two_sample_t(
        [["1", "A"], ["2", "A"], ["3", "A"], ["2", "B"], ["4", "B"], ["6", "B"]],
        _response_column(),
        _group_column(),
    )

    assert result["summary_type"] == "two_sample_t_test"
    assert result["method"] == "welch_two_sample_t"
    assert result["variance_assumption"] == "welch"
    assert result["missing_policy"] == "complete_case"
    assert result["warnings"] == [
        "two_sample_t_independence_assumption",
        "two_sample_t_not_auto_switched",
    ]
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    assert result["group_count"] == 2
    groups = result["groups"]  # type: ignore[assignment]
    assert groups[0]["group_label"] == "A"
    assert groups[0]["n"] == 3
    assert groups[0]["mean"] == 2.0
    assert groups[0]["variance"] == 1.0
    assert groups[1]["group_label"] == "B"
    assert groups[1]["mean"] == 4.0
    assert groups[1]["variance"] == 4.0

    contrast = result["contrast"]  # type: ignore[assignment]
    assert contrast["estimate"] == -2.0
    assert contrast["estimate_definition"] == "group_1_mean_minus_group_2_mean"
    assert contrast["statistic"] < 0
    assert 0.0 <= contrast["p_value"] <= 1.0
    assert contrast["effect_size"]["hedges_g"] < 0


def test_two_sample_t_matches_scipy_reference_fixture_for_welch_and_pooled() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        rows = _rows_from_case(case)
        expected = cases_by_id[case["case_id"]]
        for variance_assumption in ["welch", "pooled"]:
            result = calculate_two_sample_t(
                rows,
                _response_column(),
                _group_column(),
                alpha=case["alpha"],
                confidence_level=case["confidence_level"],
                alternative=case["alternative"],
                null_difference=case["null_difference"],
                variance_assumption=variance_assumption,
            )
            assert [group["group_label"] for group in result["groups"]] == expected["group_order"]
            assert [group["n"] for group in result["groups"]] == expected["group_sizes"]
            assert [group["mean"] for group in result["groups"]] == pytest.approx(
                expected["group_means"],
                abs=1e-12,
            )
            contrast = result["contrast"]
            expected_contrast = expected[variance_assumption]
            assert contrast["estimate"] == pytest.approx(expected["estimate"], abs=1e-12)
            assert contrast["standard_error"] == pytest.approx(
                expected_contrast["standard_error"],
                abs=1e-12,
            )
            assert contrast["df"] == pytest.approx(expected_contrast["df"], abs=1e-12)
            assert contrast["statistic"] == pytest.approx(
                expected_contrast["statistic"],
                abs=1e-12,
            )
            assert contrast["p_value"] == pytest.approx(
                expected_contrast["pvalue"],
                abs=1e-12,
            )
            assert contrast["confidence_interval"]["lower"] == pytest.approx(
                expected_contrast["ci_lower"],
                abs=1e-12,
            )
            assert contrast["confidence_interval"]["upper"] == pytest.approx(
                expected_contrast["ci_upper"],
                abs=1e-12,
            )
            assert contrast["effect_size"]["cohen_d"] == pytest.approx(
                expected["effect_size"]["cohen_d"],
                abs=1e-12,
            )
            assert contrast["effect_size"]["hedges_g"] == pytest.approx(
                expected["effect_size"]["hedges_g"],
                abs=1e-12,
            )


def test_two_sample_t_reports_exclusions_and_pooled_warning() -> None:
    result = calculate_two_sample_t(
        [["1", "A"], ["2", "A"], ["", "A"], ["bad", "B"], ["4", "B"], ["6", "B"], ["7", ""]],
        _response_column(),
        _group_column(),
        variance_assumption="pooled",
    )

    assert result["n_total"] == 7
    assert result["n_used"] == 4
    assert result["n_excluded_missing_response"] == 1
    assert result["n_excluded_missing_group"] == 1
    assert result["n_excluded_non_numeric_response"] == 1
    assert result["warnings"] == [
        "two_sample_t_independence_assumption",
        "two_sample_t_not_auto_switched",
        "pooled_variance_assumption_selected",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]


def test_two_sample_t_rejects_invalid_group_structure_without_fake_statistic() -> None:
    with pytest.raises(TwoSampleTError, match="two_sample_t_requires_exactly_two_groups"):
        calculate_two_sample_t(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"], ["5", "C"], ["6", "C"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(TwoSampleTError, match="two_sample_t_group_n_too_small"):
        calculate_two_sample_t(
            [["1", "A"], ["2", "A"], ["3", "B"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(TwoSampleTError, match="two_sample_t_standard_error_zero"):
        calculate_two_sample_t(
            [["5", "A"], ["5", "A"], ["5", "B"], ["5", "B"]],
            _response_column(),
            _group_column(),
        )


def _rows_from_case(case: dict[str, object]) -> list[list[str]]:
    groups = case["groups"]
    assert isinstance(groups, dict)
    rows: list[list[str]] = []
    for group_label, values in groups.items():
        assert isinstance(group_label, str)
        assert isinstance(values, list)
        rows.extend([[str(value), group_label] for value in values])
    return rows


def _response_column() -> TwoSampleTResponseColumn:
    return TwoSampleTResponseColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _group_column() -> TwoSampleTGroupColumn:
    return TwoSampleTGroupColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="group",
        unit=None,
    )
