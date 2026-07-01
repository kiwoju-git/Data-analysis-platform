import pytest

from app.statistics.individuals_chart import (
    IndividualsChartColumn,
    IndividualsChartError,
    calculate_individuals_chart,
)


def test_individuals_chart_is_hand_checkable_for_i_mr_limits() -> None:
    result = calculate_individuals_chart(
        [["10"], ["11"], ["9"], ["10"], ["12"], ["11"]],
        _value_column(),
    )

    assert result["summary_type"] == "individuals_chart"
    assert result["method"] == "i_mr_chart"
    assert result["order_source"] == "canonical_row_order"
    assert result["n_total"] == 6
    assert result["n_used"] == 6
    assert result["sigma_estimator"] == {
        "method": "average_moving_range_d2",
        "moving_range_length": 2,
        "d2": 1.128,
        "mrbar": pytest.approx(1.4),
        "sigma": pytest.approx(1.2411347517730495),
    }
    assert result["individuals_chart"]["center_line"] == pytest.approx(10.5)
    assert result["individuals_chart"]["lcl"] == pytest.approx(6.776595744680851)
    assert result["individuals_chart"]["ucl"] == pytest.approx(14.22340425531915)
    assert result["moving_range_chart"]["center_line"] == pytest.approx(1.4)
    assert result["moving_range_chart"]["lcl"] == 0.0
    assert result["moving_range_chart"]["ucl"] == pytest.approx(4.5738)
    assert result["signals"] == []
    assert result["warnings"] == [
        "individuals_chart_uses_canonical_row_order",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
    ]
    assert result["individuals_chart"]["points"][0] == {
        "position": 1,
        "canonical_position": 1,
        "value": 10.0,
        "signal_codes": [],
    }
    assert result["moving_range_chart"]["points"][0] == {
        "position": 2,
        "previous_position": 1,
        "canonical_position": 2,
        "previous_canonical_position": 1,
        "value": 1.0,
        "signal_codes": [],
    }


def test_individuals_chart_detects_i_and_mr_limit_signals() -> None:
    result = calculate_individuals_chart(
        [["10"], ["10.1"], ["10.2"], ["10.1"], ["10"], ["14"]],
        _value_column(),
    )

    assert result["individuals_chart"]["ucl"] == pytest.approx(13.073758865248226)
    assert result["moving_range_chart"]["ucl"] == pytest.approx(2.87496)
    assert result["signals"] == [
        {
            "signal_id": "i-limit-1",
            "code": "individuals_chart_i_beyond_3_sigma",
            "severity": "warning",
            "chart": "individuals",
            "position": 6,
            "canonical_position": 6,
            "value": 14.0,
            "limit": "upper",
            "definition": "one_point_outside_3_sigma_limits",
        },
        {
            "signal_id": "mr-limit-1",
            "code": "individuals_chart_mr_beyond_ucl",
            "severity": "warning",
            "chart": "moving_range",
            "position": 6,
            "previous_position": 5,
            "canonical_position": 6,
            "previous_canonical_position": 5,
            "value": 4.0,
            "limit": "upper",
            "definition": "one_moving_range_above_upper_control_limit",
        },
    ]
    assert result["individuals_chart"]["points"][-1]["signal_codes"] == [
        "individuals_chart_i_beyond_3_sigma",
    ]
    assert result["moving_range_chart"]["points"][-1]["signal_codes"] == [
        "individuals_chart_mr_beyond_ucl",
    ]
    assert result["warnings"] == [
        "individuals_chart_uses_canonical_row_order",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "individuals_chart_i_limit_signal_detected",
        "individuals_chart_mr_limit_signal_detected",
    ]


