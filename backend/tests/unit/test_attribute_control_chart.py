import json
from pathlib import Path

import pytest

from app.statistics.attribute_control_chart import (
    AttributeControlChartColumn,
    AttributeControlChartError,
    calculate_attribute_control_chart,
    calculate_attribute_control_chart_phase_2,
)

REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/quality_attribute_control_chart_nist_reference.json"
)


def test_c_chart_matches_nist_published_counts_example() -> None:
    fixture = _fixture()["c_chart"]
    result = calculate_attribute_control_chart(
        [[str(value)] for value in fixture["counts"]],
        _count_column(),
        None,
        chart_type="c",
        count_definition="defects",
        constant_opportunity_confirmed=True,
    )

    expected = fixture["expected"]
    assert result["summary_type"] == "attribute_control_chart"
    assert result["method"] == "c_chart"
    assert result["center_line"] == pytest.approx(expected["center_line"], abs=1e-12)
    assert result["chart"]["points"][0]["lcl"] == pytest.approx(expected["lcl"], abs=1e-12)
    assert result["chart"]["points"][0]["ucl"] == pytest.approx(expected["ucl"], abs=1e-12)
    assert [signal["position"] for signal in result["signals"]] == expected[
        "strict_signal_positions"
    ]
    assert result["chart"]["points"][2]["value"] == expected["ucl"]
    assert result["chart"]["points"][2]["signal_codes"] == []
    assert result["chart"]["points"][23]["signal_codes"] == [
        "attribute_control_chart_point_beyond_control_limits"
    ]


def test_p_and_np_charts_match_nist_proportions_example() -> None:
    fixture = _fixture()
    rows = [[str(count), "50"] for count in fixture["p_chart"]["counts"]]
    p_result = calculate_attribute_control_chart(
        rows,
        _count_column(),
        _denominator_column(),
        chart_type="p",
        count_definition="defectives",
    )
    np_result = calculate_attribute_control_chart(
        rows,
        _count_column(),
        _denominator_column(),
        chart_type="np",
        count_definition="defectives",
    )

    p_expected = fixture["p_chart"]["expected"]
    assert p_result["center_line"] == pytest.approx(p_expected["center_line"], abs=1e-12)
    assert p_result["chart"]["points"][0]["lcl"] == pytest.approx(p_expected["lcl"], abs=1e-12)
    assert p_result["chart"]["points"][0]["ucl"] == pytest.approx(p_expected["ucl"], abs=1e-12)
    np_expected = fixture["np_chart"]["expected"]
    assert np_result["center_line"] == pytest.approx(np_expected["center_line"], abs=1e-12)
    assert np_result["chart"]["points"][0]["lcl"] == pytest.approx(np_expected["lcl"], abs=1e-12)
    assert np_result["chart"]["points"][0]["ucl"] == pytest.approx(np_expected["ucl"], abs=1e-12)


def test_u_chart_matches_independently_evaluated_nist_formula() -> None:
    fixture = _fixture()["u_chart"]
    result = calculate_attribute_control_chart(
        [
            [str(count), str(opportunity)]
            for count, opportunity in zip(fixture["counts"], fixture["opportunities"], strict=True)
        ],
        _count_column(),
        _denominator_column(),
        chart_type="u",
        count_definition="defects",
    )

    expected = fixture["expected"]
    assert result["center_line"] == pytest.approx(expected["center_line"], abs=1e-12)
    assert result["limits_vary"] is True
    assert [point["lcl"] for point in result["chart"]["points"]] == pytest.approx(
        expected["lcl"], abs=1e-12
    )
    assert [point["ucl"] for point in result["chart"]["points"]] == pytest.approx(
        expected["ucl"], abs=1e-12
    )
    assert result["total_count"] == 29
    assert result["total_denominator"] == 60


def test_p_chart_uses_weighted_center_and_point_specific_limits() -> None:
    result = calculate_attribute_control_chart(
        [["1", "10"], ["4", "20"], ["3", "10"]],
        _count_column(),
        _denominator_column(),
        chart_type="p",
        count_definition="defectives",
    )

    assert result["center_line"] == pytest.approx(0.2)
    assert result["limits_vary"] is True
    assert result["chart"]["points"][0]["ucl"] != result["chart"]["points"][1]["ucl"]
    assert result["dispersion"]["used_to_adjust_limits"] is False
    assert "attribute_control_chart_normal_approximation_weak" in result["warnings"]


