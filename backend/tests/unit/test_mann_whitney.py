import json
from pathlib import Path

import pytest

from app.statistics.mann_whitney import (
    MannWhitneyError,
    MannWhitneyGroupColumn,
    MannWhitneyResponseColumn,
    calculate_mann_whitney,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/mann_whitney_input.json")
REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/mann_whitney_scipy_reference.json",
)


def test_mann_whitney_is_hand_checkable_for_u_and_effect_size() -> None:
    result = calculate_mann_whitney(
        [["1", "A"], ["2", "A"], ["3", "A"], ["4", "B"], ["5", "B"], ["6", "B"]],
        _response_column(),
        _group_column(),
        method="exact",
    )

    assert result["summary_type"] == "mann_whitney_u_test"
    assert result["method"] == "mann_whitney_u"
    assert result["missing_policy"] == "complete_case"
    assert result["requested_method"] == "exact"
    assert result["resolved_method"] == "exact"
    assert result["has_ties"] is False
    assert result["warnings"] == [
        "mann_whitney_independence_assumption",
        "mann_whitney_not_median_test",
        "small_group_size",
    ]
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    assert result["group_count"] == 2

    groups = result["groups"]
    assert groups[0]["group_label"] == "A"
    assert groups[0]["n"] == 3
    assert groups[0]["rank_sum"] == 6.0
    assert groups[0]["mean_rank"] == 2.0
    assert groups[1]["group_label"] == "B"
    assert groups[1]["rank_sum"] == 15.0
    assert groups[1]["mean_rank"] == 5.0

    test = result["test"]
    assert test["u_statistic"] == 0.0
    assert test["p_value"] == pytest.approx(0.1, abs=1e-12)
    assert test["effect_size"]["rank_biserial"] == -1.0
    assert test["effect_size"]["common_language_probability"] == 0.0


def test_mann_whitney_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        rows = _rows_from_case(case)
        expected = cases_by_id[case["case_id"]]
        result = calculate_mann_whitney(
            rows,
            _response_column(),
            _group_column(),
            alpha=case["alpha"],
            alternative=case["alternative"],
            method=case["method"],
        )

        assert [group["group_label"] for group in result["groups"]] == expected["group_order"]
        assert [group["n"] for group in result["groups"]] == expected["group_sizes"]
        assert [group["median"] for group in result["groups"]] == expected["group_medians"]
        assert [group["rank_sum"] for group in result["groups"]] == pytest.approx(
            expected["rank_sums"],
            abs=1e-12,
        )
        assert [group["mean_rank"] for group in result["groups"]] == pytest.approx(
            expected["mean_ranks"],
            abs=1e-12,
        )
        test = result["test"]
        assert test["u_statistic"] == pytest.approx(expected["u_statistic"], abs=1e-12)
        assert test["p_value"] == pytest.approx(expected["pvalue"], abs=1e-12)
        assert test["effect_size"]["rank_biserial"] == pytest.approx(
            expected["rank_biserial"],
            abs=1e-12,
        )
        assert test["effect_size"]["common_language_probability"] == pytest.approx(
            expected["common_language_probability"],
            abs=1e-12,
        )


def test_mann_whitney_reports_exclusions_and_auto_asymptotic_for_ties() -> None:
    result = calculate_mann_whitney(
        [
            ["1", "A"],
            ["2", "A"],
            ["2", "A"],
            ["3", "A"],
            ["2", "B"],
            ["4", "B"],
            ["5", "B"],
            ["", "A"],
            ["bad", "B"],
            ["6", ""],
        ],
        _response_column(),
        _group_column(),
    )

    assert result["n_total"] == 10
    assert result["n_used"] == 7
    assert result["n_excluded_missing_response"] == 1
    assert result["n_excluded_missing_group"] == 1
    assert result["n_excluded_non_numeric_response"] == 1
    assert result["has_ties"] is True
    assert result["requested_method"] == "auto"
    assert result["resolved_method"] == "asymptotic"
    assert result["warnings"] == [
        "mann_whitney_independence_assumption",
        "mann_whitney_not_median_test",
        "mann_whitney_ties_detected",
        "mann_whitney_auto_asymptotic_due_to_ties",
        "small_group_size",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]
    test = result["test"]
    assert 0.0 <= test["p_value"] <= 1.0


def test_mann_whitney_rejects_invalid_design_without_fake_statistic() -> None:
    with pytest.raises(MannWhitneyError, match="mann_whitney_requires_exactly_two_groups"):
        calculate_mann_whitney(
            [["1", "A"], ["2", "B"], ["3", "C"]],
            _response_column(),
            _group_column(),
        )

    with pytest.raises(MannWhitneyError, match="mann_whitney_exact_with_ties"):
        calculate_mann_whitney(
            [["1", "A"], ["2", "A"], ["2", "B"], ["3", "B"]],
            _response_column(),
            _group_column(),
            method="exact",
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


def _response_column() -> MannWhitneyResponseColumn:
    return MannWhitneyResponseColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _group_column() -> MannWhitneyGroupColumn:
    return MannWhitneyGroupColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="group",
        unit=None,
    )