def test_individuals_chart_detects_same_side_centerline_signal() -> None:
    result = calculate_individuals_chart(
        [
            ["8"],
            ["12"],
            ["8"],
            ["12"],
            ["11"],
            ["11"],
            ["11"],
            ["11"],
            ["11"],
            ["11"],
            ["11"],
            ["11"],
            ["11"],
        ],
        _value_column(),
    )

    same_side_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "individuals_chart_i_same_side_centerline"
    ]
    assert same_side_signals == [
        {
            "signal_id": "i-same-side-1",
            "code": "individuals_chart_i_same_side_centerline",
            "severity": "warning",
            "chart": "individuals",
            "direction": "above",
            "length": 10,
            "start_position": 4,
            "end_position": 13,
            "position": 13,
            "start_canonical_position": 4,
            "canonical_position": 13,
            "value": 11.0,
            "definition": "consecutive_points_on_same_side_of_centerline",
        },
    ]
    assert "individuals_chart_i_same_side_signal_detected" in result["warnings"]
    assert result["individuals_chart"]["points"][3]["signal_codes"] == [
        "individuals_chart_i_same_side_centerline",
    ]
    assert result["individuals_chart"]["points"][-1]["signal_codes"] == [
        "individuals_chart_i_same_side_centerline",
    ]


def test_individuals_chart_detects_strict_trend_signal() -> None:
    result = calculate_individuals_chart(
        [["1"], ["2"], ["3"], ["4"], ["5"], ["6"]],
        _value_column(),
    )

    assert result["signals"] == [
        {
            "signal_id": "i-trend-1",
            "code": "individuals_chart_i_trend",
            "severity": "warning",
            "chart": "individuals",
            "direction": "increasing",
            "length": 6,
            "start_position": 1,
            "end_position": 6,
            "position": 6,
            "start_canonical_position": 1,
            "canonical_position": 6,
            "value": 6.0,
            "definition": "strictly_monotonic_consecutive_points",
        },
    ]
    assert result["warnings"] == [
        "individuals_chart_uses_canonical_row_order",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "individuals_chart_i_trend_signal_detected",
    ]
    assert result["individuals_chart"]["points"][0]["signal_codes"] == [
        "individuals_chart_i_trend",
    ]
    assert result["individuals_chart"]["points"][-1]["signal_codes"] == [
        "individuals_chart_i_trend",
    ]


def test_individuals_chart_breaks_trend_on_equal_adjacent_values() -> None:
    result = calculate_individuals_chart(
        [["1"], ["2"], ["3"], ["3"], ["4"], ["5"], ["6"]],
        _value_column(),
    )

    assert [
        signal for signal in result["signals"] if signal["code"] == "individuals_chart_i_trend"
    ] == []
    assert "individuals_chart_i_trend_signal_detected" not in result["warnings"]


def test_individuals_chart_detects_two_of_three_beyond_two_sigma_signal() -> None:
    result = calculate_individuals_chart(
        [["0"], ["0.1"], ["0.2"], ["0.1"], ["0"], ["1.0"], ["1.1"], ["1.0"]],
        _value_column(),
    )

    zone_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "individuals_chart_i_two_of_three_beyond_2_sigma"
    ]
    assert zone_signals == [
        {
            "signal_id": "i-two-of-three-1",
            "code": "individuals_chart_i_two_of_three_beyond_2_sigma",
            "severity": "warning",
            "chart": "individuals",
            "direction": "above",
            "length": 3,
            "count": 2,
            "sigma_multiple": 2.0,
            "start_position": 5,
            "end_position": 7,
            "position": 7,
            "positions": [6, 7],
            "start_canonical_position": 5,
            "canonical_position": 7,
            "canonical_positions": [6, 7],
            "value": 1.1,
            "definition": "two_of_three_consecutive_points_beyond_2_sigma_same_side",
        },
    ]
    assert "individuals_chart_i_two_of_three_signal_detected" in result["warnings"]
    assert (
        "individuals_chart_i_two_of_three_beyond_2_sigma"
        not in result["individuals_chart"]["points"][4]["signal_codes"]
    )
    assert (
        "individuals_chart_i_two_of_three_beyond_2_sigma"
        in result["individuals_chart"]["points"][5]["signal_codes"]
    )
    assert (
        "individuals_chart_i_two_of_three_beyond_2_sigma"
        in result["individuals_chart"]["points"][6]["signal_codes"]
    )


def test_individuals_chart_detects_four_of_five_beyond_one_sigma_signal() -> None:
    result = calculate_individuals_chart(
        [
            ["0"],
            ["0.3"],
            ["0.2"],
            ["0.3"],
            ["0.2"],
            ["0.62"],
            ["0.58"],
            ["0.61"],
            ["0.59"],
            ["0.6"],
        ],
        _value_column(),
    )

    zone_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "individuals_chart_i_four_of_five_beyond_1_sigma"
    ]
    assert zone_signals == [
        {
            "signal_id": "i-four-of-five-1",
            "code": "individuals_chart_i_four_of_five_beyond_1_sigma",
            "severity": "warning",
            "chart": "individuals",
            "direction": "above",
            "length": 5,
            "count": 4,
            "sigma_multiple": 1.0,
            "start_position": 5,
            "end_position": 9,
            "position": 9,
            "positions": [6, 7, 8, 9],
            "start_canonical_position": 5,
            "canonical_position": 9,
            "canonical_positions": [6, 7, 8, 9],
            "value": 0.59,
            "definition": "four_of_five_consecutive_points_beyond_1_sigma_same_side",
        },
    ]
    assert "individuals_chart_i_four_of_five_signal_detected" in result["warnings"]
    assert (
        "individuals_chart_i_four_of_five_beyond_1_sigma"
        not in result["individuals_chart"]["points"][4]["signal_codes"]
    )
    for point in result["individuals_chart"]["points"][5:9]:
        assert "individuals_chart_i_four_of_five_beyond_1_sigma" in point["signal_codes"]


def test_individuals_chart_detects_alternating_signal() -> None:
    result = calculate_individuals_chart(
        [
            ["1.0"],
            ["3.0"],
            ["1.2"],
            ["2.8"],
            ["1.4"],
            ["2.6"],
            ["1.6"],
            ["2.4"],
            ["1.8"],
            ["2.2"],
            ["1.9"],
            ["2.1"],
            ["1.95"],
            ["2.05"],
        ],
        _value_column(),
    )

    alternating_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "individuals_chart_i_alternating"
    ]
    assert alternating_signals == [
        {
            "signal_id": "i-alternating-1",
            "code": "individuals_chart_i_alternating",
            "severity": "warning",
            "chart": "individuals",
            "direction": "alternating",
            "length": 14,
            "start_position": 1,
            "end_position": 14,
            "position": 14,
            "start_canonical_position": 1,
            "canonical_position": 14,
            "value": 2.05,
            "definition": "strictly_alternating_consecutive_point_directions",
        },
    ]
    assert "individuals_chart_i_alternating_signal_detected" in result["warnings"]
    assert (
        "individuals_chart_i_alternating"
        in result["individuals_chart"]["points"][0]["signal_codes"]
    )
    assert (
        "individuals_chart_i_alternating"
        in result["individuals_chart"]["points"][-1]["signal_codes"]
    )


def test_individuals_chart_detects_fifteen_within_one_sigma_signal() -> None:
    result = calculate_individuals_chart(
        [
            ["9.8"],
            ["10.2"],
            ["9.8"],
            ["10.2"],
            ["9.8"],
            ["10.2"],
            ["9.8"],
            ["10.2"],
            ["9.8"],
            ["10.2"],
            ["9.8"],
            ["10.2"],
            ["9.8"],
            ["10.2"],
            ["9.8"],
        ],
        _value_column(),
    )

    within_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "individuals_chart_i_fifteen_within_1_sigma"
    ]
    assert within_signals == [
        {
            "signal_id": "i-fifteen-within-one-sigma-1",
            "code": "individuals_chart_i_fifteen_within_1_sigma",
            "severity": "warning",
            "chart": "individuals",
            "direction": "within",
            "length": 15,
            "count": 15,
            "sigma_multiple": 1.0,
            "start_position": 1,
            "end_position": 15,
            "position": 15,
            "positions": list(range(1, 16)),
            "start_canonical_position": 1,
            "canonical_position": 15,
            "canonical_positions": list(range(1, 16)),
            "value": 9.8,
            "definition": "fifteen_consecutive_points_within_1_sigma_centerline",
        },
    ]
    assert "individuals_chart_i_fifteen_within_1_sigma_signal_detected" in result["warnings"]
    assert (
        "individuals_chart_i_fifteen_within_1_sigma"
        in result["individuals_chart"]["points"][7]["signal_codes"]
    )


def test_individuals_chart_detects_eight_outside_one_sigma_signal() -> None:
    result = calculate_individuals_chart(
        [["9.0"], ["9.1"], ["9.2"], ["9.1"], ["10.8"], ["10.9"], ["10.8"], ["10.9"]],
        _value_column(),
    )

    outside_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "individuals_chart_i_eight_outside_1_sigma"
    ]
    assert outside_signals == [
        {
            "signal_id": "i-eight-outside-one-sigma-1",
            "code": "individuals_chart_i_eight_outside_1_sigma",
            "severity": "warning",
            "chart": "individuals",
            "direction": "outside",
            "length": 8,
            "count": 8,
            "sigma_multiple": 1.0,
            "start_position": 1,
            "end_position": 8,
            "position": 8,
            "positions": list(range(1, 9)),
            "start_canonical_position": 1,
            "canonical_position": 8,
            "canonical_positions": list(range(1, 9)),
            "value": 10.9,
            "definition": "eight_consecutive_points_outside_1_sigma_centerline",
        },
    ]
    assert "individuals_chart_i_eight_outside_1_sigma_signal_detected" in result["warnings"]
    assert (
        "individuals_chart_i_eight_outside_1_sigma"
        in result["individuals_chart"]["points"][0]["signal_codes"]
    )
    assert (
        "individuals_chart_i_eight_outside_1_sigma"
        in result["individuals_chart"]["points"][-1]["signal_codes"]
    )


def test_individuals_chart_reports_exclusions_and_truncated_points() -> None:
    result = calculate_individuals_chart(
        [["10"], [""], ["11"], ["bad"], ["9"], ["10"], ["12"]],
        _value_column(),
        point_limit=3,
    )

    assert result["n_total"] == 7
    assert result["n_used"] == 5
    assert result["n_excluded_missing_value"] == 1
    assert result["n_excluded_non_numeric_value"] == 1
    assert result["individuals_chart"]["points_truncated"] is True
    assert result["individuals_chart"]["points"] == [
        {"position": 1, "canonical_position": 1, "value": 10.0, "signal_codes": []},
        {"position": 5, "canonical_position": 5, "value": 9.0, "signal_codes": []},
        {"position": 7, "canonical_position": 7, "value": 12.0, "signal_codes": []},
    ]
    assert result["warnings"] == [
        "individuals_chart_uses_canonical_row_order",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "missing_values_excluded",
        "non_numeric_values_excluded",
        "individuals_chart_points_truncated",
    ]


def test_individuals_chart_sorts_by_numeric_order_without_exposing_order_values() -> None:
    result = calculate_individuals_chart(
        [["4", "30"], ["1", "10"], ["3", "20"], ["2", "20"], ["5", "40"], ["6", "50"]],
        _value_column(),
        order_column=_order_column(),
    )

    assert result["order_source"] == "numeric_order_column_ascending"
    assert result["order_tie_breaker"] == "canonical_row_position"
    assert result["order_timezone"] is None
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
    assert result["n_excluded_missing_order"] == 0
    assert result["n_excluded_non_numeric_order"] == 0
    assert result["individuals_chart"]["x_axis"] == "order_rank"
    assert [point["position"] for point in result["individuals_chart"]["points"]] == [
        1,
        2,
        3,
        4,
        5,
        6,
    ]
    assert [point["canonical_position"] for point in result["individuals_chart"]["points"]] == [
        2,
        3,
        4,
        1,
        5,
        6,
    ]
    assert [point["value"] for point in result["individuals_chart"]["points"]] == [
        1.0,
        3.0,
        2.0,
        4.0,
        5.0,
        6.0,
    ]
    assert [point["value"] for point in result["moving_range_chart"]["points"]] == [
        2.0,
        1.0,
        2.0,
        1.0,
        1.0,
    ]
    assert result["sigma_estimator"]["mrbar"] == pytest.approx(1.4)
    assert result["warnings"] == [
        "individuals_chart_uses_numeric_order_column",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "individuals_chart_order_ties_stable_sorted",
    ]


