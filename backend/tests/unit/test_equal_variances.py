import csv
import json
from pathlib import Path

import pytest

from app.statistics.equal_variances import (
    EqualVarianceGroupColumn,
    EqualVarianceResponseColumn,
    calculate_equal_variances,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/equal_variances_input.json")
REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/equal_variances_scipy_reference.json",
)


def test_equal_variances_is_hand_checkable_for_group_summaries() -> None:
    result = calculate_equal_variances(
        [["1", "A"], ["2", "A"], ["3", "A"], ["2", "B"], ["4", "B"], ["6", "B"]],
        _response_column(),
        _group_column(),
    )

    assert result["summary_type"] == "equal_variances_test"
    assert result["missing_policy"] == "complete_case"
    assert result["warnings"] == ["equal_variances_not_method_switch"]
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    assert result["group_count"] == 2
    groups = result["groups"]  # type: ignore[assignment]
    assert groups[0]["group_label"] == "A"
    assert groups[0]["n"] == 3
    assert groups[0]["mean"] == 2.0
    assert groups[0]["median"] == 2.0
    assert groups[0]["variance"] == 1.0
    assert groups[1]["group_label"] == "B"
    assert groups[1]["variance"] == 4.0
    assert result["schema_version"] == 2
    assert result["multiple_comparisons"]["computed"] is False  # type: ignore[index]
    assert result["multiple_comparisons"]["warnings"] == [  # type: ignore[index]
        "multiple_comparisons_group_n_too_small"
    ]
    assert result["levene"]["method"] == "levene_brown_forsythe"  # type: ignore[index]
    assert result["levene"]["computed"] is True  # type: ignore[index]
    assert 0.0 <= result["levene"]["p_value"] <= 1.0  # type: ignore[index,operator]
    assert result["additional_tests"][0]["method"] == "classical_levene_mean_centered"  # type: ignore[index]


def test_equal_variances_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        rows = _rows_from_case(case)
        result = calculate_equal_variances(rows, _response_column(), _group_column())
        expected = cases_by_id[case["case_id"]]

        assert result["group_count"] == expected["n_groups"]
        assert [group["n"] for group in result["groups"]] == expected["group_sizes"]
        levene = result["levene"]
        mean_centered = result["additional_tests"][0]  # type: ignore[index]
        assert levene["center"] == expected["brown_forsythe"]["center"]
        assert levene["statistic"] == pytest.approx(
            expected["brown_forsythe"]["statistic"],
            abs=1e-12,
        )
        assert levene["p_value"] == pytest.approx(
            expected["brown_forsythe"]["pvalue"],
            abs=1e-12,
        )
        assert mean_centered["center"] == expected["levene_mean"]["center"]
        assert mean_centered["statistic"] == pytest.approx(
            expected["levene_mean"]["statistic"],
            abs=1e-12,
        )
        assert mean_centered["p_value"] == pytest.approx(
            expected["levene_mean"]["pvalue"],
            abs=1e-12,
        )


def test_equal_variances_reports_missing_non_numeric_and_small_groups() -> None:
    result = calculate_equal_variances(
        [["1", "A"], ["", "A"], ["bad", "B"], ["2", ""], ["5", "B"]],
        _response_column(),
        _group_column(),
    )

    assert result["n_total"] == 5
    assert result["n_used"] == 2
    assert result["n_excluded_missing_response"] == 1
    assert result["n_excluded_missing_group"] == 1
    assert result["n_excluded_non_numeric_response"] == 1
    assert result["warnings"] == [
        "equal_variances_not_method_switch",
        "missing_values_excluded",
        "non_numeric_values_excluded",
        "equal_variances_group_n_too_small",
    ]
    assert result["multiple_comparisons"]["computed"] is False  # type: ignore[index]
    assert result["levene"]["warnings"] == ["equal_variances_group_n_too_small"]  # type: ignore[index]


def test_equal_variances_reports_constant_response_without_fake_statistic() -> None:
    result = calculate_equal_variances(
        [["5", "A"], ["5", "A"], ["5", "B"], ["5", "B"]],
        _response_column(),
        _group_column(),
    )

    assert "constant_response" in result["warnings"]
    assert result["groups"][0]["warnings"] == ["constant_group"]
    for test in [result["levene"], *result["additional_tests"]]:  # type: ignore[misc]
        assert test["computed"] is False
        assert test["statistic"] is None
        assert test["p_value"] is None
        assert test["warnings"] == ["constant_response"]


def test_multiple_comparisons_returns_intervals_and_consistent_decision() -> None:
    rows: list[list[str]] = []
    groups = {
        "A": [10 + offset for offset in (-2, -1, -0.5, 0, 0.5, 1, 2, -1.5, 1.5, 0.25)],
        "B": [20 + 3 * offset for offset in (-2, -1, -0.5, 0, 0.5, 1, 2, -1.5, 1.5, 0.25)],
        "C": [30 + 0.8 * offset for offset in (-2, -1, -0.5, 0, 0.5, 1, 2, -1.5, 1.5, 0.25)],
    }
    for label, values in groups.items():
        rows.extend([[str(value), label] for value in values])

    result = calculate_equal_variances(rows, _response_column(), _group_column())
    comparison = result["multiple_comparisons"]
    assert comparison["computed"] is True  # type: ignore[index]
    assert 0 <= comparison["p_value"] <= 1  # type: ignore[index,operator]
    assert len(comparison["groups"]) == 3  # type: ignore[index]
    assert comparison["reject_equal_variances"] is (comparison["p_value"] < 0.05)  # type: ignore[index,operator]
    for group in comparison["groups"]:  # type: ignore[index]
        assert group["comparison_interval"]["lower"] > 0
        assert group["comparison_interval"]["upper"] > group["comparison_interval"]["lower"]


def test_studio_process_fixture_matches_minitab_reference_output() -> None:
    source = Path("examples/tutorial/studio_process_training.csv")
    with source.open(encoding="utf-8-sig", newline="") as handle:
        parsed = list(csv.reader(handle))
    header = parsed[0]
    result = calculate_equal_variances(
        parsed[1:],
        EqualVarianceResponseColumn(
            column_id="yield_pct",
            column_index=header.index("yield_pct"),
            display_name="yield_pct",
            data_type="decimal",
            measurement_level="continuous",
            role="response",
            unit=None,
        ),
        EqualVarianceGroupColumn(
            column_id="production_line",
            column_index=header.index("production_line"),
            display_name="production_line",
            data_type="text",
            measurement_level="nominal",
            role="group",
            unit=None,
        ),
    )

    assert result["multiple_comparisons"]["p_value"] == pytest.approx(0.14518, abs=5e-5)  # type: ignore[index]
    assert result["levene"]["statistic"] == pytest.approx(1.78106, abs=5e-5)  # type: ignore[index]
    assert result["levene"]["p_value"] == pytest.approx(0.170707, abs=5e-6)  # type: ignore[index]


def _rows_from_case(case: dict[str, object]) -> list[list[str]]:
    groups = case["groups"]
    assert isinstance(groups, dict)
    rows: list[list[str]] = []
    for group_label, values in groups.items():
        assert isinstance(group_label, str)
        assert isinstance(values, list)
        rows.extend([[str(value), group_label] for value in values])
    return rows


def _response_column() -> EqualVarianceResponseColumn:
    return EqualVarianceResponseColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _group_column() -> EqualVarianceGroupColumn:
    return EqualVarianceGroupColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="group",
        unit=None,
    )
