import json
from pathlib import Path

import pytest

from app.statistics.one_sample_wilcoxon import (
    OneSampleWilcoxonColumn,
    OneSampleWilcoxonError,
    calculate_one_sample_wilcoxon,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/one_sample_wilcoxon_input.json")
REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/one_sample_wilcoxon_scipy_reference.json",
)


def test_one_sample_wilcoxon_is_hand_checkable_for_signed_ranks() -> None:
    result = calculate_one_sample_wilcoxon(
        [["1"], ["2"], ["3"], ["4"], ["5"]],
        _response_column(),
        null_location=0,
        method="exact",
    )

    assert result["summary_type"] == "one_sample_wilcoxon_signed_rank_test"
    assert result["method"] == "one_sample_wilcoxon_signed_rank"
    assert result["missing_policy"] == "complete_case"
    assert result["requested_method"] == "exact"
    assert result["resolved_method"] == "exact"
    assert result["zero_method"] == "wilcox"
    assert result["n_total"] == 5
    assert result["n_used"] == 5
    assert result["n_nonzero"] == 5
    assert result["warnings"] == [
        "one_sample_wilcoxon_symmetry_assumption",
        "one_sample_wilcoxon_not_median_test",
        "one_sample_wilcoxon_not_auto_switched",
    ]

    sample = result["sample"]
    assert sample["median"] == 3
    assert sample["median_difference"] == 3
    assert sample["positive_difference_count"] == 5
    assert sample["negative_difference_count"] == 0
    assert sample["zero_difference_count"] == 0

    test = result["test"]
    assert test["w_statistic"] == 0.0
    assert test["p_value"] == pytest.approx(0.0625, abs=1e-12)
    assert test["positive_rank_sum"] == 15.0
    assert test["negative_rank_sum"] == 0.0
    assert test["rank_sum_total"] == 15.0
    assert test["effect_size"]["rank_biserial"] == 1.0


def test_one_sample_wilcoxon_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        result = calculate_one_sample_wilcoxon(
            [[str(value)] for value in case["values"]],
            _response_column(),
            alpha=case["alpha"],
            alternative=case["alternative"],
            null_location=case["null_location"],
            method=case["method"],
            zero_method=case["zero_method"],
        )
        expected = cases_by_id[case["case_id"]]

        assert result["n_used"] == expected["n_used"]
        assert result["n_nonzero"] == expected["n_nonzero"]
        assert result["sample"]["median"] == expected["sample_median"]
        assert result["sample"]["median_difference"] == expected["median_difference"]
        test = result["test"]
        assert test["positive_rank_sum"] == pytest.approx(
            expected["positive_rank_sum"],
            abs=1e-12,
        )
        assert test["negative_rank_sum"] == pytest.approx(
            expected["negative_rank_sum"],
            abs=1e-12,
        )
        assert test["rank_sum_total"] == pytest.approx(
            expected["rank_sum_total"],
            abs=1e-12,
        )
        assert test["w_statistic"] == pytest.approx(expected["w_statistic"], abs=1e-12)
        assert test["p_value"] == pytest.approx(expected["pvalue"], abs=1e-12)
        assert test["effect_size"]["rank_biserial"] == pytest.approx(
            expected["rank_biserial"],
            abs=1e-12,
        )


def test_one_sample_wilcoxon_reports_exclusions_and_auto_asymptotic_for_zeros_or_ties() -> None:
    result = calculate_one_sample_wilcoxon(
        [["1"], ["2"], ["2"], ["3"], ["4"], [""], ["bad"]],
        _response_column(),
        null_location=2,
    )

    assert result["n_total"] == 7
    assert result["n_used"] == 5
    assert result["n_nonzero"] == 3
    assert result["n_missing"] == 1
    assert result["n_non_numeric"] == 1
    assert result["zero_difference_count"] == 2
    assert result["tie_count"] == 2
    assert result["requested_method"] == "auto"
    assert result["resolved_method"] == "asymptotic"
    assert result["warnings"] == [
        "one_sample_wilcoxon_symmetry_assumption",
        "one_sample_wilcoxon_not_median_test",
        "one_sample_wilcoxon_not_auto_switched",
        "zero_differences_detected",
        "signed_rank_ties_detected",
        "one_sample_wilcoxon_auto_asymptotic_due_to_zeros_or_ties",
        "small_nonzero_n",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]
    test = result["test"]
    assert 0.0 <= test["p_value"] <= 1.0


def test_one_sample_wilcoxon_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(
        OneSampleWilcoxonError,
        match="one_sample_wilcoxon_no_nonzero_differences",
    ):
        calculate_one_sample_wilcoxon(
            [["2"], ["2"], ["2"]],
            _response_column(),
            null_location=2,
        )

    with pytest.raises(
        OneSampleWilcoxonError,
        match="one_sample_wilcoxon_exact_with_zeros_or_ties",
    ):
        calculate_one_sample_wilcoxon(
            [["1"], ["2"], ["2"], ["3"]],
            _response_column(),
            null_location=2,
            method="exact",
        )

    with pytest.raises(OneSampleWilcoxonError, match="invalid_one_sample_wilcoxon_method"):
        calculate_one_sample_wilcoxon(
            [["1"], ["2"], ["3"]],
            _response_column(),
            method="bad",
        )


def _response_column() -> OneSampleWilcoxonColumn:
    return OneSampleWilcoxonColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )
