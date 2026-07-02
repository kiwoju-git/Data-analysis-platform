import json

import pytest

from app.statistics.run_chart import RunChartColumn, RunChartError, calculate_run_chart


def test_run_chart_is_hand_checkable_for_median_runs_and_trend() -> None:
    result = calculate_run_chart(
        [["1"], ["2"], ["3"], ["4"], ["5"], ["6"], ["4"], ["3"]],
        _value_column(),
    )

    assert result["summary_type"] == "run_chart"
    assert result["method"] == "median_run_chart"
    assert result["center_method"] == "median"
    assert result["order_source"] == "canonical_row_order"
    assert result["tie_policy"] == "exclude_from_runs"
    assert result["n_total"] == 8
    assert result["n_used"] == 8
    assert result["center_line"] == 3.5
    assert result["runs"] == {
        "run_count": 3,
        "n_above": 4,
        "n_below": 4,
        "n_ties": 0,
        "longest_run_length": 4,
        "run_count_definition": "consecutive above/below median groups excluding ties",
    }
    assert result["runs_test"] == {
        "method": "exact_conditional_run_count_distribution",
        "alpha": 0.05,
        "available": True,
        "observed_run_count": 3,
        "n_above": 4,
        "n_below": 4,
        "n_ties": 0,
        "n_non_tie": 8,
        "expected_run_count": 5.0,
        "variance": pytest.approx(1.7142857142857142),
        "p_value_low": pytest.approx(8 / 70),
        "p_value_high": pytest.approx(68 / 70),
        "interpretation": "not_extreme",
        "skipped_reason": None,
        "max_exact_n": 5000,
    }
    assert result["signals"] == [
        {
            "signal_id": "trend-1",
            "code": "run_chart_trend",
            "severity": "warning",
            "direction": "increasing",
            "length": 6,
            "start_position": 1,
            "end_position": 6,
            "definition": "strictly_monotonic_consecutive_points",
        },
    ]
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_canonical_row_order",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_trend_signal_detected",
    ]
    assert result["chart"] == {
        "x_axis": "canonical_row_position",
        "point_count": 8,
        "points_truncated": False,
        "point_limit": 1000,
        "points": [
            {
                "position": 1,
                "value": 1.0,
                "relative_to_center": "below",
                "signal_codes": ["run_chart_trend"],
            },
            {
                "position": 2,
                "value": 2.0,
                "relative_to_center": "below",
                "signal_codes": ["run_chart_trend"],
            },
            {
                "position": 3,
                "value": 3.0,
                "relative_to_center": "below",
                "signal_codes": ["run_chart_trend"],
            },
            {
                "position": 4,
                "value": 4.0,
                "relative_to_center": "above",
                "signal_codes": ["run_chart_trend"],
            },
            {
                "position": 5,
                "value": 5.0,
                "relative_to_center": "above",
                "signal_codes": ["run_chart_trend"],
            },
            {
                "position": 6,
                "value": 6.0,
                "relative_to_center": "above",
                "signal_codes": ["run_chart_trend"],
            },
            {"position": 7, "value": 4.0, "relative_to_center": "above", "signal_codes": []},
            {"position": 8, "value": 3.0, "relative_to_center": "below", "signal_codes": []},
        ],
    }


def test_run_chart_reports_exclusions_and_ties_without_raw_values() -> None:
    result = calculate_run_chart(
        [["1"], [""], ["2"], ["bad"], ["2"], ["3"], ["4"]],
        _value_column(),
        point_limit=3,
    )

    assert result["n_total"] == 7
    assert result["n_used"] == 5
    assert result["n_excluded_missing_value"] == 1
    assert result["n_excluded_non_numeric_value"] == 1
    assert result["center_line"] == 2.0
    assert result["runs"]["n_ties"] == 2
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_canonical_row_order",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "missing_values_excluded",
        "non_numeric_values_excluded",
        "run_chart_ties_excluded_from_runs",
        "run_chart_points_truncated",
    ]
    chart = result["chart"]
    assert chart["point_count"] == 5
    assert chart["points_truncated"] is True
    assert chart["points"] == [
        {"position": 1, "value": 1.0, "relative_to_center": "below", "signal_codes": []},
        {"position": 5, "value": 2.0, "relative_to_center": "tie", "signal_codes": []},
        {"position": 7, "value": 4.0, "relative_to_center": "above", "signal_codes": []},
    ]


