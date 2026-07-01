import json
from pathlib import Path

import pytest

from app.statistics.one_sample_t import (
    OneSampleTColumn,
    OneSampleTError,
    calculate_one_sample_t,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/one_sample_t_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/one_sample_t_scipy_reference.json")


def test_one_sample_t_is_hand_checkable_for_sample_summary() -> None:
    result = calculate_one_sample_t(
        [["1"], ["2"], ["3"]],
        _response_column(),
        null_mean=2.0,
    )

    assert result["summary_type"] == "one_sample_t_test"
    assert result["method"] == "one_sample_t"
    assert result["missing_policy"] == "complete_case"
    assert result["warnings"] == [
        "one_sample_t_design_assumption",
        "one_sample_t_not_auto_switched",
    ]
    assert result["n_total"] == 3
    assert result["n_used"] == 3
    sample = result["sample"]  # type: ignore[assignment]
    assert sample["n"] == 3
    assert sample["mean"] == 2.0
    assert sample["median"] == 2.0
    assert sample["variance"] == 1.0
    assert sample["std"] == 1.0
    assert sample["min"] == 1.0
    assert sample["max"] == 3.0

    contrast = result["contrast"]  # type: ignore[assignment]
    assert contrast["estimate"] == 0.0
    assert contrast["estimate_definition"] == "mean_minus_null_mean"
    assert contrast["statistic"] == 0.0
    assert contrast["df"] == 2.0
    assert contrast["p_value"] == 1.0
    assert contrast["reject_null"] is False
    assert contrast["effect_size"]["cohen_dz"] == 0.0


def test_one_sample_t_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        expected = cases_by_id[case["case_id"]]
        result = calculate_one_sample_t(
            [[str(value)] for value in case["values"]],
            _response_column(),
            alpha=case["alpha"],
            confidence_level=case["confidence_level"],
            alternative=case["alternative"],
            null_mean=case["null_mean"],
        )
        sample = result["sample"]
        assert sample["n"] == expected["n"]
        assert sample["mean"] == pytest.approx(expected["mean"], abs=1e-12)
        assert sample["variance"] == pytest.approx(expected["variance"], abs=1e-12)
        assert sample["std"] == pytest.approx(expected["std"], abs=1e-12)
        contrast = result["contrast"]
        assert contrast["estimate"] == pytest.approx(expected["estimate"], abs=1e-12)
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


def test_one_sample_t_reports_exclusions_and_one_sided_ci() -> None:
    result = calculate_one_sample_t(
        [["1"], [""], ["bad"], ["2"], ["3"]],
        _response_column(),
        alternative="greater",
        null_mean=1.0,
    )

    assert result["n_total"] == 5
    assert result["n_used"] == 3
    assert result["n_missing"] == 1
    assert result["n_non_numeric"] == 1
    assert result["warnings"] == [
        "one_sample_t_design_assumption",
        "one_sample_t_not_auto_switched",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]
    contrast = result["contrast"]
    assert contrast["confidence_interval"]["alternative"] == "greater"
    assert contrast["confidence_interval"]["lower"] is not None
    assert contrast["confidence_interval"]["upper"] is None


def test_one_sample_t_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(OneSampleTError, match="one_sample_t_n_too_small"):
        calculate_one_sample_t([["1"]], _response_column())

    with pytest.raises(OneSampleTError, match="one_sample_t_standard_error_zero"):
        calculate_one_sample_t([["5"], ["5"], ["5"]], _response_column())

    with pytest.raises(OneSampleTError, match="invalid_one_sample_t_alternative"):
        calculate_one_sample_t([["1"], ["2"], ["3"]], _response_column(), alternative="bad")


def _response_column() -> OneSampleTColumn:
    return OneSampleTColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )
