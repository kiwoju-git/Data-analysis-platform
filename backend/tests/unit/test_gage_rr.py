import json
from pathlib import Path

import pytest

from app.statistics.gage_rr import GageRrError, calculate_gage_rr_anova
from app.statistics.gage_rr_preflight import GageRrColumn

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/gage_rr_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/gage_rr_reference.json")


def test_gage_rr_balanced_crossed_anova_matches_hand_checkable_fixture() -> None:
    result = calculate_gage_rr_anova(
        _balanced_interaction_rows(),
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
    )

    assert result["summary_type"] == "gage_rr"
    assert result["method"] == "balanced_crossed_anova"
    assert result["sample"]["n_total"] == 12
    assert result["sample"]["n_used"] == 12
    assert result["design"]["part_count"] == 3
    assert result["design"]["operator_count"] == 2
    assert result["design"]["replicate_count"] == 2

    anova_rows = {row["source"]: row for row in result["anova_table"]}
    assert anova_rows["part"]["degrees_of_freedom"] == 2
    assert anova_rows["part"]["sum_of_squares"] == pytest.approx(800)
    assert anova_rows["part"]["mean_square"] == pytest.approx(400)
    assert anova_rows["part"]["f_statistic"] == pytest.approx(100)
    assert anova_rows["part"]["p_value"] == pytest.approx(0.009900990099009901)
    assert anova_rows["operator"]["degrees_of_freedom"] == 1
    assert anova_rows["operator"]["sum_of_squares"] == pytest.approx(48)
    assert anova_rows["operator"]["mean_square"] == pytest.approx(48)
    assert anova_rows["operator"]["f_statistic"] == pytest.approx(12)
    assert anova_rows["operator"]["p_value"] == pytest.approx(0.07417990022744853)
    assert anova_rows["part_operator"]["degrees_of_freedom"] == 2
    assert anova_rows["part_operator"]["sum_of_squares"] == pytest.approx(8)
    assert anova_rows["part_operator"]["mean_square"] == pytest.approx(4)
    assert anova_rows["part_operator"]["f_statistic"] == pytest.approx(2)
    assert anova_rows["part_operator"]["p_value"] == pytest.approx(0.216)
    assert anova_rows["repeatability"]["degrees_of_freedom"] == 6
    assert anova_rows["repeatability"]["sum_of_squares"] == pytest.approx(12)
    assert anova_rows["repeatability"]["mean_square"] == pytest.approx(2)
    assert anova_rows["total"]["sum_of_squares"] == pytest.approx(868)

    components = result["variance_components"]
    assert components["repeatability"]["raw_variance"] == pytest.approx(2)
    assert components["operator"]["raw_variance"] == pytest.approx(44 / 6)
    assert components["part_operator"]["raw_variance"] == pytest.approx(1)
    assert components["reproducibility"]["final_variance"] == pytest.approx(25 / 3)
    assert components["total_gage_rr"]["final_variance"] == pytest.approx(31 / 3)
    assert components["part_to_part"]["raw_variance"] == pytest.approx(99)
    assert components["total_variation"]["final_variance"] == pytest.approx(328 / 3)
    assert components["total_gage_rr"]["percent_contribution"] == pytest.approx(
        9.451219512195122,
    )
    assert components["part_to_part"]["percent_contribution"] == pytest.approx(
        90.54878048780488,
    )
    assert components["total_gage_rr"]["percent_study_variation"] == pytest.approx(
        30.742835770623245,
    )
    assert components["ndc"] == 4
    assert components["negative_component_policy"] == (
        "raw_estimate_reported_final_variance_clamped_to_zero"
    )
    assert components["interaction_policy"] == "preserve_part_operator_interaction_no_pooling"
    assert "gage_rr_negative_variance_component_clamped" not in result["warnings"]
    serialized = json.dumps(result, ensure_ascii=False)
    assert "Part A" not in serialized
    assert "Operator 1" not in serialized


def test_gage_rr_reports_negative_raw_component_and_clamps_final_variance() -> None:
    result = calculate_gage_rr_anova(
        _balanced_additive_rows(),
        measurement_column=_column("measurement", 0, data_type="decimal"),
        part_column=_column("part", 1, role="part_id"),
        operator_column=_column("operator", 2, role="operator_id"),
        replicate_column=_column("replicate", 3, role="replicate_id"),
    )

    components = result["variance_components"]
    assert components["part_operator"]["raw_variance"] == pytest.approx(-1)
    assert components["part_operator"]["final_variance"] == 0
    assert components["part_operator"]["clamped_to_zero"] is True
    assert "gage_rr_negative_variance_component_clamped" in result["warnings"]