def test_run_chart_marks_runs_test_unavailable_when_one_side_is_absent() -> None:
    result = calculate_run_chart([["1"], ["1"], ["2"]], _value_column())

    assert result["runs"] == {
        "run_count": 1,
        "n_above": 1,
        "n_below": 0,
        "n_ties": 2,
        "longest_run_length": 1,
        "run_count_definition": "consecutive above/below median groups excluding ties",
    }
    assert result["runs_test"] == {
        "method": "exact_conditional_run_count_distribution",
        "alpha": 0.05,
        "available": False,
        "observed_run_count": 1,
        "n_above": 1,
        "n_below": 0,
        "n_ties": 2,
        "n_non_tie": 1,
        "expected_run_count": None,
        "variance": None,
        "p_value_low": None,
        "p_value_high": None,
        "interpretation": "not_available",
        "skipped_reason": "one_side_absent",
        "max_exact_n": 5000,
    }
    assert result["signals"] == []
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_canonical_row_order",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_runs_test_unavailable",
        "run_chart_ties_excluded_from_runs",
    ]


def test_run_chart_sorts_by_numeric_order_without_exposing_order_values() -> None:
    result = calculate_run_chart(
        [["4", "30"], ["1", "10"], ["3", "20"], ["2", "20"], ["5", "40"], ["6", "50"]],
        _value_column(),
        order_column=_order_column(),
    )

    assert result["order_source"] == "numeric_order_column_ascending"
    assert result["order_tie_breaker"] == "canonical_row_position"
    assert result["order"] == {
        "column_id": "order",
        "column_index": 1,
        "display_name": "order",
        "data_type": "decimal",
        "measurement_level": "continuous",
        "role": "order",
        "unit": None,
    }
    assert result["order_duplicate_count"] == 1
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_numeric_order_column",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_order_ties_stable_sorted",
    ]
    chart = result["chart"]
    assert chart["x_axis"] == "order_rank"
    assert [point["position"] for point in chart["points"]] == [1, 2, 3, 4, 5, 6]
    assert [point["canonical_position"] for point in chart["points"]] == [2, 3, 4, 1, 5, 6]
    assert [point["value"] for point in chart["points"]] == [1.0, 3.0, 2.0, 4.0, 5.0, 6.0]
    chart_json = json.dumps(chart)
    assert "order_value" not in chart_json
    assert "10.0" not in chart_json
    assert "30.0" not in chart_json


def test_run_chart_sorts_by_datetime_order_without_exposing_order_values() -> None:
    result = calculate_run_chart(
        [
            ["4", "2024-01-03"],
            ["1", "2024-01-01"],
            ["3", "2024-01-02"],
            ["2", "2024-01-02"],
            ["5", "2024-01-04"],
            ["6", "2024-01-05"],
        ],
        _value_column(),
        order_column=_datetime_order_column(),
    )

    assert result["order_source"] == "datetime_order_column_ascending"
    assert result["order_timezone"] == "timezone_naive"
    assert result["order_duplicate_count"] == 1
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_datetime_order_column",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_order_ties_stable_sorted",
    ]
    chart = result["chart"]
    assert chart["x_axis"] == "order_rank"
    assert [point["position"] for point in chart["points"]] == [1, 2, 3, 4, 5, 6]
    assert [point["canonical_position"] for point in chart["points"]] == [2, 3, 4, 1, 5, 6]
    assert [point["value"] for point in chart["points"]] == [1.0, 3.0, 2.0, 4.0, 5.0, 6.0]
    chart_json = json.dumps(chart)
    assert "2024" not in chart_json
    assert "order_value" not in chart_json


