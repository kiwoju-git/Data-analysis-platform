from __future__ import annotations

import numpy as np
import pytest

from app.statistics.factorial_analysis import (
    FactorialAnalysisError,
    FactorialAnalysisRun,
    calculate_factorial_analysis,
)
from app.statistics.factorial_design import (
    FactorialDesignOptions,
    FactorialFactor,
    generate_two_level_factorial_design,
)
from app.statistics.term_block_model_selection import DoeSelectionOptions, DoeTermPolicy


def _runs(
    count: int,
    *,
    centers: int = 0,
    replicates: int = 1,
    blocks: int = 1,
) -> list[FactorialAnalysisRun]:
    factors = [
        FactorialFactor(name=chr(65 + index), low=-1, high=1, unit=None) for index in range(count)
    ]
    design = generate_two_level_factorial_design(
        factors,
        FactorialDesignOptions(
            replicates=replicates,
            center_points=centers,
            randomize=False,
            randomization_seed=7,
            block_count=blocks,
            design_type="two_level_fractional",
            fraction_id={3: "3-factor-half-r3", 4: "4-factor-half-r4", 5: "5-factor-half-r5"}[
                count
            ],
        ),
    )
    return [
        FactorialAnalysisRun(
            run.run_order,
            run.standard_order,
            run.center_point,
            run.block_index,
            run.coded_levels,
            10
            + 2 * run.coded_levels["A"]
            - run.coded_levels["B"]
            + 0.4 * run.coded_levels["A"] * run.coded_levels["B"]
            + ((run.run_order * 17) % 11) * 0.023,
        )
        for run in design.runs
    ]


def _calculate(count: int, options: DoeSelectionOptions | None = None, **kwargs):
    return calculate_factorial_analysis(
        _runs(count, **kwargs),
        [chr(65 + index) for index in range(count)],
        response_name="Synthetic",
        response_unit=None,
        max_interaction_order=2,
        regular_fraction=True,
        model_selection=options or DoeSelectionOptions(),
    )


def test_five_factor_half_fraction_really_fits_second_order_saturated_model() -> None:
    result = _calculate(5)
    assert result["sample"]["rank"] == result["sample"]["parameter_count"] == 16
    assert result["sample"]["df_residual"] == 0
    assert sum(term["kind"] == "interaction" for term in result["terms"]) == 10
    assert result["estimability"]["exclusions"] == []
    assert result["model_selection"]["removed_term_ids"] == []
    assert result["model_policy"]["requested_interaction_order"] == 2
    assert result["model_policy"]["effective_interaction_order"] == 2
    assert all(term["p_value"] is None for term in result["terms"])


def test_structural_block_span_is_not_mislabeled_as_an_unexplained_rank_dependency() -> None:
    result = _calculate(4, blocks=2)
    plan = result["estimability"]
    assert plan["rank"] == 8
    exclusion = next(item for item in plan["exclusions"] if item["term_id"] == "factor_1")
    assert exclusion["reason"] == "structural_confounding"
    # The block contrast uses intercept and a 0/1 indicator, not one signed column.
    assert exclusion["representative_term_id"] is None


def test_saturated_fraction_backward_uses_disclosed_pooling_before_p_values() -> None:
    result = _calculate(5, DoeSelectionOptions(method="backward_elimination"))
    selection = result["model_selection"]
    assert selection["initial_residual_df"] == 0
    assert selection["target_pool_count"] == 4
    assert len(selection["pooled_term_ids"]) == 4
    assert all(
        step["removal_p_value"] is None
        for step in selection["steps"]
        if step["phase"] == "initial_pooling"
    )
    assert result["sample"]["df_residual"] > 0


def test_four_factor_fraction_reports_one_representative_per_alias_pair() -> None:
    result = _calculate(4)
    plan = result["estimability"]
    assert plan["requested_parameter_count"] == 11
    assert plan["rank"] == plan["estimable_parameter_count"] == 8
    aliases = {row["term_id"]: row for row in plan["exclusions"]}
    assert aliases["factor_3:factor_4"]["representative_term_id"] == "factor_1:factor_2"
    assert aliases["factor_2:factor_4"]["representative_term_id"] == "factor_1:factor_3"
    assert aliases["factor_2:factor_3"]["representative_term_id"] == "factor_1:factor_4"
    assert all(row["reason"] == "complete_alias" and row["sign"] == 1 for row in aliases.values())
    assert not result["model_selection"]["removed_term_ids"]


def test_three_factor_fraction_discloses_main_interaction_confounding() -> None:
    result = _calculate(3)
    assert result["sample"]["rank"] == 4
    assert len(result["estimability"]["exclusions"]) == 3
    assert {row["representative_term_id"] for row in result["estimability"]["exclusions"]} == {
        "factor_1",
        "factor_2",
        "factor_3",
    }


def test_forced_alias_conflict_fails_and_forced_representative_precedes_defaults() -> None:
    with pytest.raises(FactorialAnalysisError, match="doe_fractional_forced_terms_conflict"):
        _calculate(
            4,
            DoeSelectionOptions(
                term_policies=(
                    DoeTermPolicy("factor_1:factor_2", "forced"),
                    DoeTermPolicy("factor_3:factor_4", "forced"),
                )
            ),
        )
    result = _calculate(
        4, DoeSelectionOptions(term_policies=(DoeTermPolicy("factor_3:factor_4", "forced"),))
    )
    assert "factor_3:factor_4" in result["estimability"]["representative_term_ids"]
    assert "factor_1:factor_2" not in result["estimability"]["representative_term_ids"]


def test_replication_and_centers_use_actual_matrix_and_basis_is_response_independent() -> None:
    result = _calculate(4, centers=3, replicates=2)
    assert result["sample"]["n_observations"] == 19
    assert result["sample"]["rank"] == 9
    assert result["sample"]["df_residual"] == 10
    runs = _runs(4, centers=3, replicates=2)
    alternate = calculate_factorial_analysis(
        [
            FactorialAnalysisRun(
                run.run_order,
                run.standard_order,
                run.center_point,
                run.block_index,
                run.coded_levels,
                float(np.sin(run.run_order)),
            )
            for run in runs
        ],
        list("ABCD"),
        response_name="Other",
        response_unit=None,
        regular_fraction=True,
        model_selection=DoeSelectionOptions(),
    )
    assert result["estimability"] == alternate["estimability"]
