import json
from pathlib import Path

import pytest

from app.statistics.paired_t import PairedTColumn, PairedTError, calculate_paired_t

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/paired_t_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/paired_t_scipy_reference.json")


def test_paired_t_is_hand_checkable_for_difference_summary() -> None:
    result = calculate_paired_t(
        [["1", "2"], ["2", "4"], ["3", "6"]],
        _column("before", 0),
        _column("after", 1),
        null_difference=2.0,
    )

    assert result["summary_type"] == "paired_t_test"
    assert result["method"] == "paired_t"
    assert result["design"] == "wide_two_measurement_columns"
    assert result["difference_definition"] == "after_minus_before"
    assert result["missing_policy"] == "complete_pair"
    assert result["warnings"] == [
        "paired_t_design_assumption",
        "paired_t_not_auto_switched",
    ]
    assert result["n_total"] == 3
    assert result["n_used"] == 3
    assert result["n_incomplete_pairs"] == 0
    paired_sample = result["paired_sample"]  # type: ignore[assignment]
    assert paired_sample["n"] == 3
    assert paired_sample["before_mean"] == 2.0
    assert paired_sample["after_mean"] == 4.0
    assert paired_sample["mean_difference"] == 2.0
    assert paired_sample["median_difference"] == 2.0
    assert paired_sample["difference_variance"] == 1.0
    assert paired_sample["difference_std"] == 1.0
    assert paired_sample["min_difference"] == 1.0
    assert paired_sample["max_difference"] == 3.0

    contrast = result["contrast"]  # type: ignore[assignment]
    assert contrast["estimate"] == 0.0
    assert contrast["estimate_definition"] == "mean_after_minus_before_minus_null_difference"
    assert contrast["null_difference"] == 2.0
    assert contrast["statistic"] == 0.0
    assert contrast["df"] == 2.0
    assert contrast["p_value"] == 1.0
    assert contrast["effect_size"]["cohen_dz"] == 0.0


def test_paired_t_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        expected = cases_by_id[case["case_id"]]
        result = calculate_paired_t(
            [
                [str(before), str(after)]
                for before, after in zip(case["before"], case["after"], strict=True)
            ],
            _column("before", 0),
            _column("after", 1),
            alpha=case["alpha"],
            confidence_level=case["confidence_level"],
            alternative=case["alternative"],
            null_difference=case["null_difference"],
        )
        paired_sample = result["paired_sample"]
        assert paired_sample["n"] == expected["n"]
        assert paired_sample["before_mean"] == pytest.approx(
            expected["before_mean"],
            abs=1e-12,
        )
        assert paired_sample["after_mean"] == pytest.approx(
            expected["after_mean"],
            abs=1e-12,
        )
        assert paired_sample["mean_difference"] == pytest.approx(
            expected["mean_difference"],
            abs=1e-12,
        )
        assert paired_sample["median_difference"] == pytest.approx(
            expected["median_difference"],
            abs=1e-12,
        )
        assert paired_sample["difference_variance"] == pytest.approx(
            expected["difference_variance"],
            abs=1e-12,
        )
        assert paired_sample["difference_std"] == pytest.approx(
            expected["difference_std"],
            abs=1e-12,
        )
        contrast = result["contrast"]
        assert contrast["estimate"] == pytest.approx(
            expected["mean_difference"],
            abs=1e-12,
        )
        assert contrast["standard_error"] == pytest.approx(
            expected["standard_error"],
            abs=1e-12,
        )
        assert contrast["df"] == pytest.approx(expected["df"], abs=1e-12)
        assert contrast["statistic"] == pytest.approx(expected["statistic"], abs=1e-12)
        assert contrast["p_value"] == pytest.approx(expected["pvalue"], abs=1e-12)
        assert contrast["confidence_interval"]["lower"] == pytest.approx(
            expected["ci_lower"],
            abs=1e-12,
        )
        if expected["ci_upper"] is None:
            assert contrast["confidence_interval"]["upper"] is None
        else:
            assert contrast["confidence_interval"]["upper"] == pytest.approx(
                expected["ci_upper"],
                abs=1e-12,
            )
        assert contrast["effect_size"]["cohen_dz"] == pytest.approx(
            expected["effect_size"]["cohen_dz"],
            abs=1e-12,
        )
        assert contrast["effect_size"]["hedges_g"] == pytest.approx(
            expected["effect_size"]["hedges_g"],
            abs=1e-12,
        )


def test_paired_t_reports_incomplete_and_non_numeric_pairs() -> None:
    result = calculate_paired_t(
        [["1", "2"], ["", "3"], ["4", ""], ["bad", "5"], ["6", "bad"], ["2", "4"]],
        _column("before", 0),
        _column("after", 1),
        alternative="greater",
    )

    assert result["n_total"] == 6
    assert result["n_used"] == 2
    assert result["n_incomplete_pairs"] == 2
    assert result["n_missing_before"] == 1
    assert result["n_missing_after"] == 1
    assert result["n_non_numeric_pairs"] == 2
    assert result["n_non_numeric_before"] == 1
    assert result["n_non_numeric_after"] == 1
    assert result["warnings"] == [
        "paired_t_design_assumption",
        "paired_t_not_auto_switched",
        "incomplete_pairs_excluded",
        "non_numeric_pairs_excluded",
    ]
    contrast = result["contrast"]
    assert contrast["confidence_interval"]["alternative"] == "greater"
    assert contrast["confidence_interval"]["lower"] is not None
    assert contrast["confidence_interval"]["upper"] is None


def test_paired_t_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(PairedTError, match="paired_t_n_too_small"):
        calculate_paired_t([["1", "2"]], _column("before", 0), _column("after", 1))

    with pytest.raises(PairedTError, match="paired_t_standard_error_zero"):
        calculate_paired_t(
            [["1", "2"], ["2", "3"], ["3", "4"]],
            _column("before", 0),
            _column("after", 1),
        )

    with pytest.raises(PairedTError, match="invalid_paired_t_alternative"):
        calculate_paired_t(
            [["1", "2"], ["2", "4"], ["3", "6"]],
            _column("before", 0),
            _column("after", 1),
            alternative="bad",
        )


def _column(column_id: str, column_index: int) -> PairedTColumn:
    return PairedTColumn(
        column_id=column_id,
        column_index=column_index,
        display_name=column_id,
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )
