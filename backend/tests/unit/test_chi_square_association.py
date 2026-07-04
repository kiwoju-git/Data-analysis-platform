from __future__ import annotations

import json
from math import isfinite
from pathlib import Path

import pytest
from scipy import stats  # type: ignore[import-untyped]

from app.statistics.chi_square_association import (
    ChiSquareAssociationColumn,
    ChiSquareAssociationError,
    calculate_chi_square_association,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "reference" / "fixtures"


def test_chi_square_association_is_hand_checkable_for_two_by_two_table() -> None:
    rows = _rows_from_counts(["A", "B"], ["yes", "no"], [[30, 10], [10, 30]])

    result = calculate_chi_square_association(rows, _row_column(), _column_column())

    assert result["summary_type"] == "chi_square_association"
    assert result["method"] == "pearson_chi_square_independence"
    assert result["n_total"] == 80
    assert result["n_used"] == 80
    assert result["test"]["statistic"] == pytest.approx(20.0, abs=1e-12)
    assert result["test"]["df"] == 1
    assert result["test"]["p_value"] == pytest.approx(7.744216431044088e-06, abs=1e-15)
    assert result["effect_size"]["cramers_v"] == pytest.approx(0.5, abs=1e-12)
    assert result["contingency_table"]["column_totals"] == [40, 40]
    first_cell = result["contingency_table"]["rows"][0]["cells"][0]
    assert first_cell["observed"] == 30
    assert first_cell["expected"] == pytest.approx(20.0, abs=1e-12)
    assert first_cell["row_percent"] == pytest.approx(0.75, abs=1e-12)
    assert first_cell["column_percent"] == pytest.approx(0.75, abs=1e-12)
    assert first_cell["total_percent"] == pytest.approx(0.375, abs=1e-12)
    assert first_cell["standardized_residual"] == pytest.approx(
        (30.0 - 20.0) / (20.0**0.5),
        abs=1e-12,
    )
    assert "two_by_two_table" in result["warnings"]
    assert result["recommended_alternative_tests"] == []


def test_chi_square_association_matches_reference_fixture_and_scipy() -> None:
    input_payload = json.loads(
        (FIXTURE_DIR / "chi_square_association_input.json").read_text(),
    )
    reference_payload = json.loads(
        (FIXTURE_DIR / "chi_square_association_scipy_reference.json").read_text(),
    )
    references = {reference["case_id"]: reference for reference in reference_payload["cases"]}

    for case in input_payload["cases"]:
        expected = references[case["case_id"]]
        rows = _rows_from_counts(case["row_levels"], case["column_levels"], case["counts"])
        result = calculate_chi_square_association(
            rows,
            _row_column(),
            _column_column(),
            alpha=case["alpha"],
        )
        scipy_result = stats.chi2_contingency(case["counts"], correction=False)

        assert result["method"] == expected["method"]
        assert [level["level"] for level in result["row_levels"]] == expected["row_levels"]
        assert [level["level"] for level in result["column_levels"]] == expected["column_levels"]
        assert result["n_used"] == expected["n_used"]
        assert result["test"]["statistic"] == pytest.approx(
            expected["chi_square"],
            abs=1e-12,
        )
        assert result["test"]["statistic"] == pytest.approx(
            float(scipy_result.statistic),
            abs=1e-12,
        )
        assert result["test"]["p_value"] == pytest.approx(expected["p_value"], abs=1e-15)
        assert result["test"]["p_value"] == pytest.approx(
            float(scipy_result.pvalue),
            abs=1e-15,
        )
        assert result["test"]["df"] == expected["df"]
        assert result["effect_size"]["cramers_v"] == pytest.approx(
            expected["cramers_v"],
            abs=1e-12,
        )
        assert result["expected_count_summary"]["min_expected"] == pytest.approx(
            expected["min_expected"],
            abs=1e-12,
        )
        assert result["expected_count_summary"]["cells_below_5"] == expected["cells_below_5"]
        assert result["expected_count_summary"]["share_below_5"] == pytest.approx(
            expected["share_below_5"],
            abs=1e-12,
        )
        for row_index, expected_row in enumerate(expected["expected_counts"]):
            for column_index, expected_count in enumerate(expected_row):
                cell = result["contingency_table"]["rows"][row_index]["cells"][column_index]
                assert cell["expected"] == pytest.approx(expected_count, abs=1e-12)


def test_chi_square_association_reports_exclusions_and_sparse_2x2_warning() -> None:
    rows = _rows_from_counts(["A", "B"], ["yes", "no"], [[8, 1], [2, 9]])
    rows.extend([[None, "yes"], ["A", ""], ["", "yes"]])

    result = calculate_chi_square_association(rows, _row_column(), _column_column())

    assert result["n_total"] == 23
    assert result["n_used"] == 20
    assert result["n_excluded_missing_row"] == 2
    assert result["n_excluded_missing_column"] == 1
    assert result["expected_count_summary"]["rule_of_thumb_passed"] is False
    assert "missing_values_excluded" in result["warnings"]
    assert "small_expected_counts" in result["warnings"]
    assert "fisher_exact_recommended_for_sparse_2x2" in result["warnings"]
    assert result["recommended_alternative_tests"] == [
        {
            "method": "fisher_exact",
            "reason": "sparse_2x2_expected_counts",
            "implemented": False,
        },
    ]
    assert result["method"] == "pearson_chi_square_independence"
    assert result["test"]["statistic_name"] == "chi_square"
    for row in result["contingency_table"]["rows"]:
        for cell in row["cells"]:
            assert isfinite(cell["standardized_residual"])


def test_chi_square_association_rejects_invalid_inputs_without_fallback() -> None:
    with pytest.raises(ChiSquareAssociationError, match="invalid_chi_square_alpha"):
        calculate_chi_square_association(
            _rows_from_counts(["A", "B"], ["yes", "no"], [[1, 2], [3, 4]]),
            _row_column(),
            _column_column(),
            alpha=1.0,
        )

    with pytest.raises(
        ChiSquareAssociationError,
        match="chi_square_requires_at_least_two_row_levels",
    ):
        calculate_chi_square_association(
            [["A", "yes"], ["A", "no"]],
            _row_column(),
            _column_column(),
        )

    with pytest.raises(
        ChiSquareAssociationError,
        match="chi_square_requires_at_least_two_column_levels",
    ):
        calculate_chi_square_association(
            [["A", "yes"], ["B", "yes"]],
            _row_column(),
            _column_column(),
        )


def _rows_from_counts(
    row_levels: list[str],
    column_levels: list[str],
    counts: list[list[int]],
) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_index, row_level in enumerate(row_levels):
        for column_index, column_level in enumerate(column_levels):
            rows.extend([[row_level, column_level] for _ in range(counts[row_index][column_index])])
    return rows


def _row_column() -> ChiSquareAssociationColumn:
    return ChiSquareAssociationColumn(
        column_id="row_factor",
        column_index=0,
        display_name="row_factor",
        data_type="string",
        measurement_level="nominal",
        role="factor",
        unit=None,
    )


def _column_column() -> ChiSquareAssociationColumn:
    return ChiSquareAssociationColumn(
        column_id="column_factor",
        column_index=1,
        display_name="column_factor",
        data_type="string",
        measurement_level="nominal",
        role="factor",
        unit=None,
    )
