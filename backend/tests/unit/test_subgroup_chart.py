import pytest

from app.statistics.subgroup_chart import (
    SubgroupChartColumn,
    SubgroupChartError,
    calculate_subgroup_chart,
)


def test_subgroup_chart_is_hand_checkable_for_xbar_r_limits() -> None:
    result = calculate_subgroup_chart(
        [["10", "A"], ["12", "A"], ["11", "B"], ["13", "B"], ["9", "C"], ["11", "C"]],
        _value_column(),
        _subgroup_column(),
    )

    assert result["summary_type"] == "subgroup_chart"
    assert result["method"] == "xbar_r_chart"
    assert result["order_source"] == "canonical_subgroup_first_seen"
    assert result["subgroup_size"] == 2
    assert result["subgroup_count"] == 3
    assert result["constants"] == {
        "source": "standard_xbar_r_constants",
        "subgroup_size": 2,
        "a2": 1.88,
        "d3": 0.0,
        "d4": 3.267,
    }
    assert result["xbar_chart"]["center_line"] == pytest.approx(11.0)
    assert result["xbar_chart"]["lcl"] == pytest.approx(7.24)
    assert result["xbar_chart"]["ucl"] == pytest.approx(14.76)
    assert result["r_chart"]["center_line"] == pytest.approx(2.0)
    assert result["r_chart"]["lcl"] == pytest.approx(0.0)
    assert result["r_chart"]["ucl"] == pytest.approx(6.534)
    assert result["signals"] == []
    assert result["warnings"] == [
        "subgroup_chart_uses_canonical_subgroup_order",
        "subgroup_chart_control_limits_estimated_from_xbar_r_constants",
        "subgroup_chart_rational_subgroups_not_proven",
    ]
    assert result["xbar_chart"]["points"][0] == {
        "position": 1,
        "subgroup_label": "A",
        "first_canonical_position": 1,
        "last_canonical_position": 2,
        "n": 2,
        "value": 11.0,
        "mean": 11.0,
        "range": 2.0,
        "signal_codes": [],
    }
    assert result["r_chart"]["points"][1] == {
        "position": 2,
        "subgroup_label": "B",
        "first_canonical_position": 3,
        "last_canonical_position": 4,
        "n": 2,
        "value": 2.0,
        "mean": 12.0,
        "range": 2.0,
        "signal_codes": [],
    }


def test_subgroup_chart_detects_xbar_limit_signal() -> None:
    result = calculate_subgroup_chart(
        [
            ["10", "A"],
            ["10.1", "A"],
            ["10", "B"],
            ["10.1", "B"],
            ["10", "C"],
            ["10.1", "C"],
            ["10.3", "D"],
            ["10.4", "D"],
        ],
        _value_column(),
        _subgroup_column(),
    )

    assert result["xbar_chart"]["ucl"] == pytest.approx(10.313)
    assert len(result["signals"]) == 1
    signal = result["signals"][0]
    assert signal == {
        "signal_id": "xbar-limit-1",
        "code": "subgroup_chart_xbar_beyond_control_limits",
        "severity": "warning",
        "chart": "xbar",
        "position": 4,
        "subgroup_label": "D",
        "first_canonical_position": 7,
        "last_canonical_position": 8,
        "value": signal["value"],
        "limit": "upper",
        "definition": "one_subgroup_mean_outside_xbar_control_limits",
    }
    assert signal["value"] == pytest.approx(10.35)
    assert "subgroup_chart_xbar_limit_signal_detected" in result["warnings"]
    assert result["xbar_chart"]["points"][-1]["signal_codes"] == [
        "subgroup_chart_xbar_beyond_control_limits",
    ]


def test_subgroup_chart_detects_range_limit_signal() -> None:
    result = calculate_subgroup_chart(
        [
            ["10", "A"],
            ["10.1", "A"],
            ["10", "B"],
            ["10.1", "B"],
            ["10", "C"],
            ["10.1", "C"],
            ["10", "D"],
            ["12", "D"],
        ],
        _value_column(),
        _subgroup_column(),
    )

    assert result["r_chart"]["ucl"] == pytest.approx(1.878525)
    range_signals = [
        signal
        for signal in result["signals"]
        if signal["code"] == "subgroup_chart_r_beyond_control_limits"
    ]
    assert range_signals == [
        {
            "signal_id": "r-limit-1",
            "code": "subgroup_chart_r_beyond_control_limits",
            "severity": "warning",
            "chart": "r",
            "position": 4,
            "subgroup_label": "D",
            "first_canonical_position": 7,
            "last_canonical_position": 8,
            "value": 2.0,
            "limit": "upper",
            "definition": "one_subgroup_range_outside_r_control_limits",
        },
    ]
    assert "subgroup_chart_r_limit_signal_detected" in result["warnings"]
    assert result["r_chart"]["points"][-1]["signal_codes"] == [
        "subgroup_chart_r_beyond_control_limits",
    ]


def test_subgroup_chart_is_hand_checkable_for_xbar_s_limits() -> None:
    result = calculate_subgroup_chart(
        [
            ["10", "A"],
            ["11", "A"],
            ["12", "A"],
            ["11", "B"],
            ["12", "B"],
            ["13", "B"],
            ["9", "C"],
            ["10", "C"],
            ["11", "C"],
        ],
        _value_column(),
        _subgroup_column(),
        chart_type="xbar_s",
    )

    assert result["summary_type"] == "subgroup_chart"
    assert result["method"] == "xbar_s_chart"
    assert result["chart_type"] == "xbar_s"
    assert result["subgroup_size"] == 3
    assert result["subgroup_count"] == 3
    assert result["constants"] == {
        "source": "standard_xbar_s_constants",
        "subgroup_size": 3,
        "a3": 1.954,
        "b3": 0.0,
        "b4": 2.568,
        "stddev_definition": "sample_standard_deviation_n_minus_1",
    }
    assert result["xbar_chart"]["center_line"] == pytest.approx(11.0)
    assert result["xbar_chart"]["lcl"] == pytest.approx(9.046)
    assert result["xbar_chart"]["ucl"] == pytest.approx(12.954)
    assert result["s_chart"]["center_line"] == pytest.approx(1.0)
    assert result["s_chart"]["lcl"] == pytest.approx(0.0)
    assert result["s_chart"]["ucl"] == pytest.approx(2.568)
    assert result["signals"] == []
    assert result["warnings"] == [
        "subgroup_chart_uses_canonical_subgroup_order",
        "subgroup_chart_control_limits_estimated_from_xbar_s_constants",
        "subgroup_chart_rational_subgroups_not_proven",
    ]
    assert result["s_chart"]["points"][0] == {
        "position": 1,
        "subgroup_label": "A",
        "first_canonical_position": 1,
        "last_canonical_position": 3,
        "n": 3,
        "value": 1.0,
        "mean": 11.0,
        "range": 2.0,
        "signal_codes": [],
        "stddev": 1.0,
    }


def test_subgroup_chart_detects_stddev_limit_signal() -> None:
    result = calculate_subgroup_chart(
        [
            ["10", "A"],
            ["10.1", "A"],
            ["10.2", "A"],
            ["10", "B"],
            ["10.1", "B"],
            ["10.2", "B"],
            ["10", "C"],
            ["10.1", "C"],
            ["10.2", "C"],
            ["9", "D"],
            ["10.1", "D"],
            ["11.2", "D"],
        ],
        _value_column(),
        _subgroup_column(),
        chart_type="xbar_s",
    )

    assert result["s_chart"]["center_line"] == pytest.approx(0.35)
    assert result["s_chart"]["ucl"] == pytest.approx(0.8988)
    assert len(result["signals"]) == 1
    signal = result["signals"][0]
    assert signal == {
        "signal_id": "s-limit-1",
        "code": "subgroup_chart_s_beyond_control_limits",
        "severity": "warning",
        "chart": "s",
        "position": 4,
        "subgroup_label": "D",
        "first_canonical_position": 10,
        "last_canonical_position": 12,
        "value": signal["value"],
        "limit": "upper",
        "definition": "one_subgroup_stddev_outside_s_control_limits",
    }
    assert signal["value"] == pytest.approx(1.1)
    assert "subgroup_chart_s_limit_signal_detected" in result["warnings"]
    assert result["s_chart"]["points"][-1]["signal_codes"] == [
        "subgroup_chart_s_beyond_control_limits",
    ]


def test_subgroup_chart_reports_exclusions_and_truncated_points() -> None:
    result = calculate_subgroup_chart(
        [
            ["10", "A"],
            ["11", "A"],
            ["", "B"],
            ["bad", "B"],
            ["12", ""],
            ["12", "B"],
            ["14", "B"],
            ["13", "C"],
            ["15", "C"],
        ],
        _value_column(),
        _subgroup_column(),
        point_limit=2,
    )

    assert result["n_total"] == 9
    assert result["n_used"] == 6
    assert result["n_excluded_missing_value"] == 1
    assert result["n_excluded_non_numeric_value"] == 1
    assert result["n_excluded_missing_subgroup"] == 1
    assert result["xbar_chart"]["points_truncated"] is True
    assert [point["subgroup_label"] for point in result["xbar_chart"]["points"]] == ["A", "C"]
    assert result["warnings"] == [
        "subgroup_chart_uses_canonical_subgroup_order",
        "subgroup_chart_control_limits_estimated_from_xbar_r_constants",
        "subgroup_chart_rational_subgroups_not_proven",
        "missing_values_excluded",
        "non_numeric_values_excluded",
        "subgroup_chart_subgroup_missing_excluded",
        "subgroup_chart_points_truncated",
    ]


def test_subgroup_chart_rejects_invalid_inputs_without_fake_limits() -> None:
    with pytest.raises(SubgroupChartError, match="subgroup_chart_subgroup_count_too_small"):
        calculate_subgroup_chart([["1", "A"], ["2", "A"]], _value_column(), _subgroup_column())

    with pytest.raises(SubgroupChartError, match="subgroup_chart_subgroup_size_too_small"):
        calculate_subgroup_chart(
            [["1", "A"], ["2", "A"], ["3", "B"]],
            _value_column(),
            _subgroup_column(),
        )

    with pytest.raises(
        SubgroupChartError,
        match="subgroup_chart_varying_subgroup_size_unsupported",
    ):
        calculate_subgroup_chart(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"], ["5", "B"]],
            _value_column(),
            _subgroup_column(),
        )

    with pytest.raises(SubgroupChartError, match="subgroup_chart_subgroup_size_unsupported"):
        calculate_subgroup_chart(
            [
                *[["1", "A"] for _index in range(11)],
                *[["2", "B"] for _index in range(11)],
            ],
            _value_column(),
            _subgroup_column(),
        )

    with pytest.raises(SubgroupChartError, match="subgroup_chart_zero_average_range"):
        calculate_subgroup_chart(
            [["2", "A"], ["2", "A"], ["3", "B"], ["3", "B"]],
            _value_column(),
            _subgroup_column(),
        )

    with pytest.raises(SubgroupChartError, match="subgroup_chart_zero_average_stddev"):
        calculate_subgroup_chart(
            [["2", "A"], ["2", "A"], ["2", "A"], ["3", "B"], ["3", "B"], ["3", "B"]],
            _value_column(),
            _subgroup_column(),
            chart_type="xbar_s",
        )

    with pytest.raises(SubgroupChartError, match="subgroup_chart_type_unsupported"):
        calculate_subgroup_chart(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"]],
            _value_column(),
            _subgroup_column(),
            chart_type="xbar_mr",
        )

    with pytest.raises(SubgroupChartError, match="subgroup_chart_missing_policy_unsupported"):
        calculate_subgroup_chart(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"]],
            _value_column(),
            _subgroup_column(),
            missing_policy="available_case_by_column",
        )

    with pytest.raises(SubgroupChartError, match="invalid_subgroup_chart_point_limit"):
        calculate_subgroup_chart(
            [["1", "A"], ["2", "A"], ["3", "B"], ["4", "B"]],
            _value_column(),
            _subgroup_column(),
            point_limit=0,
        )


def _value_column() -> SubgroupChartColumn:
    return SubgroupChartColumn(
        column_id="value",
        column_index=0,
        display_name="value",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _subgroup_column() -> SubgroupChartColumn:
    return SubgroupChartColumn(
        column_id="subgroup",
        column_index=1,
        display_name="subgroup",
        data_type="text",
        measurement_level="nominal",
        role="subgroup_id",
        unit=None,
    )
