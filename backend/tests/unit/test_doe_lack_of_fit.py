import json
from itertools import product

import pytest
from scipy import stats

from app.statistics.doe_lack_of_fit import decompose_lack_of_fit
from app.statistics.factorial_analysis import FactorialAnalysisRun, calculate_factorial_analysis
from app.statistics.term_block_model_selection import DoeSelectionOptions, DoeTermPolicy


def _corners(replicates=2, identical=False, blocks=False):
    runs = []
    for index, values in enumerate(product((-1, 1), repeat=3)):
        for repeat in range(replicates):
            response = 20 + values[0] + 2 * values[0] * values[1]
            response += 0 if identical else (repeat - 0.5) * 0.2
            runs.append(
                FactorialAnalysisRun(
                    len(runs) + 1,
                    index + 1,
                    False,
                    repeat + 1 if blocks else 1,
                    dict(zip("ABC", values, strict=True)),
                    response,
                )
            )
    return runs


def _fit(runs, order=1, options=None):
    return calculate_factorial_analysis(
        runs,
        list("ABC"),
        response_name="Synthetic",
        response_unit="mm",
        max_interaction_order=order,
        model_selection=options or DoeSelectionOptions(),
    )


def test_zero_centers_with_replicated_corners_supports_lack_of_fit():
    result = _fit(_corners())
    lack = result["anova"]["lack_of_fit"]
    assert result["sample"]["df_residual"] == 12
    assert lack["unique_design_point_count"] == 8
    assert lack["pure_error"]["df"] == 8
    assert lack["lack_of_fit"]["df"] == 4
    assert lack["available"] is True
    # Orthogonal omitted AB contrast contributes 16*2^2; within pairs, 16*.1^2.
    assert lack["pure_error"]["sum_squares"] == pytest.approx(0.16, abs=1e-12)
    assert lack["lack_of_fit"]["sum_squares"] == pytest.approx(64, abs=1e-10)
    assert lack["lack_of_fit"]["f_statistic"] == pytest.approx(800, abs=1e-8)
    assert lack["lack_of_fit"]["p_value"] == pytest.approx(stats.f.sf(800, 4, 8), rel=1e-10)


@pytest.mark.parametrize(
    "runs,order,reason",
    [
        (_corners(1), 1, "no_replicated_design_points"),
        (_corners(2, identical=True), 1, "pure_error_variance_zero"),
        (_corners(2), 3, "no_lack_of_fit_df"),
        (_corners(2, blocks=True), 1, "no_replicated_design_points"),
    ],
)
def test_unavailable_inference_keeps_anova_decomposition(runs, order, reason):
    lack = _fit(runs, order)["anova"]["lack_of_fit"]
    assert lack["available"] is False
    assert lack["reason"] == reason
    assert lack["decomposition_available"] is True
    assert lack["lack_of_fit"]["f_statistic"] is None
    assert lack["lack_of_fit"]["p_value"] is None
    assert lack["lack_of_fit"]["sum_squares"] is not None


def test_backward_recomputes_final_rank_without_merging_physical_conditions():
    result = _fit(
        _corners(),
        2,
        DoeSelectionOptions(
            method="backward_elimination",
            term_policies=(DoeTermPolicy("factor_1:factor_2", "forced"),),
        ),
    )
    lack = result["anova"]["lack_of_fit"]
    assert lack["unique_design_point_count"] == 8
    assert lack["pure_error"]["df"] == 8
    assert lack["lack_of_fit"]["df"] == 8 - result["sample"]["rank"]


def test_numerical_negative_is_only_clamped_within_recorded_roundoff_tolerance():
    small = decompose_lack_of_fit(sse=1 - 1e-15, pure_error_ss=1, pure_error_df=8, lack_of_fit_df=4)
    assert small["available"] and small["lack_of_fit"]["sum_squares"] == 0
    invalid = decompose_lack_of_fit(sse=0.9, pure_error_ss=1, pure_error_df=8, lack_of_fit_df=4)
    assert invalid["reason"] == "numerical_decomposition_failure"
    assert invalid["lack_of_fit"]["sum_squares"] is None
    assert invalid["lack_of_fit"]["p_value"] is None


@pytest.mark.parametrize("value", [float("inf"), float("nan"), -1.0])
def test_invalid_decomposition_remains_strict_json(value):
    result = decompose_lack_of_fit(
        sse=1.0,
        pure_error_ss=value,
        pure_error_df=3,
        lack_of_fit_df=2,
    )
    assert result["reason"] == "numerical_decomposition_failure"
    assert result["available"] is False
    json.dumps(result, allow_nan=False)


def test_stored_report_explains_zero_pure_error_without_recomputing():
    from app.services.doe_lack_of_fit_report import lack_of_fit_report_notice

    result = _fit(_corners(2, identical=True))
    lack = result["anova"]["lack_of_fit"]
    assert "Pure-error variance is zero" in lack_of_fit_report_notice(lack, "en")
    assert "순수오차 분산이 0" in lack_of_fit_report_notice(lack, "ko")
    assert "Center points are not required" in lack_of_fit_report_notice(lack, "en")