def test_gage_rr_matches_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        result = calculate_gage_rr_anova(
            case["rows"],
            measurement_column=_column("measurement", 0, data_type="decimal"),
            part_column=_column("part", 1, role="part_id"),
            operator_column=_column("operator", 2, role="operator_id"),
            replicate_column=_column("replicate", 3, role="replicate_id"),
        )
        expected = cases_by_id[case["case_id"]]
        anova_rows = {row["source"]: row for row in result["anova_table"]}

        for source, expected_row in expected["anova"].items():
            actual_row = anova_rows[source]
            assert actual_row["degrees_of_freedom"] == expected_row["df"]
            assert actual_row["sum_of_squares"] == pytest.approx(
                expected_row["ss"],
                abs=1e-12,
            )
            if "ms" in expected_row:
                assert actual_row["mean_square"] == pytest.approx(
                    expected_row["ms"],
                    abs=1e-12,
                )
            _assert_optional_approx(actual_row["f_statistic"], expected_row.get("f"))
            _assert_optional_approx(actual_row["p_value"], expected_row.get("p"))

        components = result["variance_components"]
        for component_name, expected_component in expected["variance_components"].items():
            if component_name == "ndc":
                assert components["ndc"] == expected_component
                continue
            actual_component = components[component_name]
            for key, expected_value in expected_component.items():
                if isinstance(expected_value, bool):
                    assert actual_component[key] is expected_value
                else:
                    assert actual_component[key] == pytest.approx(expected_value, abs=1e-12)
        assert result["warnings"] == expected["warnings"]


def test_gage_rr_rejects_invalid_designs_without_fake_components() -> None:
    with pytest.raises(GageRrError, match="gage_rr_unbalanced_crossed_design"):
        calculate_gage_rr_anova(
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

    with pytest.raises(GageRrError, match="gage_rr_zero_total_variation"):
        calculate_gage_rr_anova(
            [
                ["10", "Part A", "Operator 1", "1"],
                ["10", "Part A", "Operator 1", "2"],
                ["10", "Part A", "Operator 2", "1"],
                ["10", "Part A", "Operator 2", "2"],
                ["10", "Part B", "Operator 1", "1"],
                ["10", "Part B", "Operator 1", "2"],
                ["10", "Part B", "Operator 2", "1"],
                ["10", "Part B", "Operator 2", "2"],
            ],
            measurement_column=_column("measurement", 0, data_type="decimal"),
            part_column=_column("part", 1, role="part_id"),
            operator_column=_column("operator", 2, role="operator_id"),
            replicate_column=_column("replicate", 3, role="replicate_id"),
        )


def _balanced_interaction_rows() -> list[list[str]]:
    return [
        ["9", "Part A", "Operator 1", "1"],
        ["11", "Part A", "Operator 1", "2"],
        ["15", "Part A", "Operator 2", "1"],
        ["17", "Part A", "Operator 2", "2"],
        ["20", "Part B", "Operator 1", "1"],
        ["22", "Part B", "Operator 1", "2"],
        ["24", "Part B", "Operator 2", "1"],
        ["26", "Part B", "Operator 2", "2"],
        ["31", "Part C", "Operator 1", "1"],
        ["33", "Part C", "Operator 1", "2"],
        ["33", "Part C", "Operator 2", "1"],
        ["35", "Part C", "Operator 2", "2"],
    ]


def _balanced_additive_rows() -> list[list[str]]:
    return [
        ["10", "Part A", "Operator 1", "1"],
        ["12", "Part A", "Operator 1", "2"],
        ["14", "Part A", "Operator 2", "1"],
        ["16", "Part A", "Operator 2", "2"],
        ["20", "Part B", "Operator 1", "1"],
        ["22", "Part B", "Operator 1", "2"],
        ["24", "Part B", "Operator 2", "1"],
        ["26", "Part B", "Operator 2", "2"],
        ["30", "Part C", "Operator 1", "1"],
        ["32", "Part C", "Operator 1", "2"],
        ["34", "Part C", "Operator 2", "1"],
        ["36", "Part C", "Operator 2", "2"],
    ]


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


def _assert_optional_approx(actual: object, expected: object) -> None:
    if expected is None:
        assert actual is None
    else:
        assert actual == pytest.approx(expected, abs=1e-12)
