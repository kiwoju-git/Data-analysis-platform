import json
from pathlib import Path

import pytest

from app.statistics.equivalence_tost import (
    EquivalenceTostColumn,
    EquivalenceTostError,
    calculate_equivalence_tost,
    calculate_paired_equivalence_tost,
    calculate_two_sample_equivalence_tost,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/equivalence_tost_input.json")
REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/equivalence_tost_scipy_reference.json",
)


def test_equivalence_tost_is_hand_checkable_for_one_sample_mean() -> None:
    result = calculate_equivalence_tost(
        [["9"], ["10"], ["11"]],
        _response_column(),
        reference_mean=10.0,
        lower_bound=-2.0,
        upper_bound=2.0,
        alpha=0.05,
    )

    assert result["summary_type"] == "equivalence_tost"
    assert result["method"] == "one_sample_mean_tost"
    assert result["design"] == "one_sample_mean"
    assert result["confidence_level"] == pytest.approx(0.9, abs=1e-12)
    assert result["warnings"] == [
        "equivalence_tost_design_assumption",
        "equivalence_bounds_user_defined",
        "non_significance_is_not_equivalence",
    ]
    assert result["n_total"] == 3
    assert result["n_used"] == 3
    sample = result["sample"]
    assert sample["mean"] == 10.0
    assert sample["variance"] == 1.0
    assert sample["std"] == 1.0

    estimate = result["estimate"]
    assert estimate["value"] == 0.0
    assert estimate["standard_error"] == pytest.approx(1.0 / (3.0**0.5), abs=1e-12)
    assert estimate["df"] == 2.0

    lower_test = result["tests"]["lower"]
    upper_test = result["tests"]["upper"]
    assert lower_test["statistic"] == pytest.approx(3.4641016151377544, abs=1e-12)
    assert upper_test["statistic"] == pytest.approx(-3.4641016151377544, abs=1e-12)
    assert lower_test["reject_null"] is True
    assert upper_test["reject_null"] is True
    assert result["tost"]["equivalent"] is True
    assert result["confidence_interval"]["inside_equivalence_bounds"] is True


def test_equivalence_tost_matches_scipy_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        expected = cases_by_id[case["case_id"]]
        result = calculate_equivalence_tost(
            [[str(value)] for value in case["values"]],
            _response_column(),
            reference_mean=case["reference_mean"],
            lower_bound=case["lower_bound"],
            upper_bound=case["upper_bound"],
            alpha=case["alpha"],
        )
        sample = result["sample"]
        assert sample["n"] == expected["n"]
        assert sample["mean"] == pytest.approx(expected["mean"], abs=1e-12)
        assert sample["variance"] == pytest.approx(expected["variance"], abs=1e-12)
        assert sample["std"] == pytest.approx(expected["std"], abs=1e-12)
        estimate = result["estimate"]
        assert estimate["value"] == pytest.approx(expected["estimate"], abs=1e-12)
        assert estimate["standard_error"] == pytest.approx(
            expected["standard_error"],
            abs=1e-12,
        )
        assert estimate["df"] == pytest.approx(expected["df"], abs=1e-12)
        lower_test = result["tests"]["lower"]
        upper_test = result["tests"]["upper"]
        assert lower_test["statistic"] == pytest.approx(
            expected["lower_statistic"],
            abs=1e-12,
        )
        assert lower_test["p_value"] == pytest.approx(
            expected["lower_pvalue"],
            abs=1e-12,
        )
        assert upper_test["statistic"] == pytest.approx(
            expected["upper_statistic"],
            abs=1e-12,
        )
        assert upper_test["p_value"] == pytest.approx(
            expected["upper_pvalue"],
            abs=1e-12,
        )
        assert result["tost"]["p_value"] == pytest.approx(
            expected["tost_pvalue"],
            abs=1e-12,
        )
        assert result["tost"]["equivalent"] is expected["equivalent"]
        assert result["confidence_interval"]["level"] == pytest.approx(
            expected["ci_level"],
            abs=1e-12,
        )
        assert result["confidence_interval"]["lower"] == pytest.approx(
            expected["ci_lower"],
            abs=1e-12,
        )
        assert result["confidence_interval"]["upper"] == pytest.approx(
            expected["ci_upper"],
            abs=1e-12,
        )
        assert (
            result["confidence_interval"]["inside_equivalence_bounds"]
            is expected["ci_inside_bounds"]
        )
        assert result["effect_size"]["cohen_dz"] == pytest.approx(
            expected["effect_size"]["cohen_dz"],
            abs=1e-12,
        )
        assert result["effect_size"]["hedges_g"] == pytest.approx(
            expected["effect_size"]["hedges_g"],
            abs=1e-12,
        )


