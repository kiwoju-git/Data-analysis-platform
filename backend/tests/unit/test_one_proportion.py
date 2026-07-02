import json
from pathlib import Path

import pytest

from app.statistics.one_proportion import (
    OneProportionColumn,
    OneProportionError,
    calculate_one_proportion,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/one_proportion_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/one_proportion_reference.json")


def test_one_proportion_is_hand_checkable_for_counts_and_exact_p_value() -> None:
    result = calculate_one_proportion(
        [["yes"], ["yes"], ["yes"], ["no"]],
        _response_column(),
        event_level="yes",
        null_proportion=0.5,
    )

    assert result["summary_type"] == "one_proportion_test"
    assert result["method"] == "exact_binomial_test"
    assert result["input_mode"] == "dataset_binary_column"
    assert result["missing_policy"] == "complete_case"
    assert result["warnings"] == [
        "one_proportion_binary_design_assumption",
        "one_proportion_exact_binomial",
    ]
    assert result["n_total"] == 4
    assert result["n_used"] == 4
    assert result["n_missing"] == 0
    assert result["levels"] == [
        {"level": "yes", "count": 3, "is_event": True},
        {"level": "no", "count": 1, "is_event": False},
    ]
    sample = result["sample"]
    assert sample["event_count"] == 3
    assert sample["non_event_count"] == 1
    assert sample["sample_proportion"] == 0.75
    assert sample["difference_from_null"] == 0.25
    test = result["test"]
    assert test["statistic"] == 3
    assert test["p_value"] == pytest.approx(0.625, abs=1e-12)
    assert test["exact"] is True


def test_one_proportion_matches_reference_fixture() -> None:
    input_fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    cases_by_id = {case["case_id"]: case for case in reference["cases"]}

    for case in input_fixture["cases"]:
        expected = cases_by_id[case["case_id"]]
        result = calculate_one_proportion(
            [[str(value)] for value in case["values"]],
            _response_column(),
            event_level=case["event_level"],
            null_proportion=case["null_proportion"],
            alpha=case["alpha"],
            confidence_level=case["confidence_level"],
            alternative=case["alternative"],
            ci_method=case["ci_method"],
        )

        sample = result["sample"]
        assert sample["event_count"] == expected["event_count"]
        assert sample["non_event_count"] == expected["non_event_count"]
        assert sample["total"] == expected["total"]
        assert sample["sample_proportion"] == pytest.approx(
            expected["sample_proportion"],
            abs=1e-12,
        )
        assert sample["difference_from_null"] == pytest.approx(
            expected["difference_from_null"],
            abs=1e-12,
        )
        assert sample["odds"] == pytest.approx(expected["odds"], abs=1e-12)
        assert result["test"]["p_value"] == pytest.approx(expected["pvalue"], abs=1e-12)
        assert result["confidence_interval"]["lower"] == pytest.approx(
            expected["ci_lower"],
            abs=1e-12,
        )
        assert result["confidence_interval"]["upper"] == pytest.approx(
            expected["ci_upper"],
            abs=1e-12,
        )
        assert result["effect_size"]["cohen_h"] == pytest.approx(
            expected["cohen_h"],
            abs=1e-12,
        )


def test_one_proportion_reports_missing_and_single_level_warnings() -> None:
    result = calculate_one_proportion(
        [["no"], ["no"], [""], [None]],
        _response_column(),
        event_level="yes",
    )

    assert result["n_total"] == 4
    assert result["n_used"] == 2
    assert result["n_missing"] == 2
    assert result["sample"]["event_count"] == 0
    assert result["warnings"] == [
        "one_proportion_binary_design_assumption",
        "one_proportion_exact_binomial",
        "missing_values_excluded",
        "event_level_not_observed",
        "all_events_or_no_events",
        "single_observed_level",
        "event_level_absent_from_observed_levels",
    ]


def test_one_proportion_rejects_invalid_inputs_without_fake_statistic() -> None:
    with pytest.raises(OneProportionError, match="one_proportion_requires_binary_column"):
        calculate_one_proportion(
            [["yes"], ["no"], ["maybe"]],
            _response_column(),
            event_level="yes",
        )

    with pytest.raises(OneProportionError, match="one_proportion_event_level_required"):
        calculate_one_proportion(
            [["yes"], ["no"]],
            _response_column(),
            event_level=" ",
        )

    with pytest.raises(OneProportionError, match="invalid_one_proportion_null_proportion"):
        calculate_one_proportion(
            [["yes"], ["no"]],
            _response_column(),
            event_level="yes",
            null_proportion=1,
        )


def _response_column() -> OneProportionColumn:
    return OneProportionColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="text",
        measurement_level="nominal",
        role="response",
        unit=None,
    )