def test_individuals_chart_sorts_by_datetime_order_without_exposing_order_values() -> None:
    result = calculate_individuals_chart(
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
    assert [point["canonical_position"] for point in result["individuals_chart"]["points"]] == [
        2,
        3,
        4,
        1,
        5,
        6,
    ]
    assert [point["value"] for point in result["individuals_chart"]["points"]] == [
        1.0,
        3.0,
        2.0,
        4.0,
        5.0,
        6.0,
    ]
    assert result["warnings"] == [
        "individuals_chart_uses_datetime_order_column",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "individuals_chart_order_ties_stable_sorted",
    ]
    assert "2024" not in str(result)


def test_individuals_chart_reports_order_exclusions() -> None:
    result = calculate_individuals_chart(
        [["1", "1"], ["2", ""], ["3", "bad"], ["4", "2"], ["5", "3"], ["6", "4"]],
        _value_column(),
        order_column=_order_column(),
    )

    assert result["n_total"] == 6
    assert result["n_used"] == 4
    assert result["n_excluded_missing_order"] == 1
    assert result["n_excluded_non_numeric_order"] == 1
    assert [point["value"] for point in result["individuals_chart"]["points"]] == [
        1.0,
        4.0,
        5.0,
        6.0,
    ]
    assert result["warnings"] == [
        "individuals_chart_uses_numeric_order_column",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "individuals_chart_order_missing_excluded",
        "individuals_chart_order_non_numeric_excluded",
    ]


def test_individuals_chart_reports_datetime_order_exclusions() -> None:
    result = calculate_individuals_chart(
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
    assert [point["value"] for point in result["individuals_chart"]["points"]] == [
        1.0,
        4.0,
        5.0,
        6.0,
    ]
    assert result["warnings"] == [
        "individuals_chart_uses_datetime_order_column",
        "individuals_chart_control_limits_estimated_from_moving_range",
        "individuals_chart_process_stability_not_proven",
        "individuals_chart_order_missing_excluded",
        "individuals_chart_order_invalid_datetime_excluded",
    ]


def test_individuals_chart_rejects_mixed_timezone_datetime_order() -> None:
    with pytest.raises(
        IndividualsChartError,
        match="individuals_chart_order_mixed_timezone_awareness",
    ):
        calculate_individuals_chart(
            [
                ["1", "2024-01-01T00:00:00Z"],
                ["2", "2024-01-02T00:00:00"],
                ["3", "2024-01-03T00:00:00Z"],
            ],
            _value_column(),
            order_column=_datetime_order_column(),
        )


def test_individuals_chart_rejects_invalid_inputs_without_fake_limits() -> None:
    with pytest.raises(IndividualsChartError, match="individuals_chart_n_too_small"):
        calculate_individuals_chart([["1"], ["2"]], _value_column())

    with pytest.raises(IndividualsChartError, match="individuals_chart_zero_moving_range"):
        calculate_individuals_chart([["2"], ["2"], ["2"]], _value_column())

    with pytest.raises(
        IndividualsChartError,
        match="individuals_chart_missing_policy_unsupported",
    ):
        calculate_individuals_chart(
            [["1"], ["2"], ["3"]],
            _value_column(),
            missing_policy="available_case_by_column",
        )

    with pytest.raises(IndividualsChartError, match="invalid_individuals_chart_point_limit"):
        calculate_individuals_chart([["1"], ["2"], ["3"]], _value_column(), point_limit=0)

    with pytest.raises(
        IndividualsChartError,
        match="invalid_individuals_chart_same_side_min_length",
    ):
        calculate_individuals_chart(
            [["1"], ["2"], ["3"]],
            _value_column(),
            same_side_min_length=2,
        )

    with pytest.raises(IndividualsChartError, match="invalid_individuals_chart_trend_min_length"):
        calculate_individuals_chart(
            [["1"], ["2"], ["3"]],
            _value_column(),
            trend_min_length=2,
        )


def _value_column() -> IndividualsChartColumn:
    return IndividualsChartColumn(
        column_id="value",
        column_index=0,
        display_name="value",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _order_column() -> IndividualsChartColumn:
    return IndividualsChartColumn(
        column_id="order",
        column_index=1,
        display_name="order",
        data_type="decimal",
        measurement_level="continuous",
        role="order",
        unit=None,
    )


def _datetime_order_column() -> IndividualsChartColumn:
    return IndividualsChartColumn(
        column_id="when",
        column_index=1,
        display_name="when",
        data_type="datetime",
        measurement_level="datetime",
        role="feature",
        unit=None,
    )
