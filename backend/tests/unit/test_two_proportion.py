from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.statistics.two_proportion import (
    TwoProportionError,
    TwoProportionGroupColumn,
    TwoProportionResponseColumn,
    calculate_two_proportion,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "reference" / "fixtures"


def test_two_proportion_is_hand_checkable_for_counts_and_fisher_p_value() -> None:
    rows = [
        ["yes", "A"],
        ["yes", "A"],
        ["yes", "A"],
        ["yes", "A"],
        ["no", "A"],
        ["no", "A"],
        ["yes", "B"],
        ["no", "B"],
        ["no", "B"],
        ["no", "B"],
        ["no", "B"],
        ["no", "B"],
    ]

    result = calculate_two_proportion(
        rows,
        _response_column(),
        _group_column(),
        event_level="yes",
    )

    assert result["summary_type"] == "two_proportion_test"
    assert result["method"] == "fisher_exact_2x2"
    assert result["event_level"] == "yes"
    assert result["n_total"] == 12
    assert result["n_used"] == 12
    assert [group["group_label"] for group in result["groups"]] == ["A", "B"]
    assert [group["event_count"] for group in result["groups"]] == [4, 1]
    assert [group["non_event_count"] for group in result["groups"]] == [2, 5]
    assert [group["total"] for group in result["groups"]] == [6, 6]
    assert result["difference"]["estimate"] == pytest.approx(0.5, abs=1e-12)
    assert result["difference"]["confidence_interval"]["lower"] == pytest.approx(
        -0.04030387843204997,
        abs=1e-12,
    )
    assert result["difference"]["confidence_interval"]["upper"] == pytest.approx(
        0.7731752842826356,
        abs=1e-12,
    )
    assert result["test"]["p_value"] == pytest.approx(0.24242424242424238, abs=1e-12)
    assert result["test"]["statistic"] == pytest.approx(10.0, abs=1e-12)
    assert result["effect_sizes"]["risk_ratio"]["estimate"] == pytest.approx(4.0, abs=1e-12)
    assert result["effect_sizes"]["odds_ratio"]["estimate"] == pytest.approx(10.0, abs=1e-12)
    assert "two_proportion_binary_design_assumption" in result["warnings"]
    assert "two_proportion_fisher_exact" in result["warnings"]
    assert "small_expected_counts" in result["warnings"]


def test_two_proportion_matches_reference_fixture() -> None:
    input_payload = json.loads((FIXTURE_DIR / "two_proportion_input.json").read_text())
    reference_payload = json.loads(
        (FIXTURE_DIR / "two_proportion_reference.json").read_text(),
    )
    references = {reference["case_id"]: reference for reference in reference_payload["cases"]}

    for case in input_payload["cases"]:
        expected = references[case["case_id"]]
        result = calculate_two_proportion(
            case["rows"],
            _response_column(),
            _group_column(),
            event_level=case["event_level"],
            alpha=case["alpha"],
            confidence_level=case["confidence_level"],
            alternative=case["alternative"],
        )

        assert result["method"] == expected["method"]
        assert [group["group_label"] for group in result["groups"]] == expected["group_labels"]
        assert [group["event_count"] for group in result["groups"]] == expected["event_counts"]
        assert [group["non_event_count"] for group in result["groups"]] == expected[
            "non_event_counts"
        ]
        assert [group["total"] for group in result["groups"]] == expected["totals"]
        for group, expected_proportion in zip(
            result["groups"],
            expected["sample_proportions"],
            strict=True,
        ):
            assert group["sample_proportion"] == pytest.approx(expected_proportion, abs=1e-12)
        assert result["difference"]["estimate"] == pytest.approx(
            expected["difference"],
            abs=1e-12,
        )
        assert result["difference"]["confidence_interval"]["lower"] == pytest.approx(
            expected["difference_ci_lower"],
            abs=1e-12,
        )
        assert result["difference"]["confidence_interval"]["upper"] == pytest.approx(
            expected["difference_ci_upper"],
            abs=1e-12,
        )
        assert result["test"]["p_value"] == pytest.approx(expected["p_value"], abs=1e-12)
        assert result["effect_sizes"]["risk_ratio"]["estimate"] == pytest.approx(
            expected["risk_ratio"],
            abs=1e-12,
        )
        assert result["effect_sizes"]["risk_ratio"]["confidence_interval"][
            "lower"
        ] == pytest.approx(expected["risk_ratio_ci_lower"], abs=1e-12)
        assert result["effect_sizes"]["risk_ratio"]["confidence_interval"][
            "upper"
        ] == pytest.approx(expected["risk_ratio_ci_upper"], abs=1e-12)
        assert result["effect_sizes"]["odds_ratio"]["estimate"] == pytest.approx(
            expected["odds_ratio"],
            abs=1e-12,
        )
        assert result["effect_sizes"]["odds_ratio"]["confidence_interval"][
            "lower"
        ] == pytest.approx(expected["odds_ratio_ci_lower"], abs=1e-12)
        assert result["effect_sizes"]["odds_ratio"]["confidence_interval"][
            "upper"
        ] == pytest.approx(expected["odds_ratio_ci_upper"], abs=1e-12)


def test_two_proportion_reports_missing_and_zero_cell_warnings_without_fake_ci() -> None:
    rows = [
        ["yes", "A"],
        ["yes", "A"],
        ["", "A"],
        ["no", "B"],
        ["no", "B"],
        ["yes", ""],
    ]

    result = calculate_two_proportion(
        rows,
        _response_column(),
        _group_column(),
        event_level="yes",
    )

    assert result["n_total"] == 6
    assert result["n_used"] == 4
    assert result["n_excluded_missing_response"] == 1
    assert result["n_excluded_missing_group"] == 1
    assert "missing_values_excluded" in result["warnings"]
    assert "zero_cell_effect_ci_unavailable" in result["warnings"]
    assert result["effect_sizes"]["risk_ratio"]["estimate"] is None
    assert result["effect_sizes"]["risk_ratio"]["confidence_interval"] is None
    assert result["effect_sizes"]["odds_ratio"]["estimate"] is None
    assert result["effect_sizes"]["odds_ratio"]["confidence_interval"] is None


def test_two_proportion_rejects_invalid_inputs_without_fallback_statistic() -> None:
    with pytest.raises(TwoProportionError, match="invalid_two_proportion_alternative"):
        calculate_two_proportion(
            [["yes", "A"], ["no", "B"]],
            _response_column(),
            _group_column(),
            event_level="yes",
            alternative="sideways",
        )

    with pytest.raises(TwoProportionError, match="two_proportion_requires_exactly_two_groups"):
        calculate_two_proportion(
            [["yes", "A"], ["no", "B"], ["yes", "C"]],
            _response_column(),
            _group_column(),
            event_level="yes",
        )

    with pytest.raises(TwoProportionError, match="two_proportion_requires_binary_response"):
        calculate_two_proportion(
            [["yes", "A"], ["no", "A"], ["maybe", "B"]],
            _response_column(),
            _group_column(),
            event_level="yes",
        )


def _response_column() -> TwoProportionResponseColumn:
    return TwoProportionResponseColumn(
        column_id="response",
        column_index=0,
        display_name="response",
        data_type="string",
        measurement_level="binary",
        role="response",
        unit=None,
    )


def _group_column() -> TwoProportionGroupColumn:
    return TwoProportionGroupColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="string",
        measurement_level="nominal",
        role="group",
        unit=None,
    )