def test_run_chart_reports_order_exclusions() -> None:
    result = calculate_run_chart(
        [["1", "1"], ["2", ""], ["3", "bad"], ["4", "2"], ["5", "3"], ["6", "4"]],
        _value_column(),
        order_column=_order_column(),
    )

    assert result["n_total"] == 6
    assert result["n_used"] == 4
    assert result["n_excluded_missing_order"] == 1
    assert result["n_excluded_non_numeric_order"] == 1
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_numeric_order_column",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_order_missing_excluded",
        "run_chart_order_non_numeric_excluded",
    ]
    assert [point["value"] for point in result["chart"]["points"]] == [1.0, 4.0, 5.0, 6.0]


def test_run_chart_reports_datetime_order_exclusions() -> None:
    result = calculate_run_chart(
        [
            ["1", "2024-01-01"],
            ["2", ""],
            ["3", "not-a-date"],
            ["4", "2024-01-02"],
            ["5", "2024-01-03"],
            ["6", "2024-01-04"],
        ],
        _value_column(),
        order_column=_datetime_order_column(),
    )

    assert result["n_total"] == 6
    assert result["n_used"] == 4
    assert result["n_excluded_missing_order"] == 1
    assert result["n_excluded_non_numeric_order"] == 1
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_datetime_order_column",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_order_missing_excluded",
        "run_chart_order_invalid_datetime_excluded",
    ]
    assert [point["value"] for point in result["chart"]["points"]] == [1.0, 4.0, 5.0, 6.0]


def test_run_chart_rejects_mixed_timezone_datetime_order() -> None:
    with pytest.raises(RunChartError, match="run_chart_order_mixed_timezone_awareness"):
        calculate_run_chart(
            [
                ["1", "2024-01-01T00:00:00Z"],
                ["2", "2024-01-02T00:00:00"],
                ["3", "2024-01-03T00:00:00Z"],
            ],
            _value_column(),
            order_column=_datetime_order_column(),
        )


def test_run_chart_detects_strict_oscillation_without_control_limits() -> None:
    result = calculate_run_chart(
        [["1"], ["8"], ["2"], ["7"], ["3"], ["6"], ["4"], ["5"]],
        _value_column(),
        oscillation_min_length=8,
    )

    assert result["oscillation_rule"] == {
        "code": "run_chart_oscillation",
        "definition": "strictly_alternating_consecutive_point_directions",
        "minimum_length": 8,
    }
    assert result["signals"] == [
        {
            "signal_id": "oscillation-1",
            "code": "run_chart_oscillation",
            "severity": "warning",
            "direction": "alternating",
            "length": 8,
            "start_position": 1,
            "end_position": 8,
            "definition": "strictly_alternating_consecutive_point_directions",
        },
        {
            "signal_id": "mixture-1",
            "code": "run_chart_mixture",
            "severity": "warning",
            "direction": "high_runs",
            "length": 8,
            "start_position": 1,
            "end_position": 8,
            "definition": "exact_high_run_count_given_above_below_counts",
        },
    ]
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_canonical_row_order",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_oscillation_signal_detected",
        "run_chart_mixture_signal_detected",
    ]
    assert result["chart"]["points"][0]["signal_codes"] == [
        "run_chart_oscillation",
        "run_chart_mixture",
    ]
    assert result["chart"]["points"][-1]["signal_codes"] == [
        "run_chart_oscillation",
        "run_chart_mixture",
    ]
    assert "control_limit" not in json.dumps(result)


def test_run_chart_breaks_oscillation_on_equal_adjacent_values() -> None:
    result = calculate_run_chart(
        [["1"], ["4"], ["2"], ["2"], ["5"], ["3"], ["6"], ["4"], ["7"]],
        _value_column(),
        oscillation_min_length=8,
    )

    assert result["signals"] == []
    assert "run_chart_oscillation_signal_detected" not in result["warnings"]


