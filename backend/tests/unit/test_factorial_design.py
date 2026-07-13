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
NIST_REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/doe_factorial_design_reference.json",
)


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


def test_two_level_full_factorial_matches_nist_replicated_standard_order() -> None:
    fixture = json.loads(NIST_REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    case = fixture["reference_case"]
    factor_names = [factor["name"] for factor in case["factors"]]
    tolerance = fixture["tolerances"]["factor_levels_absolute"]

    assert fixture["source"]["organization"] == "NIST/SEMATECH"
    assert fixture["source"]["standard_order_url"].startswith(
        "https://www.itl.nist.gov/",
    )
    assert "NIST does not publish this checksum" in (fixture["conventions"]["application_checksum"])
    assert "does not provide responses" in fixture["conventions"]["analysis_limit"]

    design = generate_two_level_full_factorial_design(
        factors=[FactorialFactor(**factor) for factor in case["factors"]],
        options=FactorialDesignOptions(**case["options"]),
    )
    expected = case["expected_application_metadata"]

    assert design.schema_version == expected["schema_version"]
    assert design.family == expected["family"]
    assert len(design.runs) == expected["run_count"]
    assert [run.standard_order for run in design.runs] == expected["standard_orders"]
    assert [run.run_order for run in design.runs] == expected["run_orders"]
    assert [run.replicate_index for run in design.runs] == expected["replicate_indices"]
    assert [run.center_point for run in design.runs] == expected["center_points"]
    assert [run.block_index for run in design.runs] == expected["block_indices"]
    assert design.design_sha256 == expected["design_sha256"]

    first_replicate = design.runs[:8]
    second_replicate = design.runs[8:]
    actual_coded_order = [
        [run.coded_levels[name] for name in factor_names] for run in first_replicate
    ]
    actual_factor_order = [
        [run.factor_levels[name] for name in factor_names] for run in first_replicate
    ]
    assert actual_coded_order == case["published_coded_standard_order"]
    for actual, published in zip(
        actual_factor_order,
        case["published_factor_level_standard_order"],
        strict=True,
    ):
        assert actual == pytest.approx(published, abs=tolerance)
    assert [run.coded_levels for run in second_replicate] == [
        run.coded_levels for run in first_replicate
    ]
    assert [run.factor_levels for run in second_replicate] == [
        run.factor_levels for run in first_replicate
    ]


def test_two_level_full_factorial_nist_fixture_rejects_reversed_range() -> None:
    fixture = json.loads(NIST_REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    case = fixture["failure_case"]

    with pytest.raises(FactorialDesignError) as error:
        generate_two_level_full_factorial_design(
            factors=[FactorialFactor(**factor) for factor in case["factors"]],
            options=FactorialDesignOptions(**case["options"]),
        )

    assert error.value.code == case["expected_error"]


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
