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
    calculate_attribute_control_chart_phase_2,
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


def test_phase_2_fixture_and_registry_match_executable_contract() -> None:
    fixture = _fixture()
    current = fixture["current_executable"]

    assert METHOD_VERSIONS["quality.attribute_control_chart"] == current["method_version"]
    assert current == {
        "method_version": "0.3.0",
        "result_schema_version": 3,
        "limit_set_schema_version": 1,
    }


def test_phase_2_options_require_verified_limit_set_id() -> None:
    with pytest.raises(ValidationError):
        AttributeControlChartOptions.model_validate(
            {
                "phase": "phase_2",
                "chart_type": "p",
                "count_definition": "defectives",
                "count_column_id": "count",
                "denominator_column_id": "sample-size",
            }
        )


@pytest.mark.parametrize("case_index", [0, 1, 2, 3])
def test_executable_phase_2_matches_independent_policy_fixture(case_index: int) -> None:
    case = _fixture()["cases"][case_index]
    chart_type = case["chart_type"]
    monitoring = case["monitoring"]
    expected = case["expected"]
    denominators = monitoring.get("denominators")
    rows = [
        [str(count)] if denominators is None else [str(count), str(denominators[index])]
        for index, count in enumerate(monitoring["counts"])
    ]
    result = calculate_attribute_control_chart_phase_2(
        rows,
        _column("count", 0),
        None if denominators is None else _column("sample-size", 1),
        chart_type=chart_type,
        count_definition=case["count_definition"],
        frozen_center_line=expected["center_line"],
        fixed_sample_size=(case["baseline"]["denominators"][0] if chart_type == "np" else None),
        constant_opportunity_confirmed=chart_type == "c",
    )
    assert result["schema_version"] == 3
    assert result["phase"] == "phase_2"
    assert result["center_line"] == pytest.approx(expected["center_line"], abs=1e-12)
    assert [point["value"] for point in result["chart"]["points"]] == pytest.approx(
        expected["values"], abs=1e-12
    )
    assert [point["lcl"] for point in result["chart"]["points"]] == pytest.approx(
        expected["lcl"], abs=1e-12
    )
    assert [point["ucl"] for point in result["chart"]["points"]] == pytest.approx(
        expected["ucl"], abs=1e-12
    )
    assert [signal["position"] for signal in result["signals"]] == expected[
        "strict_signal_positions"
    ]


def test_phase_2_contract_reserves_immutable_dependency_and_version_policy() -> None:
    contract = CONTRACT_PATH.read_text(encoding="utf-8")

    for required in (
        "method version `0.3.0`",
        "result schema `3`",
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
