import json
from pathlib import Path

import pytest

from app.statistics.factorial_analysis import (
    FactorialAnalysisError,
    FactorialAnalysisRun,
    calculate_factorial_analysis,
)

REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/doe_factorial_analysis_nist_reference.json"
)


def test_full_three_factor_model_matches_nist_yates_coefficients_without_fake_inference() -> None:
    fixture = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    runs = _full_factorial_runs(fixture["factor_names"], fixture["responses_yates_order"])

    result = calculate_factorial_analysis(
        runs,
        fixture["factor_names"],
        response_name="Eddy current",
        response_unit=None,
        max_interaction_order=3,
    )

    terms = {term["term_id"]: term for term in result["terms"]}
    for term_id, expected in fixture["expected_coefficients"].items():
        assert terms[term_id]["coefficient"] == pytest.approx(expected, abs=1e-12)
    assert result["sample"]["df_residual"] == fixture["expected_residual_df"]
    assert result["fit"]["residual_mean_square"] is None
    assert all(term["p_value"] is None for term in result["terms"])
    assert "doe_factorial_model_saturated_no_inference" in result["warnings"]


def test_factor_effect_is_twice_coefficient_and_hierarchy_is_forced() -> None:
    runs = _replicated_two_factor_runs()

    result = calculate_factorial_analysis(
        runs,
        ["A", "B"],
        response_name="Yield",
        response_unit="kg",
        max_interaction_order=2,
    )

    terms = {term["term_id"]: term for term in result["terms"]}
    assert list(terms) == [
        "intercept",
        "factor_1",
        "factor_2",
        "factor_1:factor_2",
        "center_curvature",
    ]
    assert terms["factor_1"]["coefficient"] == pytest.approx(2.0, abs=1e-12)
    assert terms["factor_1"]["effect"] == pytest.approx(4.0, abs=1e-12)
    assert terms["factor_1:factor_2"]["coefficient"] == pytest.approx(3.0, abs=1e-12)
    assert result["model_policy"]["hierarchy_enforced"] is True
    assert result["anova"]["lack_of_fit"]["pure_error"]["df"] == 6
    assert result["anova"]["lack_of_fit"]["lack_of_fit"]["df"] == 0


def test_main_effect_model_partitions_significant_interaction_lack_of_fit() -> None:
    result = calculate_factorial_analysis(
        _replicated_two_factor_runs(),
        ["A", "B"],
        response_name="Yield",
        response_unit="kg",
        max_interaction_order=1,
    )

    lack_of_fit = result["anova"]["lack_of_fit"]
    assert lack_of_fit["available"] is True
    assert lack_of_fit["pure_error"]["df"] == 6
    assert lack_of_fit["lack_of_fit"]["df"] == 1
    assert lack_of_fit["lack_of_fit"]["f_statistic"] > 1000
    assert lack_of_fit["lack_of_fit"]["p_value"] < 1e-6
    assert "doe_factorial_higher_order_interactions_excluded_by_policy" in result["warnings"]


def test_factorial_analysis_returns_effect_and_residual_plot_payloads() -> None:
    result = calculate_factorial_analysis(
        _replicated_two_factor_runs(),
        ["A", "B"],
        response_name="Yield",
        response_unit=None,
        max_interaction_order=2,
        point_limit=5,
    )

    assert [item["factor"] for item in result["plots"]["main_effects"]] == ["A", "B"]
    assert result["plots"]["interactions"][0]["first_factor"] == "A"
    assert len(result["plots"]["interactions"][0]["cells"]) == 4
    assert result["diagnostics"]["points_truncated"] is True
    assert len(result["diagnostics"]["points"]) == 5
    assert len(result["diagnostics"]["qq_points"]) == 5


def test_factorial_analysis_preserves_small_scale_nonconstant_response() -> None:
    runs = _full_factorial_runs(
        ["A", "B"],
        [1.0e-10, 2.0e-10, 3.0e-10, 5.0e-10],
    )

    result = calculate_factorial_analysis(
        runs,
        ["A", "B"],
        response_name="Small signal",
        response_unit="V",
        max_interaction_order=2,
    )

    assert result["fit"]["total_ss"] > 0
    assert result["sample"]["df_residual"] == 0


@pytest.mark.parametrize(
    ("runs", "error"),
    [
        (
            [
                FactorialAnalysisRun(1, 1, False, None, {"A": -1, "B": -1}, 3.0),
                FactorialAnalysisRun(2, 2, False, None, {"A": 1, "B": -1}, 3.0),
            ],
            "doe_factorial_response_variance_zero",
        ),
        (
            [
                FactorialAnalysisRun(1, 1, True, None, {"A": -1, "B": 0}, 1.0),
                FactorialAnalysisRun(2, 2, False, None, {"A": 1, "B": -1}, 2.0),
            ],
            "doe_factorial_center_coding_invalid",
        ),
    ],
)
def test_factorial_analysis_rejects_invalid_data_without_fallback(
    runs: list[FactorialAnalysisRun], error: str
) -> None:
    with pytest.raises(FactorialAnalysisError, match=error):
        calculate_factorial_analysis(
            runs,
            ["A", "B"],
            response_name="Yield",
            response_unit=None,
        )


def _full_factorial_runs(
    factor_names: list[str], responses: list[float]
) -> list[FactorialAnalysisRun]:
    runs = []
    for offset, response in enumerate(responses):
        runs.append(
            FactorialAnalysisRun(
                run_order=offset + 1,
                standard_order=offset + 1,
                center_point=False,
                block_index=None,
                coded_levels={
                    name: 1 if (offset >> factor_index) & 1 else -1
                    for factor_index, name in enumerate(factor_names)
                },
                response=response,
            )
        )
    return runs


def _replicated_two_factor_runs() -> list[FactorialAnalysisRun]:
    runs: list[FactorialAnalysisRun] = []
    run_order = 1
    for _replicate, noise in ((1, -0.1), (2, 0.1)):
        for offset in range(4):
            a = 1 if offset & 1 else -1
            b = 1 if offset & 2 else -1
            runs.append(
                FactorialAnalysisRun(
                    run_order=run_order,
                    standard_order=offset + 1,
                    center_point=False,
                    block_index=None,
                    coded_levels={"A": a, "B": b},
                    response=10 + (2 * a) - b + (3 * a * b) + noise,
                )
            )
            run_order += 1
    for center_offset, noise in enumerate((-0.1, 0.0, 0.1), start=1):
        runs.append(
            FactorialAnalysisRun(
                run_order=run_order,
                standard_order=4 + center_offset,
                center_point=True,
                block_index=None,
                coded_levels={"A": 0, "B": 0},
                response=10 + noise,
            )
        )
        run_order += 1
    return runs