def test_equivalence_tost_reports_exclusions_without_equivalence_fallback() -> None:
    result = calculate_equivalence_tost(
        [["9"], [""], ["bad"], ["10"], ["11"]],
        _response_column(),
        reference_mean=10.0,
        lower_bound=-2.0,
        upper_bound=2.0,
    )

    assert result["n_total"] == 5
    assert result["n_used"] == 3
    assert result["n_missing"] == 1
    assert result["n_non_numeric"] == 1
    assert result["warnings"] == [
        "equivalence_tost_design_assumption",
        "equivalence_bounds_user_defined",
        "non_significance_is_not_equivalence",
        "missing_values_excluded",
        "non_numeric_values_excluded",
    ]


def test_equivalence_tost_requires_both_one_sided_tests_to_reject() -> None:
    result = calculate_equivalence_tost(
        [["11.1"], ["11.2"], ["11.3"]],
        _response_column(),
        reference_mean=10.0,
        lower_bound=-1.0,
        upper_bound=1.0,
        alpha=0.05,
    )

    assert result["estimate"]["value"] == pytest.approx(1.2, abs=1e-12)
    assert result["tests"]["lower"]["reject_null"] is True
    assert result["tests"]["upper"]["reject_null"] is False
    assert result["tost"]["equivalent"] is False
    assert result["tost"]["decision_rule"] == "both_one_sided_tests_reject_at_alpha"
    assert result["tost"]["p_value"] == result["tests"]["upper"]["p_value"]
    assert result["confidence_interval"]["inside_equivalence_bounds"] is False


def test_equivalence_tost_does_not_treat_nonsignificant_difference_as_equivalence() -> None:
    result = calculate_equivalence_tost(
        [["8"], ["10"], ["12"]],
        _response_column(),
        reference_mean=10.0,
        lower_bound=-0.5,
        upper_bound=0.5,
        alpha=0.05,
    )

    assert result["estimate"]["value"] == pytest.approx(0.0, abs=1e-12)
    assert result["tests"]["lower"]["p_value"] == pytest.approx(
        0.35361498905772004,
        abs=1e-12,
    )
    assert result["tests"]["upper"]["p_value"] == pytest.approx(
        0.35361498905772004,
        abs=1e-12,
    )
    assert result["tests"]["lower"]["reject_null"] is False
    assert result["tests"]["upper"]["reject_null"] is False
    assert result["tost"]["equivalent"] is False
    assert result["confidence_interval"]["inside_equivalence_bounds"] is False
    assert "non_significance_is_not_equivalence" in result["warnings"]


