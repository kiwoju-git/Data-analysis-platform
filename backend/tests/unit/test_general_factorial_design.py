from itertools import product

import pytest

from app.statistics.general_factorial_analysis import (
    GeneralFactorialAnalysisRun,
    calculate_general_factorial_analysis,
)
from app.statistics.general_factorial_design import (
    GeneralFactorialDesignError,
    GeneralFactorialFactor,
    GeneralFactorialOptions,
    generate_general_full_factorial_design,
)


def test_three_by_three_by_three_design_has_27_unique_runs() -> None:
    design = generate_general_full_factorial_design(
        [
            GeneralFactorialFactor("Temperature", (60.0, 70.0, 80.0), "C"),
            GeneralFactorialFactor("Pressure", (5.0, 10.0, 15.0), "bar"),
            GeneralFactorialFactor("Material", ("A", "B", "C")),
        ],
        GeneralFactorialOptions(
            replicates=1,
            randomize=False,
            randomization_seed=20260806,
            max_interaction_order=2,
        ),
    )

    assert len(design.runs) == 27
    assert len({tuple(run.factor_levels.values()) for run in design.runs}) == 27
    assert design.runs[0].factor_levels == {
        "Temperature": 60.0,
        "Pressure": 5.0,
        "Material": "A",
    }


@pytest.mark.parametrize("level_count", [2, 4, 10])
def test_general_factorial_supports_explicit_level_counts_and_preserves_order(
    level_count: int,
) -> None:
    levels = tuple(float(index) for index in range(level_count, 0, -1))
    design = generate_general_full_factorial_design(
        [
            GeneralFactorialFactor("Dose", levels),
            GeneralFactorialFactor("Material", ("B", "A")),
        ],
        GeneralFactorialOptions(1, False, 3, 2),
    )

    assert len(design.runs) == level_count * 2
    assert design.factors[0].levels == levels
    assert design.runs[0].factor_levels == {"Dose": float(level_count), "Material": "B"}


def test_general_factorial_mixed_two_by_three_by_five_has_30_runs() -> None:
    design = generate_general_full_factorial_design(
        [
            GeneralFactorialFactor("A", (10.0, 20.0)),
            GeneralFactorialFactor("B", ("C", "A", "B")),
            GeneralFactorialFactor("C", (1.0, 2.0, 3.0, 4.0, 5.0)),
        ],
        GeneralFactorialOptions(1, False, 19, 3),
    )

    assert len(design.runs) == 30
    assert design.runs[0].factor_levels == {"A": 10.0, "B": "C", "C": 1.0}


def test_general_factorial_rejects_mixed_numeric_and_text_levels_within_factor() -> None:
    with pytest.raises(GeneralFactorialDesignError) as error:
        generate_general_full_factorial_design(
            [
                GeneralFactorialFactor("Mixed", (1.0, "High")),
                GeneralFactorialFactor("B", ("x", "y")),
            ],
            GeneralFactorialOptions(1, False, 1, 2),
        )

    assert error.value.code == "doe_general_factorial_level_types_mixed"


@pytest.mark.parametrize(
    ("levels", "expected_code"),
    [
        (("", "A"), "doe_general_factorial_level_invalid"),
        ((1.0, 1.0), "doe_general_factorial_levels_not_unique"),
    ],
)
def test_general_factorial_rejects_blank_or_duplicate_levels(
    levels: tuple[float | str, ...],
    expected_code: str,
) -> None:
    with pytest.raises(GeneralFactorialDesignError) as error:
        generate_general_full_factorial_design(
            [GeneralFactorialFactor("A", levels), GeneralFactorialFactor("B", ("x", "y"))],
            GeneralFactorialOptions(1, False, 1, 2),
        )

    assert error.value.code == expected_code


def test_general_factorial_accepts_exact_256_run_boundary() -> None:
    design = generate_general_full_factorial_design(
        [GeneralFactorialFactor(f"F{index}", (0.0, 1.0, 2.0, 3.0)) for index in range(4)],
        GeneralFactorialOptions(1, False, 1, 2),
    )

    assert len(design.runs) == 256


def test_general_factorial_run_limit_is_rejected() -> None:
    with pytest.raises(GeneralFactorialDesignError) as error:
        generate_general_full_factorial_design(
            [GeneralFactorialFactor(f"F{index}", tuple(range(5))) for index in range(4)],
            GeneralFactorialOptions(1, False, 1, 2),
        )
    assert error.value.code == "doe_general_factorial_run_count_exceeds_limit"


def test_general_factorial_anova_uses_term_blocks_and_treatment_coding() -> None:
    levels = {"A": ("low", "middle", "high"), "B": ("x", "y")}
    runs: list[GeneralFactorialAnalysisRun] = []
    run_order = 0
    for replicate in range(2):
        for a_index, b_index in product(range(3), range(2)):
            run_order += 1
            response = 10.0 + 3.0 * a_index + 2.0 * b_index + 0.1 * replicate
            runs.append(
                GeneralFactorialAnalysisRun(
                    run_order=run_order,
                    level_indices={"A": a_index, "B": b_index},
                    factor_levels={"A": levels["A"][a_index], "B": levels["B"][b_index]},
                    response=response,
                )
            )

    result = calculate_general_factorial_analysis(
        runs,
        levels,
        response_name="Yield",
        response_unit="%",
        max_interaction_order=2,
    )

    rows = {row["term_id"]: row for row in result["anova"]["rows"]}
    assert rows["A"]["df"] == 2
    assert rows["B"]["df"] == 1
    assert rows["A:B"]["df"] == 2
    assert result["coding"]["policy"] == "treatment"
    assert result["anova"]["pure_error"]["df"] == 6
    assert len(result["group_means"]) == 6
