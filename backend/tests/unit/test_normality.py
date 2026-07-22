import json
from pathlib import Path

import pytest
from scripts.generate_normality_reference import _case_values, _load_fixture

from app.statistics.normality import (
    NormalityColumn,
    _anderson_pvalue_from_adjusted_statistic,
    calculate_normality,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/normality_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/normality_scipy_reference.json")


def test_normality_is_hand_checkable_for_symmetric_small_sample() -> None:
    result = calculate_normality(
        [[str(value)] for value in [-1.0, 0.0, 1.0]],
        [_column()],
        qq_point_limit=10,
    )

    assert result["schema_version"] == 2
    assert result["summary_type"] == "normality_test"
    assert result["missing_policy"] == "available_case_by_column"
    assert result["alpha"] == 0.05
    assert result["warnings"] == ["normality_not_method_switch"]
    column = result["columns"][0]  # type: ignore[index]
    assert column["n_total"] == 3
    assert column["n_used"] == 3
    assert column["mean"] == 0.0
    assert column["std"] == 1.0
    assert column["skewness"] == 0.0
    assert column["shapiro_wilk"]["computed"] is True
    assert 0.0 <= column["shapiro_wilk"]["p_value"] <= 1.0
    assert column["anderson_darling"]["computed"] is True
    assert column["anderson_darling"]["adjusted_statistic"] is not None
    assert 0.0 <= column["anderson_darling"]["p_value"] <= 1.0
    assert column["anderson_darling"]["p_value_is_approximate"] is True
    assert column["anderson_darling"]["p_value_method"] == "stephens_normal_unknown_mean_variance"
    assert column["anderson_darling"]["decision_at_alpha"]["alpha"] == 0.05
    assert column["qq_plot"]["point_count"] == 3
    assert column["warnings"] == []


def test_normality_matches_generated_scipy_reference_fixture() -> None:
    input_fixture = _load_fixture(INPUT_FIXTURE)
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        values = _case_values(case, _MinimalNp)
        result = calculate_normality(
            [[str(value)] for value in values],
            [_column(display_name=case["case_id"])],
            qq_point_limit=10,
        )
        column = result["columns"][0]  # type: ignore[index]
        expected = cases_by_id[case["case_id"]]
        assert column["n_used"] == expected["n"]
        assert column["shapiro_wilk"]["statistic"] == pytest.approx(
            expected["shapiro"]["statistic"],
            abs=1e-12,
        )
        assert column["shapiro_wilk"]["p_value"] == pytest.approx(
            expected["shapiro"]["pvalue"],
            abs=1e-12,
        )
        assert column["anderson_darling"]["statistic"] == pytest.approx(
            expected["anderson_norm"]["statistic"],
            abs=1e-12,
        )
        assert [
            item["critical_value"] for item in column["anderson_darling"]["critical_values"]
        ] == pytest.approx(expected["anderson_norm"]["critical_values"], abs=1e-12)
        for warning_code in expected.get("expected_warning_codes", []):
            assert warning_code in column["warnings"]


def test_normality_reports_missing_non_numeric_insufficient_and_constant() -> None:
    result = calculate_normality(
        [["5"], [None], ["bad"], ["5"]],
        [_column()],
    )

    column = result["columns"][0]  # type: ignore[index]
    assert column["n_total"] == 4
    assert column["n_used"] == 2
    assert column["n_missing"] == 1
    assert column["n_non_numeric"] == 1
    assert column["shapiro_wilk"]["computed"] is False
    assert column["anderson_darling"]["computed"] is False
    assert column["anderson_darling"]["adjusted_statistic"] is None
    assert column["anderson_darling"]["p_value"] is None
    assert column["warnings"] == [
        "non_numeric_values_excluded",
        "normality_insufficient_observations",
    ]

    constant_result = calculate_normality([[str(value)] for value in [7, 7, 7]], [_column()])
    constant_column = constant_result["columns"][0]  # type: ignore[index]
    assert constant_column["shapiro_wilk"]["computed"] is False
    assert constant_column["anderson_darling"]["computed"] is False
    assert constant_column["warnings"] == ["constant_column"]


def test_normality_truncates_qq_points_deterministically() -> None:
    result = calculate_normality(
        [[str(value)] for value in range(30)],
        [_column()],
        qq_point_limit=10,
    )

    column = result["columns"][0]  # type: ignore[index]
    assert column["qq_plot"]["point_count"] == 10
    assert column["qq_plot"]["points_truncated"] is True
    assert column["qq_plot"]["points"][0]["sample"] == 0.0
    assert column["qq_plot"]["points"][-1]["sample"] == 29.0
    assert "normality_qq_points_truncated" in column["warnings"]


@pytest.mark.parametrize(
    "adjusted_statistic",
    [0.0, 0.199999999, 0.2, 0.339999999, 0.34, 0.599999999, 0.6, 13.0, 13.000001],
)
def test_anderson_darling_pvalue_piecewise_boundaries_are_bounded(
    adjusted_statistic: float,
) -> None:
    p_value = _anderson_pvalue_from_adjusted_statistic(adjusted_statistic)
    assert 0.0 <= p_value <= 1.0


class _MinimalNp:
    @staticmethod
    def array(values: list[float], *, dtype: object) -> list[float]:
        assert dtype is float
        return [float(value) for value in values]

    @staticmethod
    def linspace(start: float, stop: float, count: int, *, dtype: object) -> list[float]:
        assert dtype is float
        step = (stop - start) / (count - 1)
        return [start + step * index for index in range(count)]


def _column(display_name: str = "alpha") -> NormalityColumn:
    return NormalityColumn(
        column_id="alpha",
        column_index=0,
        display_name=display_name,
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )
