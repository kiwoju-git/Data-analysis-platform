import json
from math import sqrt
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.analyses import AttributeControlChartOptions
from app.statistics.attribute_control_chart import (
    AttributeControlChartColumn,
    calculate_attribute_control_chart,
)

FIXTURE_PATH = Path(
    "backend/tests/reference/fixtures/quality_attribute_control_chart_phase_2_reference_policy.json"
)
CONTRACT_PATH = Path("docs/attribute_control_chart_phase_2_contract.md")


def test_phase_2_policy_fixture_matches_frozen_limit_formulas() -> None:
    fixture = _fixture()

    for case in fixture["cases"]:
        values, center, lcl, ucl = _evaluate_frozen_case(case)
        expected = case["expected"]

        assert center == pytest.approx(expected["center_line"], abs=1e-12)
        assert values == pytest.approx(expected["values"], abs=1e-12)
        assert lcl == pytest.approx(expected["lcl"], abs=1e-12)
        assert ucl == pytest.approx(expected["ucl"], abs=1e-12)
        assert _strict_signal_positions(values, lcl, ucl) == expected["strict_signal_positions"]


def test_phase_2_fixture_and_contract_keep_current_execution_phase_1_only() -> None:
    fixture = _fixture()
    current = fixture["current_executable"]
    proposed = fixture["proposed_executable"]

    assert METHOD_VERSIONS["quality.attribute_control_chart"] == current["method_version"]
    assert current == {
        "method_version": "0.1.0",
        "result_schema_version": 1,
        "phase": "phase_1_only",
    }
    assert proposed == {
        "method_version": "0.2.0",
        "result_schema_version": 2,
        "limit_set_schema_version": 1,
    }

    result = calculate_attribute_control_chart(
        [["1", "10"], ["2", "10"]],
        _column("count", 0),
        _column("sample-size", 1),
        chart_type="p",
        count_definition="defectives",
    )
    assert result["schema_version"] == current["result_schema_version"]
    assert result["control_limit_method"] == "phase_1_estimated_three_sigma"
    assert result["baseline"] == "all_filtered_valid_points"


@pytest.mark.parametrize("field,value", [("phase", "phase_2"), ("limit_set_id", "asset-1")])
def test_current_options_reject_unimplemented_phase_2_fields(field: str, value: str) -> None:
    payload: dict[str, object] = {
        "chart_type": "p",
        "count_definition": "defectives",
        "count_column_id": "count",
        "denominator_column_id": "sample-size",
        field: value,
    }

    with pytest.raises(ValidationError) as exc_info:
        AttributeControlChartOptions.model_validate(payload)

    assert exc_info.value.errors()[0]["type"] == "extra_forbidden"
    assert exc_info.value.errors()[0]["loc"] == (field,)


def test_phase_2_contract_reserves_immutable_dependency_and_version_policy() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")

    for required in (
        "method version `0.2.0`",
        "result schema `2`",
        "limit-set asset schema `1`",
        "app-created `limit_set_id`",
        "canonical payload SHA-256",
        "never falls",
        "attribute_control_chart_phase_2_np_sample_size_mismatch",
        "WECO/Nelson",
        "policy-adjusted formula parity",
    ):
        assert required in contract


def _evaluate_frozen_case(
    case: dict[str, Any],
) -> tuple[list[float], float, list[float], list[float]]:
    chart_type = case["chart_type"]
    baseline = case["baseline"]
    monitoring = case["monitoring"]
    baseline_counts = baseline["counts"]
    monitoring_counts = monitoring["counts"]

    if chart_type in {"p", "np", "u"}:
        baseline_denominators = baseline["denominators"]
        center_rate = sum(baseline_counts) / sum(baseline_denominators)
    else:
        center_rate = sum(baseline_counts) / len(baseline_counts)

    if chart_type == "p":
        denominators = monitoring["denominators"]
        values = [
            count / denominator
            for count, denominator in zip(monitoring_counts, denominators, strict=True)
        ]
        limits = [
            (
                max(0.0, center_rate - 3 * sqrt(center_rate * (1 - center_rate) / n)),
                min(1.0, center_rate + 3 * sqrt(center_rate * (1 - center_rate) / n)),
            )
            for n in denominators
        ]
        center = center_rate
    elif chart_type == "np":
        sample_size = baseline["denominators"][0]
        center = sample_size * center_rate
        spread = 3 * sqrt(sample_size * center_rate * (1 - center_rate))
        values = [float(count) for count in monitoring_counts]
        limits = [(max(0.0, center - spread), min(sample_size, center + spread))] * len(values)
    elif chart_type == "c":
        center = center_rate
        spread = 3 * sqrt(center)
        values = [float(count) for count in monitoring_counts]
        limits = [(max(0.0, center - spread), center + spread)] * len(values)
    else:
        denominators = monitoring["denominators"]
        center = center_rate
        values = [
            count / denominator
            for count, denominator in zip(monitoring_counts, denominators, strict=True)
        ]
        limits = [
            (
                max(0.0, center - 3 * sqrt(center / denominator)),
                center + 3 * sqrt(center / denominator),
            )
            for denominator in denominators
        ]

    return values, center, [limit[0] for limit in limits], [limit[1] for limit in limits]


def _strict_signal_positions(values: list[float], lcl: list[float], ucl: list[float]) -> list[int]:
    return [
        position
        for position, (value, lower, upper) in enumerate(zip(values, lcl, ucl, strict=True), 1)
        if value < lower or value > upper
    ]


def _column(column_id: str, column_index: int) -> AttributeControlChartColumn:
    return AttributeControlChartColumn(
        column_id=column_id,
        column_index=column_index,
        display_name=column_id,
        data_type="integer",
        measurement_level="count",
        role="measure",
        unit=None,
    )


def _fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
