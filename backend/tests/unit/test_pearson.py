import json
from pathlib import Path

import pytest

from app.statistics.pearson import (
    PearsonCorrelationColumn,
    PearsonCorrelationError,
    calculate_pearson_correlation,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/pearson_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/pearson_scipy_reference.json")


def test_pearson_is_hand_checkable_for_sample_summaries() -> None:
    result = calculate_pearson_correlation(
        [["1", "1"], ["2", "3"], ["3", "2"], ["4", "5"]],
        _x_column(),
        _y_column(),
    )

    assert result["summary_type"] == "pearson_correlation"
    assert result["method"] == "pearson_product_moment_correlation"
    assert result["missing_policy"] == "complete_case"
    assert result["warnings"] == [
        "pearson_correlation_not_causation",
        "pearson_linear_relationship_assumption",
        "pearson_outlier_sensitive",
    ]
    assert result["n_total"] == 4
    assert result["n_used"] == 4
    assert result["x_summary"]["mean"] == 2.5
    assert result["y_summary"]["mean"] == 2.75
    assert result["scatterplot"] == {
        "x_column_id": "x",
        "y_column_id": "y",
        "point_count": 4,
        "points_truncated": False,
        "point_limit": 500,
        "points": [
            {"x": 1.0, "y": 1.0},
            {"x": 2.0, "y": 3.0},
            {"x": 3.0, "y": 2.0},
            {"x": 4.0, "y": 5.0},
        ],
    }
    assert result["association"]["covariance"] == pytest.approx(1.8333333333333333, abs=1e-12)
    assert result["association"]["correlation"] == pytest.approx(
        0.8315218406202999,
        abs=1e-12,
    )
    assert result["association"]["r_squared"] == pytest.approx(
        0.6914285714285714,
        abs=1e-12,
    )
    assert result["test"]["statistic_name"] == "r"
    assert result["test"]["p_value"] == pytest.approx(0.1684781593797, abs=1e-12)
    assert result["confidence_interval"]["method"] == "fisher_z"
    assert result["confidence_interval"]["lower"] == pytest.approx(
        -0.6451324587565248,
        abs=1e-12,
    )
    assert result["confidence_interval"]["upper"] == pytest.approx(
        0.9963561001514175,
        abs=1e-12,
    )


def test_pearson_scatterplot_payload_is_capped_without_row_identity() -> None:
    result = calculate_pearson_correlation(
        [["1", "1"], ["2", "3"], ["3", "2"], ["4", "5"], ["5", "6"], ["6", "8"]],
        _x_column(),
        _y_column(),
        scatter_point_limit=3,
    )

    scatterplot = result["scatterplot"]
    assert scatterplot["point_count"] == 6
    assert scatterplot["points_truncated"] is True
    assert scatterplot["point_limit"] == 3
    assert scatterplot["points"] == [
        {"x": 1.0, "y": 1.0},
        {"x": 3.0, "y": 2.0},
        {"x": 6.0, "y": 8.0},
    ]
    assert "row_index" not in scatterplot["points"][0]


def test_pearson_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        result = calculate_pearson_correlation(
            [[str(x), str(y)] for x, y in zip(case["x"], case["y"], strict=True)],
            _x_column(),
            _y_column(),
            alpha=case["alpha"],
            confidence_level=case["confidence_level"],
        )
        expected = cases_by_id[case["case_id"]]
        assert result["n_used"] == expected["n"]
        assert result["association"]["correlation"] == pytest.approx(
            expected["correlation"],
            abs=1e-12,
        )
        assert result["association"]["covariance"] == pytest.approx(
            expected["covariance"],
            abs=1e-12,
        )
        assert result["test"]["p_value"] == pytest.approx(expected["pvalue"], abs=1e-12)
        assert result["confidence_interval"]["lower"] == pytest.approx(
            expected["ci_lower"],
            abs=1e-12,
        )
        assert result["confidence_interval"]["upper"] == pytest.approx(
            expected["ci_upper"],
            abs=1e-12,
        )


def test_pearson_reports_exclusions_without_pairwise_n_drift() -> None:
    result = calculate_pearson_correlation(
        [
            ["1", "2"],
            ["", "3"],
            ["bad", "4"],
            ["4", ""],
            ["5", "bad"],
            ["6", "7"],
            ["7", "9"],
            ["8", "10"],
        ],
        _x_column(),
        _y_column(),
    )

    assert result["n_total"] == 8
    assert result["n_used"] == 4
    assert result["n_excluded_missing_x"] == 1
    assert result["n_excluded_missing_y"] == 1
    assert result["n_excluded_non_numeric_x"] == 1
    assert result["n_excluded_non_numeric_y"] == 1
    assert result["warnings"] == [
        "pearson_correlation_not_causation",
        "pearson_linear_relationship_assumption",
        "pearson_outlier_sensitive",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]


def test_pearson_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(PearsonCorrelationError, match="pearson_n_too_small"):
        calculate_pearson_correlation(
            [["1", "1"], ["2", "2"], ["3", "3"]],
            _x_column(),
            _y_column(),
        )

    with pytest.raises(PearsonCorrelationError, match="pearson_x_constant"):
        calculate_pearson_correlation(
            [["1", "1"], ["1", "2"], ["1", "3"], ["1", "4"]],
            _x_column(),
            _y_column(),
        )

    with pytest.raises(PearsonCorrelationError, match="pearson_y_constant"):
        calculate_pearson_correlation(
            [["1", "1"], ["2", "1"], ["3", "1"], ["4", "1"]],
            _x_column(),
            _y_column(),
        )


def _x_column() -> PearsonCorrelationColumn:
    return PearsonCorrelationColumn(
        column_id="x",
        column_index=0,
        display_name="x",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _y_column() -> PearsonCorrelationColumn:
    return PearsonCorrelationColumn(
        column_id="y",
        column_index=1,
        display_name="y",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )
