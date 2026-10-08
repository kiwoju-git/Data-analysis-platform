import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from app.statistics.two_variances import (
    TwoVariancesError,
    TwoVariancesOptions,
    calculate_two_variances,
    parse_two_variance_groups,
)

A = [1, 2, 3, 4, 5]
B = [1, 3, 5, 7, 9]
F = TwoVariancesOptions(method="normal_f")


def test_independent_reference() -> None:
    fixture = json.loads(
        (Path(__file__).parents[1] / "reference/two_variances_reference.json").read_text(
            encoding="utf-8"
        )
    )
    assert A == fixture["sample_1"] and B == fixture["sample_2"]
    result = calculate_two_variances(A, B, F)
    assert [group["variance"] for group in result["groups"]] == [2.5, 10]
    assert result["ratio_estimate"]["variance"] == 0.25
    assert result["ratio_estimate"]["standard_deviation"] == 0.5
    assert result["test"]["statistic"] == 0.25
    assert result["test"]["p_value"] == pytest.approx(
        fixture["normal_f"]["two_sided_p_value"],
        rel=fixture["tolerance"]["relative"],
        abs=fixture["tolerance"]["absolute_p"],
    )
    assert result["test"]["df1"] == result["test"]["df2"] == 4
    assert result["ratio_interval"]["lower"]["value"] == pytest.approx(
        0.0260293843634819, rel=1e-11
    )
    assert result["ratio_interval"]["upper"]["value"] == pytest.approx(2.40113247118072, rel=1e-11)
    bf = calculate_two_variances(A, B, TwoVariancesOptions())
    assert bf["test"]["statistic"] == pytest.approx(72 / 35, rel=1e-11)
    assert bf["test"]["p_value"] == pytest.approx(0.189403661093321, rel=1e-11)
    assert bf["ratio_interval"] == {"available": False, "reason": "not_provided_by_selected_method"}
    assert "two_variances_independence_required" in bf["warnings"]


@pytest.mark.parametrize("alternative", ["two_sided", "less", "greater"])
def test_swap_scale_and_sd(alternative: str) -> None:
    options = replace(F, alternative=alternative)
    result = calculate_two_variances(A, B, options)
    scaled = calculate_two_variances([v * 7 for v in A], [v * 7 for v in B], options)
    reverse = calculate_two_variances(
        B,
        A,
        replace(
            options,
            alternative={"less": "greater", "greater": "less", "two_sided": "two_sided"}[
                alternative
            ],
        ),
    )
    assert result["test"]["p_value"] == pytest.approx(scaled["test"]["p_value"], rel=1e-11)
    assert result["test"]["p_value"] == pytest.approx(reverse["test"]["p_value"], rel=1e-11)
    assert reverse["ratio_estimate"]["variance"] == 4
    sd = calculate_two_variances(
        A, B, replace(options, ratio_scale="standard_deviation", hypothesized_ratio=0.5)
    )
    variance = calculate_two_variances(A, B, replace(options, hypothesized_ratio=0.25))
    assert sd["test"] == variance["test"]
    for bound in ("lower", "upper"):
        value = sd["ratio_interval"][bound]["value"]
        expected = variance["ratio_interval"][bound]["value"]
        assert value == (None if expected is None else pytest.approx(math.sqrt(expected)))
    if alternative == "two_sided":
        assert result["ratio_interval"]["lower"]["value"] == pytest.approx(
            1 / reverse["ratio_interval"]["upper"]["value"]
        )
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    "sample,code",
    [
        ([1], "two_variances_group_n_too_small"),
        ([2, 2, 2], "two_variances_zero_variance"),
        ([1, math.nan, 3], "two_variances_nonfinite_input"),
        ([1, math.inf, 3], "two_variances_nonfinite_input"),
        ([1e308, -1e308, 2e308], "two_variances_nonfinite_input"),
    ],
)
def test_rejects_invalid_samples(sample, code) -> None:
    with pytest.raises(TwoVariancesError, match=code):
        calculate_two_variances(sample, B, F)


def test_degenerate_deviations_and_budget() -> None:
    with pytest.raises(TwoVariancesError, match="nonfinite_result"):
        calculate_two_variances(A, B, replace(F, confidence_level=0.9999999999999999))
    with pytest.raises(TwoVariancesError, match="degenerate_absolute_deviations"):
        calculate_two_variances([1, 1, 3, 3], [2, 2, 4, 4], TwoVariancesOptions())
    with pytest.raises(TwoVariancesError, match="usable_rows_limit"):
        calculate_two_variances(list(range(10001)), list(range(10000)), F)
    with pytest.raises(TwoVariancesError, match="equality_only"):
        calculate_two_variances(A, B, TwoVariancesOptions(alternative="less"))


def test_group_keys_and_complete_case_parsing() -> None:
    distinct = parse_two_variance_groups([["1", " A"], ["2", "A"], ["3", "B"]], 0, 1)
    assert list(distinct.values) == [" A", "A", "B"]
    first, second = "x" * 200 + "a", "x" * 200 + "b"
    result = parse_two_variance_groups(
        [["1.234,5", first], ["2,5", second], ["NaN", first], [None, first], ["3", ""]],
        0,
        1,
        decimal=",",
        thousands=".",
    )
    assert result.values == {first: [1234.5], second: [2.5]}
    assert result.row_indices == {first: [1], second: [2]}
    assert result.sample() == {
        "n_total": 5,
        "n_used": 2,
        "n_excluded": 3,
        "missing_response": 1,
        "missing_group": 1,
        "nonnumeric_response": 1,
        "missing_policy": "complete_case",
    }
