import json

from app.statistics.gage_rr_preflight import (
    GageRrColumn,
    calculate_gage_rr_preflight,
)


def test_gage_rr_preflight_accepts_balanced_crossed_design_without_fake_results() -> None:
    rows = [
        ["10.0", "Part A", "Operator 1", "1"],
        ["10.1", "Part A", "Operator 1", "2"],
        ["10.2", "Part A", "Operator 2", "1"],
        ["10.3", "Part A", "Operator 2", "2"],
        ["11.0", "Part B", "Operator 1", "1"],
        ["11.1", "Part B", "Operator 1", "2"],
        ["11.2", "Part B", "Operator 2", "1"],
        ["11.3", "Part B", "Operator 2", "2"],
        ["12.0", "Part C", "Operator 1", "1"],
        ["12.1", "Part C", "Operator 1", "2"],
        ["12.2", "Part C", "Operator 2", "1"],
        ["12.3", "Part C", "Operator 2", "2"],
    ]

    result = calculate_gage_rr_preflight(
        rows,
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
    )

    assert result["summary_type"] == "gage_rr_preflight"
    assert result["method"] == "balanced_crossed_anova_preflight"
    assert result["next_step"] == "ready_for_balanced_crossed_anova"
    assert result["sample"]["n_total"] == 12
    assert result["sample"]["n_used"] == 12
    assert result["design"] == {
        "design_type": "crossed",
        "balanced": True,
        "ready_for_anova": True,
        "part_count": 3,
        "operator_count": 2,
        "replicate_level_count": 2,
        "expected_cell_count": 6,
        "observed_cell_count": 6,
        "missing_cell_count": 0,
        "min_replicates_per_cell": 2,
        "max_replicates_per_cell": 2,
        "expected_replicates_per_cell": 2,
        "replicate_set_consistent": True,
        "duplicate_replicates_per_cell": 0,
        "cell_replicate_count_distribution": [{"replicate_count": 2, "cell_count": 6}],
    }
    assert "anova_table" not in result
    assert "variance_components" not in result
    assert "percent_gage_rr" not in result
    assert "ndc" not in result


def test_gage_rr_preflight_reports_unbalanced_design_without_raw_labels() -> None:
    rows = [
        ["10.0", "Part A", "Operator 1", "1"],
        ["10.1", "Part A", "Operator 1", "2"],
        ["10.2", "Part A", "Operator 2", "1"],
        ["bad", "Part A", "Operator 2", "2"],
        ["11.0", "Part B", "Operator 1", "1"],
        ["11.1", "Part B", "Operator 1", "1"],
    ]

    result = calculate_gage_rr_preflight(
        rows,
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
    )

    assert result["next_step"] == "fix_design_before_gage_rr"
    assert result["design"]["ready_for_anova"] is False
    issue_codes = [issue["code"] for issue in result["issues"]]
    assert "gage_rr_crossed_cells_missing" in issue_codes
    assert "gage_rr_unbalanced_crossed_design" in issue_codes
    assert "gage_rr_duplicate_replicates_per_cell" in issue_codes
    assert "non_numeric_values_excluded" in issue_codes
    serialized = json.dumps(result, ensure_ascii=False)
    assert "Part A" not in serialized
    assert "Operator 1" not in serialized


def _column(
    column_id: str,
    column_index: int,
    *,
    data_type: str = "text",
    role: str = "unspecified",
) -> GageRrColumn:
    return GageRrColumn(
        column_id=column_id,
        column_index=column_index,
        display_name=column_id,
        data_type=data_type,
        measurement_level="continuous" if data_type == "decimal" else "nominal",
        role=role,
        unit=None,
    )
