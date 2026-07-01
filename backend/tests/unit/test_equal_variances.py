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
    tests = result["tests"]  # type: ignore[assignment]
    assert tests[0]["method"] == "brown_forsythe"
    assert tests[0]["computed"] is True
    assert 0.0 <= tests[0]["p_value"] <= 1.0
    assert tests[1]["method"] == "levene_mean"
    assert tests[1]["computed"] is True


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
        tests = {test["method"]: test for test in result["tests"]}
        assert tests["brown_forsythe"]["center"] == expected["brown_forsythe"]["center"]
        assert tests["brown_forsythe"]["statistic"] == pytest.approx(
            expected["brown_forsythe"]["statistic"],
            abs=1e-12,
        )
        assert tests["brown_forsythe"]["p_value"] == pytest.approx(
            expected["brown_forsythe"]["pvalue"],
            abs=1e-12,
        )
        assert tests["levene_mean"]["center"] == expected["levene_mean"]["center"]
        assert tests["levene_mean"]["statistic"] == pytest.approx(
            expected["levene_mean"]["statistic"],
            abs=1e-12,
        )
        assert tests["levene_mean"]["p_value"] == pytest.approx(
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
    for test in result["tests"]:
        assert test["computed"] is False
        assert test["warnings"] == ["equal_variances_group_n_too_small"]


def test_equal_variances_reports_constant_response_without_fake_statistic() -> None:
    result = calculate_equal_variances(
        [["5", "A"], ["5", "A"], ["5", "B"], ["5", "B"]],
        _response_column(),
        _group_column(),
    )

    assert "constant_response" in result["warnings"]
    assert result["groups"][0]["warnings"] == ["constant_group"]
    for test in result["tests"]:
        assert test["computed"] is False
        assert test["statistic"] is None
        assert test["p_value"] is None
        assert test["warnings"] == ["constant_response"]


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
