import json
from pathlib import Path

import pytest

from app.statistics.factorial_design import (
    FactorialDesignError,
    FactorialDesignOptions,
    FactorialFactor,
    generate_two_level_full_factorial_design,
    run_to_payload,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/factorial_design_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/factorial_design_reference.json")


def test_two_level_full_factorial_standard_order_and_center_point() -> None:
    design = generate_two_level_full_factorial_design(
        factors=[
            FactorialFactor(name="Temperature", low=100.0, high=120.0, unit="C"),
            FactorialFactor(name="Pressure", low=10.0, high=30.0, unit="bar"),
        ],
        options=FactorialDesignOptions(
            replicates=1,
            center_points=1,
            randomize=False,
            randomization_seed=42,
        ),
    )

    assert design.family == "two_level_full_factorial"
    assert len(design.runs) == 5
    assert [run.run_order for run in design.runs] == [1, 2, 3, 4, 5]
    assert [run.standard_order for run in design.runs] == [1, 2, 3, 4, 5]
    assert design.runs[0].coded_levels == {"Temperature": -1, "Pressure": -1}
    assert design.runs[1].factor_levels == {"Temperature": 120.0, "Pressure": 10.0}
    assert design.runs[2].factor_levels == {"Temperature": 100.0, "Pressure": 30.0}
    assert design.runs[4].center_point is True
    assert design.runs[4].coded_levels == {"Temperature": 0, "Pressure": 0}
    assert design.runs[4].factor_levels == {"Temperature": 110.0, "Pressure": 20.0}
    assert len(design.design_sha256) == 64


def test_two_level_full_factorial_same_seed_reproduces_run_order() -> None:
    factors = [
        FactorialFactor(name="A", low=-1.0, high=1.0),
        FactorialFactor(name="B", low=5.0, high=9.0),
        FactorialFactor(name="C", low=0.0, high=10.0),
    ]
    options = FactorialDesignOptions(
        replicates=2,
        center_points=2,
        randomize=True,
        randomization_seed=20260702,
        block_count=2,
    )

    first = generate_two_level_full_factorial_design(factors=factors, options=options)
    second = generate_two_level_full_factorial_design(factors=factors, options=options)

    assert [run.standard_order for run in first.runs] == [run.standard_order for run in second.runs]
    assert [run.replicate_index for run in first.runs] == [
        run.replicate_index for run in second.runs
    ]
    assert [run.block_index for run in first.runs[:4]] == [1, 2, 1, 2]
    assert first.design_sha256 == second.design_sha256


def test_two_level_full_factorial_matches_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        design = generate_two_level_full_factorial_design(
            factors=[
                FactorialFactor(
                    name=factor["name"],
                    low=factor["low"],
                    high=factor["high"],
                    unit=factor["unit"],
                )
                for factor in case["factors"]
            ],
            options=FactorialDesignOptions(**case["options"]),
        )
        expected = cases_by_id[case["case_id"]]

        assert design.design_sha256 == expected["design_sha256"]
        if "runs" in expected:
            assert [run_to_payload(run) for run in design.runs] == expected["runs"]
        if "run_order_summary" in expected:
            assert [
                {
                    "run_order": run.run_order,
                    "standard_order": run.standard_order,
                    "replicate_index": run.replicate_index,
                    "block_index": run.block_index,
                    "center_point": run.center_point,
                }
                for run in design.runs
            ] == expected["run_order_summary"]


def test_two_level_full_factorial_rejects_invalid_designs() -> None:
    with pytest.raises(FactorialDesignError) as duplicate_error:
        generate_two_level_full_factorial_design(
            factors=[
                FactorialFactor(name="A", low=0.0, high=1.0),
                FactorialFactor(name="a", low=0.0, high=1.0),
            ],
            options=FactorialDesignOptions(
                replicates=1,
                center_points=0,
                randomize=False,
                randomization_seed=1,
            ),
        )
    assert duplicate_error.value.code == "doe_factorial_factor_names_not_unique"

    with pytest.raises(FactorialDesignError) as range_error:
        generate_two_level_full_factorial_design(
            factors=[
                FactorialFactor(name="A", low=1.0, high=1.0),
                FactorialFactor(name="B", low=0.0, high=1.0),
            ],
            options=FactorialDesignOptions(
                replicates=1,
                center_points=0,
                randomize=False,
                randomization_seed=1,
            ),
        )
    assert range_error.value.code == "doe_factorial_factor_range_invalid"

    with pytest.raises(FactorialDesignError) as run_limit_error:
        generate_two_level_full_factorial_design(
            factors=[
                FactorialFactor(name="A", low=0.0, high=1.0),
                FactorialFactor(name="B", low=0.0, high=1.0),
                FactorialFactor(name="C", low=0.0, high=1.0),
                FactorialFactor(name="D", low=0.0, high=1.0),
                FactorialFactor(name="E", low=0.0, high=1.0),
                FactorialFactor(name="F", low=0.0, high=1.0),
            ],
            options=FactorialDesignOptions(
                replicates=5,
                center_points=0,
                randomize=False,
                randomization_seed=1,
            ),
        )
    assert run_limit_error.value.code == "doe_factorial_run_count_exceeds_limit"