def test_attribute_chart_reports_exclusions_truncation_and_no_raw_labels() -> None:
    result = calculate_attribute_control_chart(
        [["1", "10"], ["", "20"], ["bad", "20"], ["2", ""], ["3", "bad"], ["4", "20"]],
        _count_column(),
        _denominator_column(),
        chart_type="p",
        count_definition="defectives",
        point_limit=1,
    )

    assert result["n_total"] == 6
    assert result["n_used"] == 2
    assert result["n_excluded_missing_count"] == 1
    assert result["n_excluded_non_numeric_count"] == 1
    assert result["n_excluded_missing_denominator"] == 1
    assert result["n_excluded_non_numeric_denominator"] == 1
    assert result["chart"]["points_truncated"] is True
    assert len(result["chart"]["points"]) == 1
    serialized = json.dumps(result, ensure_ascii=False)
    assert "bad" not in serialized
    assert "attribute_control_chart_points_truncated" in result["warnings"]


@pytest.mark.parametrize(
    ("rows", "chart_type", "definition", "denominator", "confirmed", "error"),
    [
        ([["-1"], ["2"]], "c", "defects", False, True, "attribute_control_chart_negative_count"),
        (
            [["1.5"], ["2"]],
            "c",
            "defects",
            False,
            True,
            "attribute_control_chart_non_integer_count",
        ),
        (
            [["NaN"], ["2"]],
            "c",
            "defects",
            False,
            True,
            "attribute_control_chart_count_not_finite",
        ),
        (
            [["1", "0"], ["2", "10"]],
            "p",
            "defectives",
            True,
            False,
            "attribute_control_chart_denominator_not_positive",
        ),
        (
            [["1", "Infinity"], ["2", "10"]],
            "p",
            "defectives",
            True,
            False,
            "attribute_control_chart_denominator_not_finite",
        ),
        (
            [["1", "10.5"], ["2", "10"]],
            "p",
            "defectives",
            True,
            False,
            "attribute_control_chart_sample_size_not_integer",
        ),
        (
            [["11", "10"], ["2", "10"]],
            "p",
            "defectives",
            True,
            False,
            "attribute_control_chart_defectives_exceed_sample_size",
        ),
        (
            [["1", "10"], ["2", "20"]],
            "np",
            "defectives",
            True,
            False,
            "attribute_control_chart_np_varying_sample_size",
        ),
        (
            [["1"], ["2"]],
            "p",
            "defectives",
            False,
            False,
            "attribute_control_chart_denominator_required",
        ),
        (
            [["1"], ["2"]],
            "c",
            "defects",
            False,
            False,
            "attribute_control_chart_c_constant_opportunity_required",
        ),
        (
            [["1"], ["2"]],
            "c",
            "defectives",
            False,
            True,
            "attribute_control_chart_count_definition_mismatch",
        ),
        ([["0"], ["0"]], "c", "defects", False, True, "attribute_control_chart_zero_variation"),
    ],
)
def test_attribute_chart_rejects_invalid_inputs_without_fallback(
    rows: list[list[str]],
    chart_type: str,
    definition: str,
    denominator: bool,
    confirmed: bool,
    error: str,
) -> None:
    with pytest.raises(AttributeControlChartError, match=error):
        calculate_attribute_control_chart(
            rows,
            _count_column(),
            _denominator_column() if denominator else None,
            chart_type=chart_type,
            count_definition=definition,
            constant_opportunity_confirmed=confirmed,
        )


def test_phase_2_uses_frozen_center_without_refitting_monitoring_rows() -> None:
    result = calculate_attribute_control_chart_phase_2(
        [["0", "20"], ["0", "40"]],
        _count_column(),
        _denominator_column(),
        chart_type="p",
        count_definition="defectives",
        frozen_center_line=0.25,
        fixed_sample_size=None,
    )

    assert result["center_line"] == 0.25
    assert result["total_count"] == 0
    assert result["control_limit_method"] == "phase_2_frozen_three_sigma"
    assert "attribute_control_chart_phase_2_limits_frozen_from_verified_asset" in result["warnings"]