def test_run_chart_detects_exact_low_run_count_as_clustering() -> None:
    result = calculate_run_chart(
        [["1"], ["1.4"], ["1.1"], ["1.3"], ["1.2"], ["10"], ["10.4"], ["10.1"], ["10.3"], ["10.2"]],
        _value_column(),
    )

    assert result["runs"]["run_count"] == 2
    assert result["runs_test"]["available"] is True
    assert result["runs_test"]["observed_run_count"] == 2
    assert result["runs_test"]["n_above"] == 5
    assert result["runs_test"]["n_below"] == 5
    assert result["runs_test"]["p_value_low"] == pytest.approx(2 / 252)
    assert result["runs_test"]["p_value_high"] == pytest.approx(1.0)
    assert result["runs_test"]["interpretation"] == "clustering"
    assert result["signals"] == [
        {
            "signal_id": "clustering-1",
            "code": "run_chart_clustering",
            "severity": "warning",
            "direction": "low_runs",
            "length": 10,
            "start_position": 1,
            "end_position": 10,
            "definition": "exact_low_run_count_given_above_below_counts",
        },
    ]
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_canonical_row_order",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_clustering_signal_detected",
    ]


def test_run_chart_detects_exact_high_run_count_as_mixture() -> None:
    result = calculate_run_chart(
        [["1"], ["10"], ["1.1"], ["10.1"], ["1.2"], ["10.2"], ["1.3"], ["10.3"], ["1.4"], ["10.4"]],
        _value_column(),
    )

    assert result["runs"]["run_count"] == 10
    assert result["runs_test"]["available"] is True
    assert result["runs_test"]["observed_run_count"] == 10
    assert result["runs_test"]["p_value_low"] == pytest.approx(1.0)
    assert result["runs_test"]["p_value_high"] == pytest.approx(2 / 252)
    assert result["runs_test"]["interpretation"] == "mixture"
    assert result["signals"] == [
        {
            "signal_id": "mixture-1",
            "code": "run_chart_mixture",
            "severity": "warning",
            "direction": "high_runs",
            "length": 10,
            "start_position": 1,
            "end_position": 10,
            "definition": "exact_high_run_count_given_above_below_counts",
        },
    ]
    assert result["warnings"] == [
        "run_chart_not_control_chart",
        "run_chart_uses_canonical_row_order",
        "run_chart_trend_rule_defined",
        "run_chart_oscillation_rule_defined",
        "run_chart_runs_test_defined",
        "run_chart_mixture_signal_detected",
    ]


def test_run_chart_rejects_invalid_inputs_without_fake_signals() -> None:
    with pytest.raises(RunChartError, match="run_chart_n_too_small"):
        calculate_run_chart([["1"], ["2"]], _value_column())

    with pytest.raises(RunChartError, match="run_chart_all_values_tied_to_center"):
        calculate_run_chart([["2"], ["2"], ["2"]], _value_column())

    with pytest.raises(RunChartError, match="invalid_run_chart_center_method"):
        calculate_run_chart([["1"], ["2"], ["3"]], _value_column(), center_method="mean")

    with pytest.raises(RunChartError, match="run_chart_missing_policy_unsupported"):
        calculate_run_chart(
            [["1"], ["2"], ["3"]],
            _value_column(),
            missing_policy="available_case_by_column",
        )

    with pytest.raises(RunChartError, match="invalid_run_chart_oscillation_min_length"):
        calculate_run_chart(
            [["1"], ["2"], ["3"], ["4"]],
            _value_column(),
            oscillation_min_length=3,
        )

    with pytest.raises(RunChartError, match="invalid_run_chart_runs_test_alpha"):
        calculate_run_chart(
            [["1"], ["2"], ["3"], ["4"]],
            _value_column(),
            runs_test_alpha=0.5,
        )


def _value_column() -> RunChartColumn:
    return RunChartColumn(
        column_id="value",
        column_index=0,
        display_name="value",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _order_column() -> RunChartColumn:
    return RunChartColumn(
        column_id="order",
        column_index=1,
        display_name="order",
        data_type="decimal",
        measurement_level="continuous",
        role="order",
        unit=None,
    )


def _datetime_order_column() -> RunChartColumn:
    return RunChartColumn(
        column_id="order",
        column_index=1,
        display_name="order",
        data_type="datetime",
        measurement_level="datetime",
        role="time",
        unit=None,
    )
