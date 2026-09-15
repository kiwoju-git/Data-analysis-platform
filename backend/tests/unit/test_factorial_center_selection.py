import json
from itertools import product
from pathlib import Path

import pytest

from app.statistics.factorial_analysis import (
    FactorialAnalysisError,
    FactorialAnalysisRun,
    calculate_factorial_analysis,
)
from app.statistics.term_block_model_selection import DoeSelectionOptions, DoeTermPolicy

REFERENCE = json.loads(
    (Path(__file__).parents[1] / "reference/fixtures/factorial_center_titer.json").read_text(
        encoding="utf-8"
    )
)


def titer_runs():
    names = [factor["name"] for factor in REFERENCE["factors"]]
    settings = [tuple(reversed(row)) for row in product((-1, 1), repeat=3)] + [(0, 0, 0)] * 3
    return [
        FactorialAnalysisRun(
            index + 1, index + 1, index >= 8, None, dict(zip(names, row, strict=True)), response
        )
        for index, (row, response) in enumerate(zip(settings, REFERENCE["responses"], strict=True))
    ]


def titer_analysis(options):
    return calculate_factorial_analysis(
        titer_runs(),
        [factor["name"] for factor in REFERENCE["factors"]],
        response_name="Titer",
        response_unit=None,
        model_selection=options,
    )


def test_supplied_full_model_reference():
    result = titer_analysis(DoeSelectionOptions())
    expected = REFERENCE["steps"][0]
    assert [term["coefficient"] for term in result["terms"]] == pytest.approx(
        expected["coefficients"], abs=1e-9, rel=1e-8
    )
    assert [term["p_value"] for term in result["terms"]] == pytest.approx(
        expected["p_values"], abs=1e-9, rel=1e-8
    )


def test_center_must_leave_before_ab_supplied_reference():
    result = titer_analysis(DoeSelectionOptions(method="backward_elimination"))
    selection = result["model_selection"]
    assert selection["removed_term_ids"] == REFERENCE["removed_term_ids"]
    assert selection["final_term_ids"] == [
        "factor_1",
        "factor_2",
        "factor_3",
        "factor_1:factor_3",
        "factor_2:factor_3",
    ]
    assert result["model_policy"]["center_curvature_included"] is False
    assert len(selection["steps"]) == 3
    for step, expected in zip(selection["steps"], REFERENCE["steps"], strict=True):
        assert step["residual_df"] == expected["residual_df"]
        assert step["residual_standard_error"] == pytest.approx(expected["s"], abs=1e-9)
        for metric in ("r_squared", "adjusted_r_squared", "predicted_r_squared", "press"):
            assert step[metric] == pytest.approx(expected[metric], abs=1e-9, rel=1e-8)
        assert step["mallows_cp"] == pytest.approx(expected["mallows_cp"], abs=1e-9)
        active_statistics = [
            term for term in step["term_statistics"] if term["status"] != "removed_this_step"
        ]
        assert [term["coefficient"] for term in active_statistics] == pytest.approx(
            expected["coefficients"], abs=1e-9
        )
        assert [term["p_value"] for term in active_statistics[1:]] == pytest.approx(
            expected["p_values"][1:], abs=1e-9
        )
    final_b = next(
        term for term in selection["steps"][-1]["term_statistics"] if term["term_id"] == "factor_2"
    )
    assert final_b["status"] == "retained_for_hierarchy"
    assert final_b["p_value"] > 0.05


def test_forced_center_reproduces_explicit_legacy_policy():
    result = titer_analysis(
        DoeSelectionOptions(
            method="backward_elimination",
            term_policies=(DoeTermPolicy("center_curvature", "forced"),),
        )
    )
    assert result["model_selection"]["removed_term_ids"] == ["factor_1:factor_2"]
    assert "center_curvature" in result["model_selection"]["fixed_term_ids"]
    assert result["model_policy"]["center_curvature_disposition"] == "forced"
    center = next(term for term in result["terms"] if term["kind"] == "curvature")
    assert center["p_value"] == pytest.approx(0.676363, abs=1e-6)


def test_excluded_center_matches_second_step_and_error_partition():
    result = titer_analysis(
        DoeSelectionOptions(term_policies=(DoeTermPolicy("center_curvature", "excluded"),))
    )
    selection = result["model_selection"]
    assert selection["initially_excluded_term_ids"] == ["center_curvature"]
    assert selection["removed_term_ids"] == []
    assert result["model_policy"]["center_curvature_included"] is False
    assert result["model_policy"]["center_curvature_disposition"] == "excluded"
    error = result["anova"]["lack_of_fit"]
    assert error["pure_error"]["df"] == 2
    assert error["pure_error"]["sum_squares"] == pytest.approx(0.031666666666666565)
    assert error["curvature_in_error"]["df"] == 1
    assert error["curvature_in_error"]["sum_squares"] == pytest.approx(0.0021878787878787)
    assert sum(
        error[key]["sum_squares"]
        for key in ("pure_error", "curvature_in_error", "non_curvature_lack_of_fit")
    ) == pytest.approx(result["anova"]["residual"]["sum_squares"])
    assert [term["coefficient"] for term in result["terms"]] == pytest.approx(
        REFERENCE["steps"][1]["coefficients"], abs=1e-9
    )


def test_manual_interaction_exclusion_does_not_reenter():
    result = titer_analysis(
        DoeSelectionOptions(term_policies=(DoeTermPolicy("factor_2:factor_3", "excluded"),))
    )
    selection = result["model_selection"]
    assert selection["initially_excluded_term_ids"] == ["factor_2:factor_3"]
    assert "factor_2:factor_3" not in selection["initial_term_ids"] + selection["final_term_ids"]
    assert selection["removed_term_ids"] == []


def test_parent_exclusion_rejected_and_structural_term_cannot_be_removed():
    for term_id in ("factor_1", "intercept"):
        with pytest.raises(FactorialAnalysisError):
            titer_analysis(DoeSelectionOptions(term_policies=(DoeTermPolicy(term_id, "excluded"),)))


def test_minimal_trace_still_records_center_removal():
    result = titer_analysis(
        DoeSelectionOptions(method="backward_elimination", display_step_details=False)
    )
    assert result["model_selection"]["steps"] == []
    assert result["model_policy"]["center_curvature_removed_step"] == 1
    assert result["model_selection"]["removed_term_ids"] == REFERENCE["removed_term_ids"]