@pytest.mark.parametrize(
    ("rows", "chart_type", "count_definition", "center", "fixed_sample_size", "denominator"),
    [
        ([["6", "20"]], "p", "defectives", 0.5, None, True),
        ([["6", "20"]], "np", "defectives", 10.0, 20, True),
        ([["6"]], "c", "defects", 10.0, None, False),
        ([["6", "20"]], "u", "defects", 0.5, None, True),
    ],
)
def test_phase_2_accepts_one_monitoring_point_without_fake_dispersion(
    rows,
    chart_type,
    count_definition,
    center,
    fixed_sample_size,
    denominator,
) -> None:
    result = calculate_attribute_control_chart_phase_2(
        rows,
        _count_column(),
        _denominator_column() if denominator else None,
        chart_type=chart_type,
        count_definition=count_definition,
        frozen_center_line=center,
        fixed_sample_size=fixed_sample_size,
        constant_opportunity_confirmed=chart_type == "c",
    )

    assert result["schema_version"] == 3
    assert result["n_used"] == 1
    assert result["chart"]["point_count"] == 1
    assert result["dispersion"] == {
        "available": False,
        "method": "pearson_chi_square_over_degrees_of_freedom_against_frozen_center",
        "degrees_of_freedom": 0,
        "ratio": None,
        "reason_code": "attribute_control_chart_dispersion_insufficient_points",
        "warning_threshold": 2.0,
        "used_to_adjust_limits": False,
    }


def test_phase_2_two_points_restore_available_dispersion() -> None:
    result = calculate_attribute_control_chart_phase_2(
        [["9"], ["11"]],
        _count_column(),
        None,
        chart_type="c",
        count_definition="defects",
        frozen_center_line=10.0,
        fixed_sample_size=None,
        constant_opportunity_confirmed=True,
    )

    assert result["dispersion"]["available"] is True
    assert result["dispersion"]["degrees_of_freedom"] == 1
    assert result["dispersion"]["ratio"] == pytest.approx(0.2)
    assert result["dispersion"]["reason_code"] is None


def test_phase_2_uses_strict_limit_boundary_for_single_point() -> None:
    equality = calculate_attribute_control_chart_phase_2(
        [["4"]],
        _count_column(),
        None,
        chart_type="c",
        count_definition="defects",
        frozen_center_line=1.0,
        fixed_sample_size=None,
        constant_opportunity_confirmed=True,
    )
    outside = calculate_attribute_control_chart_phase_2(
        [["5"]],
        _count_column(),
        None,
        chart_type="c",
        count_definition="defects",
        frozen_center_line=1.0,
        fixed_sample_size=None,
        constant_opportunity_confirmed=True,
    )

    assert equality["chart"]["points"][0]["value"] == equality["chart"]["points"][0]["ucl"]
    assert equality["signals"] == []
    assert [signal["limit"] for signal in outside["signals"]] == ["upper"]


def test_phase_2_rejects_zero_usable_monitoring_points() -> None:
    with pytest.raises(
        AttributeControlChartError,
        match="attribute_control_chart_phase_2_no_usable_points",
    ):
        calculate_attribute_control_chart_phase_2(
            [[""], ["not-a-count"]],
            _count_column(),
            None,
            chart_type="c",
            count_definition="defects",
            frozen_center_line=10.0,
            fixed_sample_size=None,
            constant_opportunity_confirmed=True,
        )


def test_phase_2_np_rejects_sample_size_different_from_frozen_asset() -> None:
    with pytest.raises(
        AttributeControlChartError,
        match="attribute_control_chart_phase_2_np_sample_size_mismatch",
    ):
        calculate_attribute_control_chart_phase_2(
            [["2", "20"], ["3", "21"]],
            _count_column(),
            _denominator_column(),
            chart_type="np",
            count_definition="defectives",
            frozen_center_line=5.0,
            fixed_sample_size=20,
        )


def test_phase_2_c_requires_current_equal_opportunity_confirmation() -> None:
    with pytest.raises(
        AttributeControlChartError,
        match="attribute_control_chart_phase_2_c_opportunity_confirmation_required",
    ):
        calculate_attribute_control_chart_phase_2(
            [["2"], ["3"]],
            _count_column(),
            None,
            chart_type="c",
            count_definition="defects",
            frozen_center_line=5.0,
            fixed_sample_size=None,
        )


def _fixture() -> dict[str, object]:
    return json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))


def _count_column() -> AttributeControlChartColumn:
    return AttributeControlChartColumn(
        column_id="count",
        column_index=0,
        display_name="Count",
        data_type="integer",
        measurement_level="count",
        role="response",
        unit=None,
    )


def _denominator_column() -> AttributeControlChartColumn:
    return AttributeControlChartColumn(
        column_id="denominator",
        column_index=1,
        display_name="Sample size or opportunity",
        data_type="decimal",
        measurement_level="ratio",
        role="weight",
        unit=None,
    )
