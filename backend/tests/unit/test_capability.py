import json
from pathlib import Path

import pytest

from app.statistics.capability import (
    CapabilityColumn,
    CapabilityError,
    calculate_normal_capability,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/capability_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/capability_reference.json")


def test_normal_capability_is_hand_checkable_for_two_sided_specs() -> None:
    result = calculate_normal_capability(
        [["10"], ["11"], ["12"], ["13"], ["14"]],
        _value_column(),
        lsl=8.0,
        usl=16.0,
        target=12.0,
    )

    assert result["summary_type"] == "capability_analysis"
    assert result["method"] == "normal_capability"
    assert result["distribution"] == "normal"
    assert result["spec_limits"] == {"lsl": 8.0, "usl": 16.0, "target": 12.0}
    assert result["n_total"] == 5
    assert result["n_used"] == 5
    assert result["sample"] == {
        "mean": 12.0,
        "std_overall": pytest.approx(1.5811388300841898),
        "std_within": pytest.approx(0.8865248226950355),
        "min": 10.0,
        "max": 14.0,
    }
    assert result["sigma_estimators"] == {
        "overall": "sample_standard_deviation_ddof_1",
        "within": "average_moving_range_d2",
        "moving_range_length": 2,
        "d2": 1.128,
        "mrbar": 1.0,
    }
    assert result["capability"]["within"] == {
        "two_sided": pytest.approx(1.504),
        "lower": pytest.approx(1.504),
        "upper": pytest.approx(1.504),
        "min_side": pytest.approx(1.504),
    }
    assert result["capability"]["overall"] == {
        "two_sided": pytest.approx(0.8432740427115678),
        "lower": pytest.approx(0.8432740427115678),
        "upper": pytest.approx(0.8432740427115678),
        "min_side": pytest.approx(0.8432740427115678),
    }
    assert result["observed_nonconformance"] == {
        "below_lsl_count": 0,
        "above_usl_count": 0,
        "total_count": 0,
        "below_lsl_proportion": 0.0,
        "above_usl_proportion": 0.0,
        "total_proportion": 0.0,
        "total_ppm": 0.0,
    }
    assert result["expected_nonconformance_normal"]["total_probability"] == pytest.approx(
        0.011412036386001651,
    )
    assert result["expected_nonconformance_normal"]["total_ppm"] == pytest.approx(
        11412.036386001651,
    )
    assert result["histogram"]["bin_count"] == 5
    assert len(result["histogram"]["bins"]) == 5
    assert result["warnings"] == [
        "capability_normal_model_assumed",
        "capability_control_limits_not_spec_limits",
        "capability_process_stability_not_proven",
        "capability_measurement_system_not_verified",
        "capability_within_sigma_uses_canonical_moving_range",
        "capability_point_estimates_without_ci",
        "capability_target_recorded_cpm_not_computed",
    ]


def test_normal_capability_supports_one_sided_spec_and_exclusions() -> None:
    result = calculate_normal_capability(
        [["10"], [""], ["bad"], ["11"], ["12"], ["13"], ["14"]],
        _value_column(),
        lsl=None,
        usl=16.0,
    )

    assert result["n_total"] == 7
    assert result["n_used"] == 5
    assert result["n_excluded_missing_value"] == 1
    assert result["n_excluded_non_numeric_value"] == 1
    assert result["capability"]["overall"]["two_sided"] is None
    assert result["capability"]["overall"]["lower"] is None
    assert result["capability"]["overall"]["upper"] == pytest.approx(0.8432740427115678)
    assert result["capability"]["overall"]["min_side"] == pytest.approx(0.8432740427115678)
    assert result["expected_nonconformance_normal"]["below_lsl_probability"] == 0.0
    assert "capability_one_sided_spec" in result["warnings"]
    assert "capability_process_stability_not_proven" in result["warnings"]
    assert "missing_values_excluded" in result["warnings"]
    assert "non_numeric_values_excluded" in result["warnings"]


def test_normal_capability_matches_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        result = calculate_normal_capability(
            case["rows"],
            _value_column(),
            lsl=case["lsl"],
            usl=case["usl"],
            target=case["target"],
            histogram_bin_limit=case["histogram_bin_limit"],
        )
        expected = cases_by_id[case["case_id"]]

        assert result["n_total"] == expected["n_total"]
        assert result["n_used"] == expected["n_used"]
        assert result["n_excluded_missing_value"] == expected["n_excluded_missing_value"]
        assert result["n_excluded_non_numeric_value"] == (expected["n_excluded_non_numeric_value"])
        _assert_optional_numeric_mapping(result["sample"], expected["sample"])
        _assert_optional_numeric_mapping(
            result["capability"]["within"],
            expected["capability_within"],
        )
        _assert_optional_numeric_mapping(
            result["capability"]["overall"],
            expected["capability_overall"],
        )
        _assert_optional_numeric_mapping(
            result["expected_nonconformance_normal"],
            expected["expected_nonconformance_normal"],
        )
        _assert_optional_numeric_mapping(
            result["observed_nonconformance"],
            expected["observed_nonconformance"],
        )
        assert result["warnings"] == expected["warnings"]


def test_normal_capability_rejects_invalid_inputs_without_fake_indices() -> None:
    with pytest.raises(CapabilityError, match="capability_spec_limit_required"):
        calculate_normal_capability([["1"], ["2"]], _value_column(), lsl=None, usl=None)

    with pytest.raises(CapabilityError, match="capability_spec_limits_invalid"):
        calculate_normal_capability([["1"], ["2"]], _value_column(), lsl=3.0, usl=2.0)

    with pytest.raises(CapabilityError, match="capability_target_outside_spec"):
        calculate_normal_capability([["1"], ["2"]], _value_column(), lsl=0.0, usl=3.0, target=4.0)

    with pytest.raises(CapabilityError, match="capability_n_too_small"):
        calculate_normal_capability([[""], ["2"]], _value_column(), lsl=0.0, usl=3.0)

    with pytest.raises(CapabilityError, match="capability_zero_overall_sigma"):
        calculate_normal_capability([["2"], ["2"], ["2"]], _value_column(), lsl=0.0, usl=3.0)

    with pytest.raises(CapabilityError, match="capability_missing_policy_unsupported"):
        calculate_normal_capability(
            [["1"], ["2"]],
            _value_column(),
            lsl=0.0,
            usl=3.0,
            missing_policy="available_case_by_column",
        )

    with pytest.raises(CapabilityError, match="invalid_capability_histogram_bin_limit"):
        calculate_normal_capability(
            [["1"], ["2"]],
            _value_column(),
            lsl=0.0,
            usl=3.0,
            histogram_bin_limit=0,
        )


def _value_column() -> CapabilityColumn:
    return CapabilityColumn(
        column_id="value",
        column_index=0,
        display_name="value",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit="mm",
    )


def _assert_optional_numeric_mapping(actual: object, expected: dict[str, object]) -> None:
    assert isinstance(actual, dict)
    for key, expected_value in expected.items():
        if expected_value is None:
            assert actual[key] is None
        else:
            assert actual[key] == pytest.approx(expected_value, abs=1e-12)
