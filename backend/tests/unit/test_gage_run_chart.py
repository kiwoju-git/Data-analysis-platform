import json
from pathlib import Path

import pytest

from app.statistics.gage_run_chart import (
    GageRunChartColumn,
    GageRunChartError,
    calculate_gage_run_chart,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/gage_run_chart_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/gage_run_chart_reference.json")
ORDERING_REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/quality_gage_run_chart_ordering_reference.json",
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


def test_gage_run_chart_matches_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        result = calculate_gage_run_chart(
            case["rows"],
            measurement_column=_column("measurement", 0, data_type="decimal"),
            part_column=_column("part", 1, role="part_id"),
            operator_column=_column("operator", 2, role="operator_id"),
            replicate_column=_column("replicate", 3, role="replicate_id"),
            order_column=_column("run", 4, data_type="integer", role="order"),
            point_limit=case["point_limit"],
        )
        expected = cases_by_id[case["case_id"]]

        _assert_numeric_mapping(result["summary"], expected["summary"])
        _assert_summary_rows(result["part_summaries"], expected["part_summaries"])
        _assert_summary_rows(result["operator_summaries"], expected["operator_summaries"])
        _assert_numeric_mapping(
            result["chart"]["points"][0],
            expected["first_chart_point"],
        )
        assert result["warnings"] == expected["warnings"]
        serialized = json.dumps(result, ensure_ascii=False)
        assert "Part A" not in serialized
        assert "Operator 1" not in serialized


def test_gage_run_chart_matches_hand_reviewed_ordering_reference() -> None:
    fixture = json.loads(ORDERING_REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    case = fixture["success_case"]
    expected = case["expected"]
    tolerance = fixture["tolerances"]["numeric_absolute"]

    assert fixture["source"]["type"] == "internal_hand_reviewed_diagnostic_fixture"
    assert "synthetic" in fixture["source"]["license_review"]
    assert (
        "does not establish measurement-system acceptability"
        in (fixture["conventions"]["interpretation_limit"])
    )

    result = calculate_gage_run_chart(
        case["rows"],
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
        order_column=_column("run", 4, data_type="integer", role="order"),
        point_limit=case["point_limit"],
    )

    assert result["order_source"] == expected["order_source"]
    assert result["order_tie_breaker"] == expected["order_tie_breaker"]
    assert result["sample"] == expected["sample"]
    assert result["design"] == expected["design"]
    _assert_numeric_mapping(result["summary"], expected["summary"])

    chart = result["chart"]
    assert chart["point_count"] == expected["chart"]["point_count"]
    assert chart["points_truncated"] is expected["chart"]["points_truncated"]
    assert chart["point_limit"] == expected["chart"]["point_limit"]
    assert [point["position"] for point in chart["points"]] == [1, 2, 3, 4, 5]
    assert [point["canonical_position"] for point in chart["points"]] == (
        expected["chart"]["canonical_positions"]
    )
    assert [point["value"] for point in chart["points"]] == pytest.approx(
        expected["chart"]["values"],
        abs=tolerance,
    )
    assert [point["part_index"] for point in chart["points"]] == (expected["chart"]["part_indices"])
    assert [point["operator_index"] for point in chart["points"]] == (
        expected["chart"]["operator_indices"]
    )
    assert [point["replicate_index"] for point in chart["points"]] == (
        expected["chart"]["replicate_indices"]
    )
    assert result["warnings"] == expected["warnings"]

    serialized = json.dumps(result, ensure_ascii=False)
    for raw_label in expected["redacted_labels"]:
        assert raw_label not in serialized


def test_gage_run_chart_ordering_reference_rejects_duplicate_replicate() -> None:
    fixture = json.loads(ORDERING_REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    case = fixture["failure_case"]

    with pytest.raises(GageRunChartError, match=case["expected_error"]):
        calculate_gage_run_chart(
            case["rows"],
            measurement_column=_column("measurement", 0, data_type="decimal"),
            part_column=_column("part", 1, role="part_id"),
            operator_column=_column("operator", 2, role="operator_id"),
            replicate_column=_column("replicate", 3, role="replicate_id"),
        )


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


def _assert_summary_rows(
    actual_rows: object,
    expected_rows: list[dict[str, object]],
) -> None:
    assert isinstance(actual_rows, list)
    assert len(actual_rows) == len(expected_rows)
    for actual_row, expected_row in zip(actual_rows, expected_rows, strict=True):
        _assert_numeric_mapping(actual_row, expected_row)


def _assert_numeric_mapping(actual: object, expected: dict[str, object]) -> None:
    assert isinstance(actual, dict)
    for key, expected_value in expected.items():
        assert actual[key] == pytest.approx(expected_value, abs=1e-12)
