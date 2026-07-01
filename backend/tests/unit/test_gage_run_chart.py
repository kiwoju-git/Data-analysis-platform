import json

import pytest

from app.statistics.gage_run_chart import (
    GageRunChartColumn,
    GageRunChartError,
    calculate_gage_run_chart,
)


def test_gage_run_chart_balanced_design_redacts_labels_and_summarizes_patterns() -> None:
    result = calculate_gage_run_chart(
        _balanced_rows(),
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
        order_column=_column("run", 4, data_type="integer", role="order"),
    )

    assert result["summary_type"] == "gage_run_chart"
    assert result["method"] == "measurement_system_run_chart"
    assert result["sample"]["n_total"] == 12
    assert result["sample"]["n_used"] == 12
    assert result["design"]["part_count"] == 3
    assert result["design"]["operator_count"] == 2
    assert result["design"]["replicate_count"] == 2
    assert result["order_source"] == "numeric_order_column_ascending"
    assert result["summary"]["mean"] == pytest.approx(23)
    assert result["summary"]["range"] == pytest.approx(26)
    assert result["part_summaries"][0] == {
        "index": 1,
        "n": 4,
        "mean": 13,
        "minimum": 9,
        "maximum": 17,
        "range": 8,
    }
    assert result["operator_summaries"][0]["mean"] == pytest.approx(21)
    assert result["chart"]["point_count"] == 12
    assert result["chart"]["points"][0] == {
        "position": 1,
        "canonical_position": 2,
        "value": 11,
        "part_index": 1,
        "operator_index": 1,
        "replicate_index": 2,
    }
    assert result["warnings"] == [
        "gage_run_chart_diagnostic_only",
        "gage_run_chart_requires_gage_design",
        "gage_run_chart_labels_redacted",
        "gage_run_chart_uses_order_column",
    ]
    serialized = json.dumps(result, ensure_ascii=False)
    assert "Part A" not in serialized
    assert "Operator 1" not in serialized


def test_gage_run_chart_uses_canonical_order_and_caps_points() -> None:
    result = calculate_gage_run_chart(
        _balanced_rows(),
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
        point_limit=5,
    )

    assert result["order_source"] == "canonical_row_order"
    assert result["chart"]["point_count"] == 12
    assert result["chart"]["points_truncated"] is True
    assert len(result["chart"]["points"]) == 5
    assert result["chart"]["points"][0]["canonical_position"] == 1
    assert "gage_run_chart_uses_canonical_row_order" in result["warnings"]
    assert "gage_run_chart_points_truncated" in result["warnings"]


def test_gage_run_chart_rejects_invalid_designs_without_fake_points() -> None:
    with pytest.raises(GageRunChartError, match="gage_run_chart_unbalanced_crossed_design"):
        calculate_gage_run_chart(
            [
                ["10", "Part A", "Operator 1", "1"],
                ["11", "Part A", "Operator 1", "2"],
                ["12", "Part A", "Operator 2", "1"],
                ["13", "Part A", "Operator 2", "2"],
                ["14", "Part A", "Operator 2", "3"],
                ["20", "Part B", "Operator 1", "1"],
                ["21", "Part B", "Operator 1", "2"],
                ["22", "Part B", "Operator 2", "1"],
                ["23", "Part B", "Operator 2", "2"],
            ],
            measurement_column=_column("measurement", 0, data_type="decimal"),
            part_column=_column("part", 1, role="part_id"),
            operator_column=_column("operator", 2, role="operator_id"),
            replicate_column=_column("replicate", 3, role="replicate_id"),
        )

    with pytest.raises(GageRunChartError, match="gage_run_chart_replicate_count_too_small"):
        calculate_gage_run_chart(
            [
                ["10", "Part A", "Operator 1", "1"],
                ["12", "Part A", "Operator 2", "1"],
                ["20", "Part B", "Operator 1", "1"],
                ["22", "Part B", "Operator 2", "1"],
            ],
            measurement_column=_column("measurement", 0, data_type="decimal"),
            part_column=_column("part", 1, role="part_id"),
            operator_column=_column("operator", 2, role="operator_id"),
            replicate_column=_column("replicate", 3, role="replicate_id"),
        )


def _balanced_rows() -> list[list[str]]:
    return [
        ["9", "Part A", "Operator 1", "1", "2"],
        ["11", "Part A", "Operator 1", "2", "1"],
        ["15", "Part A", "Operator 2", "1", "4"],
        ["17", "Part A", "Operator 2", "2", "3"],
        ["20", "Part B", "Operator 1", "1", "6"],
        ["22", "Part B", "Operator 1", "2", "5"],
        ["24", "Part B", "Operator 2", "1", "8"],
        ["26", "Part B", "Operator 2", "2", "7"],
        ["31", "Part C", "Operator 1", "1", "10"],
        ["33", "Part C", "Operator 1", "2", "9"],
        ["33", "Part C", "Operator 2", "1", "12"],
        ["35", "Part C", "Operator 2", "2", "11"],
    ]


def _column(
    display_name: str,
    index: int,
    *,
    data_type: str = "text",
    role: str = "unspecified",
) -> GageRunChartColumn:
    return GageRunChartColumn(
        column_id=display_name,
        column_index=index,
        display_name=display_name,
        data_type=data_type,
        measurement_level="continuous" if data_type == "decimal" else "nominal",
        role=role,
        unit=None,
    )