def test_equivalence_tost_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(EquivalenceTostError, match="equivalence_tost_design_unsupported"):
        calculate_equivalence_tost(
            [["1"], ["2"], ["3"]],
            _response_column(),
            design="paired_mean",
            reference_mean=0.0,
            lower_bound=-1.0,
            upper_bound=1.0,
        )

    with pytest.raises(EquivalenceTostError, match="equivalence_tost_bounds_order_invalid"):
        calculate_equivalence_tost(
            [["1"], ["2"], ["3"]],
            _response_column(),
            reference_mean=0.0,
            lower_bound=1.0,
            upper_bound=1.0,
        )

    with pytest.raises(EquivalenceTostError, match="invalid_equivalence_tost_alpha"):
        calculate_equivalence_tost(
            [["1"], ["2"], ["3"]],
            _response_column(),
            reference_mean=0.0,
            lower_bound=-1.0,
            upper_bound=1.0,
            alpha=0.5,
        )

    with pytest.raises(EquivalenceTostError, match="equivalence_tost_n_too_small"):
        calculate_equivalence_tost(
            [["1"]],
            _response_column(),
            reference_mean=0.0,
            lower_bound=-1.0,
            upper_bound=1.0,
        )

    with pytest.raises(EquivalenceTostError, match="equivalence_tost_standard_error_zero"):
        calculate_equivalence_tost(
            [["5"], ["5"], ["5"]],
            _response_column(),
            reference_mean=0.0,
            lower_bound=-1.0,
            upper_bound=1.0,
        )


def test_two_sample_equivalence_welch_and_pooled_use_test_minus_reference() -> None:
    rows = [
        *[[str(value), "Test"] for value in [9.7, 10.0, 10.2, 10.1]],
        *[[str(value), "Reference"] for value in [9.8, 9.9, 10.0, 10.1, 10.2]],
    ]
    welch = calculate_two_sample_equivalence_tost(
        rows,
        _response_column(),
        _group_column(),
        test_group_label="Test",
        reference_group_label="Reference",
        lower_bound=-0.5,
        upper_bound=0.5,
        variance_assumption="welch",
    )
    pooled = calculate_two_sample_equivalence_tost(
        rows,
        _response_column(),
        _group_column(),
        test_group_label="Test",
        reference_group_label="Reference",
        lower_bound=-0.5,
        upper_bound=0.5,
        variance_assumption="pooled",
    )

    assert welch["design"] == "two_sample_independent_mean_difference"
    assert welch["estimate_definition"] == "mean_test_minus_mean_reference"
    assert welch["estimate"]["value"] == pytest.approx(0.0, abs=1e-12)
    test_variance = 0.04666666666666664
    reference_variance = 0.025
    variance_term = (test_variance / 4) + (reference_variance / 5)
    expected_df = variance_term**2 / (
        ((test_variance / 4) ** 2) / 3 + ((reference_variance / 5) ** 2) / 4
    )
    assert welch["estimate"]["standard_error"] == pytest.approx(
        variance_term**0.5,
        abs=1e-12,
    )
    assert welch["estimate"]["df"] == pytest.approx(expected_df, abs=1e-12)
    assert welch["tost"]["equivalent"] is True
    assert pooled["estimate"]["df"] == 7.0
    assert pooled["estimate"]["standard_error"] != pytest.approx(
        welch["estimate"]["standard_error"],
        abs=1e-15,
    )


def test_paired_equivalence_uses_only_complete_test_minus_reference_pairs() -> None:
    result = calculate_paired_equivalence_tost(
        [
            ["10.1", "10.0"],
            ["10.2", "10.0"],
            ["", "10.0"],
            ["10.0", ""],
            ["9.9", "10.0"],
        ],
        _response_column(),
        _paired_reference_column(),
        lower_bound=-0.5,
        upper_bound=0.5,
    )

    assert result["design"] == "paired_mean_difference"
    assert result["n_total"] == 5
    assert result["n_complete_pairs"] == 3
    assert result["n_incomplete_pairs"] == 2
    assert result["n_missing_test"] == 1
    assert result["n_missing_reference"] == 1
    assert result["estimate"]["value"] == pytest.approx(0.06666666666666643, abs=1e-12)
    assert result["estimate"]["df"] == 2.0
    assert result["tost"]["equivalent"] is True


def _response_column() -> EquivalenceTostColumn:
    return EquivalenceTostColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _group_column() -> EquivalenceTostColumn:
    return EquivalenceTostColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="group",
        unit=None,
    )


def _paired_reference_column() -> EquivalenceTostColumn:
    return EquivalenceTostColumn(
        column_id="reference",
        column_index=1,
        display_name="reference",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )
