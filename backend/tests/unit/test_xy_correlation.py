import json
from pathlib import Path

import pytest

from app.statistics.xy_correlation import (
    XyCorrelationColumn,
    XyCorrelationError,
    calculate_xy_correlation,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/xy_correlation_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/xy_correlation_scipy_reference.json")


def test_xy_correlation_is_hand_checkable_for_matrix_shape_and_counts() -> None:
    result = calculate_xy_correlation(
        [
            ["1", "2", "1", "2"],
            ["2", "1", "2", "1"],
            ["3", "4", "1", "4"],
            ["4", "8", "4", "3"],
            ["5", "9", "5", "7"],
            ["6", "13", "7", "8"],
        ],
        [_x1_column(), _x2_column()],
        [_y1_column(), _y2_column()],
    )

    assert result["summary_type"] == "xy_correlation_matrix"
    assert result["method"] == "pairwise_pearson_product_moment_correlation"
    assert result["missing_policy"] == "pairwise_complete_case"
    assert result["pair_count"] == 4
    assert result["warnings"] == [
        "xy_correlation_not_causation",
        "xy_correlation_linear_relationship_assumption",
        "xy_correlation_outlier_sensitive",
    ]

    pairs = _pairs_by_key(result)
    assert pairs["x1:y1"]["n_used"] == 6
    assert pairs["x1:y1"]["status"] == "ok"
    assert pairs["x1:y1"]["association"]["correlation"] == pytest.approx(
        0.9268715709799871,
        abs=1e-12,
    )
    assert pairs["x1:y1"]["test"]["p_value"] == pytest.approx(
        0.007826113791877531,
        abs=1e-12,
    )
    assert pairs["x1:y1"]["confidence_interval"]["method"] == "fisher_z"


def test_xy_correlation_matches_scipy_reference_fixture() -> None:
    fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))

    result = calculate_xy_correlation(
        fixture["rows"],
        [_x1_column(), _x2_column()],
        [_y1_column(), _y2_column()],
        alpha=0.05,
        confidence_level=0.95,
    )

    pairs = _pairs_by_key(result)
    for pair_key, expected in reference["pairs"].items():
        pair = pairs[pair_key]
        assert pair["status"] == "ok"
        assert pair["association"]["correlation"] == pytest.approx(
            expected["correlation"],
            abs=1e-12,
        )
        assert pair["test"]["p_value"] == pytest.approx(expected["p_value"], abs=1e-12)


def test_xy_correlation_reports_pairwise_exclusions_and_cell_failures() -> None:
    result = calculate_xy_correlation(
        [
            ["1", "10", "2"],
            ["2", "10", "4"],
            ["3", "10", ""],
            ["4", "10", "8"],
            ["5", "10", "bad"],
            ["6", "10", "11"],
        ],
        [_x1_column(), _constant_x_column()],
        [_single_y_column()],
    )

    pairs = _pairs_by_key(result)
    ok_pair = pairs["x1:y"]
    assert ok_pair["status"] == "ok"
    assert ok_pair["n_total"] == 6
    assert ok_pair["n_used"] == 4
    assert ok_pair["n_excluded_missing_y"] == 1
    assert ok_pair["n_excluded_non_numeric_y"] == 1
    assert ok_pair["warnings"] == ["missing_values_excluded", "non_numeric_values_excluded"]

    failed_pair = pairs["constant:y"]
    assert failed_pair["status"] == "failed"
    assert failed_pair["error_code"] == "xy_correlation_x_constant"
    assert failed_pair["association"] is None
    assert failed_pair["test"] is None
    assert failed_pair["confidence_interval"] is None
    assert "xy_correlation_pair_failed" in result["warnings"]
    assert "missing_values_excluded" in result["warnings"]
    assert "non_numeric_values_excluded" in result["warnings"]


def test_xy_correlation_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(XyCorrelationError, match="invalid_xy_correlation_alpha"):
        calculate_xy_correlation([["1", "2"]], [_x1_column()], [_single_y_column()], alpha=0)

    with pytest.raises(XyCorrelationError, match="invalid_xy_correlation_confidence_level"):
        calculate_xy_correlation(
            [["1", "2"]],
            [_x1_column()],
            [_single_y_column()],
            confidence_level=1,
        )

    with pytest.raises(XyCorrelationError, match="xy_correlation_columns_required"):
        calculate_xy_correlation([["1", "2"]], [], [_single_y_column()])


def _pairs_by_key(result: dict[str, object]) -> dict[str, dict[str, object]]:
    pairs = result["pairs"]
    assert isinstance(pairs, list)
    by_key: dict[str, dict[str, object]] = {}
    for pair in pairs:
        assert isinstance(pair, dict)
        x = pair["x"]
        y = pair["y"]
        assert isinstance(x, dict)
        assert isinstance(y, dict)
        by_key[f"{x['display_name']}:{y['display_name']}"] = pair
    return by_key


def _x1_column() -> XyCorrelationColumn:
    return XyCorrelationColumn(
        column_id="x1",
        column_index=0,
        display_name="x1",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _x2_column() -> XyCorrelationColumn:
    return XyCorrelationColumn(
        column_id="x2",
        column_index=1,
        display_name="x2",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _constant_x_column() -> XyCorrelationColumn:
    return XyCorrelationColumn(
        column_id="constant",
        column_index=1,
        display_name="constant",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _y1_column() -> XyCorrelationColumn:
    return XyCorrelationColumn(
        column_id="y1",
        column_index=2,
        display_name="y1",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _y2_column() -> XyCorrelationColumn:
    return XyCorrelationColumn(
        column_id="y2",
        column_index=3,
        display_name="y2",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _single_y_column() -> XyCorrelationColumn:
    return XyCorrelationColumn(
        column_id="y",
        column_index=2,
        display_name="y",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )
