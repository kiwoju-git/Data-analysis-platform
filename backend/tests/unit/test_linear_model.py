import csv
import hashlib
import json
from math import sqrt
from pathlib import Path

import pytest
from scipy import stats  # type: ignore[import-untyped]

from app.services.regression_models import (
    _design_vector_for_manifest,
    _dot,
    _prediction_interval,
    _quadratic_form,
)
from app.statistics.linear_model import (
    LinearModelColumn,
    LinearModelError,
    calculate_linear_model,
)

INPUT_FIXTURE = Path("backend/tests/reference/fixtures/linear_model_input.json")
REFERENCE_FIXTURE = Path("backend/tests/reference/fixtures/linear_model_numpy_reference.json")
STATSMODELS_REFERENCE_FIXTURE = Path(
    "backend/tests/reference/fixtures/regression_linear_model_reference.json",
)
STATSMODELS_REFERENCE_CSV = Path(
    "backend/tests/reference/fixtures/regression_linear_model_reference.csv",
)


def test_linear_model_is_hand_checkable_for_shape_and_fit() -> None:
    result = calculate_linear_model(
        [
            ["10", "1", "3"],
            ["13", "2", "2"],
            ["15", "3", "4"],
            ["18", "4", "3"],
            ["21", "5", "5"],
            ["23", "6", "4"],
            ["26", "7", "6"],
            ["29", "8", "5"],
        ],
        _response_column(),
        [_x1_column(), _x2_column()],
    )

    assert result["schema_version"] == 4
    assert result["summary_type"] == "linear_model"
    assert result["method"] == "ordinary_least_squares_numeric_predictors"
    assert result["missing_policy"] == "complete_case"
    assert result["warnings"] == [
        "linear_model_not_causation",
        "linear_model_linearity_assumption",
        "linear_model_independence_assumption",
        "linear_model_homoscedasticity_assumption",
        "linear_model_residual_normality_assumption",
        "linear_model_outlier_influence_sensitive",
    ]
    assert result["sample"] == {
        "n_total": 8,
        "n_used": 8,
        "n_excluded_missing": 0,
        "n_excluded_non_numeric": 0,
        "df_model": 2,
        "df_residual": 5,
    }
    fit = result["fit"]
    assert isinstance(fit, dict)
    assert fit["r_squared"] == pytest.approx(0.9982608695652174, abs=1e-12)
    coefficients = _coefficients_by_term(result)
    assert coefficients["Intercept"]["estimate"] == pytest.approx(7.425, abs=1e-12)
    assert coefficients["x1"]["estimate"] == pytest.approx(2.7, abs=1e-12)
    assert coefficients["x2"]["estimate"] == pytest.approx(-0.05, abs=1e-12)
    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["diagnostic_points"]["points_included"] == 8
    assert diagnostics["diagnostic_points"]["truncated"] is False
    first_point = diagnostics["diagnostic_points"]["points"][0]
    assert set(first_point) == {
        "row_index",
        "fitted",
        "residual",
        "standardized_residual",
        "leverage",
        "cooks_distance",
    }


def test_linear_model_supports_categorical_main_effect_treatment_coding() -> None:
    result = calculate_linear_model(
        [
            ["10", "A"],
            ["11", "A"],
            ["13", "B"],
            ["14", "B"],
            ["16", "C"],
            ["17", "C"],
        ],
        _response_column(),
        [_group_column()],
    )

    assert result["schema_version"] == 4
    assert result["method"] == "ordinary_least_squares_main_effects"
    assert "linear_model_categorical_treatment_coding" in result["warnings"]
    assert result["sample"] == {
        "n_total": 6,
        "n_used": 6,
        "n_excluded_missing": 0,
        "n_excluded_non_numeric": 0,
        "df_model": 2,
        "df_residual": 3,
    }
    specification = result["model_specification"]
    assert isinstance(specification, dict)
    assert specification["terms"] == [
        {
            "term": "group",
            "kind": "categorical_main_effect",
            "column_id": "group",
            "coding": "treatment",
            "reference_level": "A",
            "levels": ["A", "B", "C"],
        },
    ]
    fit = result["fit"]
    assert isinstance(fit, dict)
    assert fit["r_squared"] == pytest.approx(0.96, abs=1e-12)
    coefficients = _coefficients_by_term(result)
    assert coefficients["Intercept"]["estimate"] == pytest.approx(10.5, abs=1e-12)
    assert coefficients["group[B]"]["estimate"] == pytest.approx(3.0, abs=1e-12)
    assert coefficients["group[B]"]["level"] == "B"
    assert coefficients["group[B]"]["reference_level"] == "A"
    assert coefficients["group[B]"]["coding"] == "treatment"
    assert coefficients["group[C]"]["estimate"] == pytest.approx(6.0, abs=1e-12)
    assert coefficients["group[C]"]["level"] == "C"


def test_linear_model_supports_numeric_quadratic_and_interaction_terms() -> None:
    result = calculate_linear_model(
        [
            ["3.2", "-2", "0"],
            ["0.9", "-1", "1"],
            ["3.05", "0", "2"],
            ["7.5", "1", "0"],
            ["12.95", "2", "1"],
            ["22.6", "3", "2"],
            ["20.8", "4", "0"],
            ["34.05", "5", "1"],
        ],
        _response_column(),
        [_x1_column(), _x2_column()],
        quadratic_terms=["x1"],
        interaction_terms=[("x1", "x2")],
    )

    assert result["schema_version"] == 4
    assert result["method"] == "ordinary_least_squares_safe_terms"
    assert "linear_model_quadratic_terms_selected" in result["warnings"]
    assert "linear_model_interaction_terms_selected" in result["warnings"]
    assert result["sample"] == {
        "n_total": 8,
        "n_used": 8,
        "n_excluded_missing": 0,
        "n_excluded_non_numeric": 0,
        "df_model": 4,
        "df_residual": 3,
    }
    specification = result["model_specification"]
    assert isinstance(specification, dict)
    assert specification["terms"] == [
        {
            "term": "x1",
            "kind": "numeric_main_effect",
            "column_id": "x1",
            "source_column_ids": ["x1"],
        },
        {
            "term": "x2",
            "kind": "numeric_main_effect",
            "column_id": "x2",
            "source_column_ids": ["x2"],
        },
        {
            "term": "x1^2",
            "kind": "numeric_quadratic",
            "column_id": "x1",
            "source_column_ids": ["x1"],
        },
        {
            "term": "x1:x2",
            "kind": "numeric_interaction",
            "column_id": None,
            "source_column_ids": ["x1", "x2"],
        },
    ]
    coefficients = _coefficients_by_term(result)
    assert coefficients["Intercept"]["estimate"] == pytest.approx(
        5.018918918918922,
        abs=1e-12,
    )
    assert coefficients["x1"]["estimate"] == pytest.approx(1.9327702702702732, abs=1e-12)
    assert coefficients["x2"]["estimate"] == pytest.approx(-1.027027027027025, abs=1e-12)
    assert coefficients["x1^2"]["estimate"] == pytest.approx(
        0.5040540540540538,
        abs=1e-12,
    )
    assert coefficients["x1^2"]["source_column_ids"] == ["x1"]
    assert coefficients["x1:x2"]["estimate"] == pytest.approx(
        1.5542792792792784,
        abs=1e-12,
    )
    assert coefficients["x1:x2"]["source_column_ids"] == ["x1", "x2"]


def test_linear_model_matches_numpy_reference_fixture() -> None:
    fixture = json.loads(INPUT_FIXTURE.read_text(encoding="utf-8"))
    reference = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))

    result = calculate_linear_model(
        fixture["rows"],
        _response_column(),
        [_x1_column(), _x2_column()],
        alpha=0.05,
        confidence_level=0.95,
    )

    fit = result["fit"]
    assert isinstance(fit, dict)
    for key, expected in reference["fit"].items():
        assert fit[key] == pytest.approx(expected, abs=1e-12)

    coefficients = _coefficients_by_term(result)
    for term, expected in reference["coefficients"].items():
        coefficient = coefficients[term]
        assert coefficient["estimate"] == pytest.approx(expected["estimate"], abs=1e-12)
        assert coefficient["standard_error"] == pytest.approx(
            expected["standard_error"],
            abs=1e-12,
        )
        assert coefficient["statistic"] == pytest.approx(expected["statistic"], abs=1e-12)
        assert coefficient["p_value"] == pytest.approx(expected["p_value"], abs=1e-12)
        ci = coefficient["confidence_interval"]
        assert isinstance(ci, dict)
        assert ci["lower"] == pytest.approx(expected["ci_low"], abs=1e-12)
        assert ci["upper"] == pytest.approx(expected["ci_high"], abs=1e-12)
        if "vif" in expected:
            assert coefficient["vif"] == pytest.approx(expected["vif"], abs=1e-12)

    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)
    for key, expected in reference["diagnostics"].items():
        if key == "diagnostic_points":
            point_payload = diagnostics[key]
            assert isinstance(point_payload, dict)
            assert point_payload["point_limit"] == expected["point_limit"]
            assert point_payload["points_included"] == expected["points_included"]
            assert point_payload["truncated"] == expected["truncated"]
            points = point_payload["points"]
            assert isinstance(points, list)
            _assert_nested_approx(points[0], expected["first_point"])
            max_cooks_point = max(
                points,
                key=lambda point: point["cooks_distance"]
                if isinstance(point["cooks_distance"], float)
                else -1.0,
            )
            _assert_nested_approx(max_cooks_point, expected["max_cooks_distance_point"])
            continue
        _assert_nested_approx(diagnostics[key], expected)


def test_linear_model_matches_statsmodels_treatment_and_prediction_reference() -> None:
    fixture = json.loads(STATSMODELS_REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    tolerance = fixture["tolerances"]["statsmodels_absolute"]
    expected = fixture["expected"]

    assert fixture["source"]["tool"] == "statsmodels"
    assert fixture["source"]["version"] == "0.14.6"
    assert "temporary reference-generation environment" in (fixture["source"]["license_review"])
    assert "fully synthetic" in fixture["source"]["data_review"]
    assert "not pinned" in fixture["conventions"]["manifest_checksum_contract"]
    assert (
        hashlib.sha256(STATSMODELS_REFERENCE_CSV.read_bytes()).hexdigest()
        == (fixture["input"]["csv_sha256"])
    )

    with STATSMODELS_REFERENCE_CSV.open(encoding="utf-8", newline="") as handle:
        rows = [[row["y"], row["x"], row["group"]] for row in csv.DictReader(handle)]
    result = calculate_linear_model(
        rows,
        _response_column(),
        [_x1_named_x_column(), _group_column_index_2()],
        alpha=0.05,
        confidence_level=0.95,
    )

    assert result["sample"] == expected["sample"]
    specification = result["model_specification"]
    assert isinstance(specification, dict)
    assert specification["terms"][1] == {
        "term": "group",
        "kind": "categorical_main_effect",
        "column_id": "group",
        "coding": "treatment",
        "reference_level": fixture["input"]["reference_level"],
        "levels": fixture["input"]["categorical_levels"],
    }

    fit = result["fit"]
    assert isinstance(fit, dict)
    for key, expected_value in expected["fit"].items():
        assert fit[key] == pytest.approx(expected_value, abs=tolerance)

    coefficients = _coefficients_by_term(result)
    assert list(coefficients) == expected["application_coefficient_order"]
    assert (
        result["prediction_basis"]["coefficient_order"]
        == (expected["application_coefficient_order"])
    )
    for term, expected_coefficient in expected["coefficients"].items():
        assert (
            fixture["conventions"]["term_mapping"][term]
            == (expected_coefficient["statsmodels_term"])
        )
        coefficient = coefficients[term]
        for field in ("estimate", "standard_error", "statistic", "p_value"):
            assert coefficient[field] == pytest.approx(
                expected_coefficient[field],
                abs=tolerance,
            )
        interval = coefficient["confidence_interval"]
        assert isinstance(interval, dict)
        assert interval["lower"] == pytest.approx(
            expected_coefficient["ci_lower"],
            abs=tolerance,
        )
        assert interval["upper"] == pytest.approx(
            expected_coefficient["ci_upper"],
            abs=tolerance,
        )
        if expected_coefficient["vif"] is None:
            assert coefficient["vif"] is None
        else:
            assert coefficient["vif"] == pytest.approx(
                expected_coefficient["vif"],
                abs=tolerance,
            )

    diagnostics = result["diagnostics"]
    assert isinstance(diagnostics, dict)
    assert diagnostics["condition_number"] == pytest.approx(
        expected["condition_number"],
        abs=tolerance,
    )
    assert result["warnings"] == expected["warnings"]

    basis = result["prediction_basis"]
    assert isinstance(basis, dict)
    coefficient_estimates = [
        float(coefficients[term]["estimate"]) for term in basis["coefficient_order"]
    ]
    t_critical = float(
        stats.t.ppf(0.975, df=basis["df_residual"]),
    )
    for prediction in expected["predictions"]:
        design_vector = _design_vector_for_manifest(
            manifest={"model_specification": specification},
            values_by_source_column_id={
                "x": float(prediction["x"]),
                "group": prediction["group"],
            },
        )
        predicted_mean = _dot(design_vector, coefficient_estimates)
        leverage = _quadratic_form(design_vector, basis["xtx_inverse"])
        mean_interval = _prediction_interval(
            center=predicted_mean,
            standard_error=sqrt(basis["sigma_squared"] * leverage),
            t_critical=t_critical,
            confidence_level=0.95,
        )
        observation_interval = _prediction_interval(
            center=predicted_mean,
            standard_error=sqrt(basis["sigma_squared"] * (1.0 + leverage)),
            t_critical=t_critical,
            confidence_level=0.95,
        )
        assert predicted_mean == pytest.approx(
            prediction["predicted_mean"],
            abs=tolerance,
        )
        assert mean_interval.lower == pytest.approx(
            prediction["mean_ci_lower"],
            abs=tolerance,
        )
        assert mean_interval.upper == pytest.approx(
            prediction["mean_ci_upper"],
            abs=tolerance,
        )
        assert observation_interval.lower == pytest.approx(
            prediction["prediction_interval_lower"],
            abs=tolerance,
        )
        assert observation_interval.upper == pytest.approx(
            prediction["prediction_interval_upper"],
            abs=tolerance,
        )


def test_linear_model_statsmodels_fixture_rejects_single_factor_level() -> None:
    fixture = json.loads(STATSMODELS_REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    case = fixture["failure_case"]

    with pytest.raises(LinearModelError, match=case["expected_error"]):
        calculate_linear_model(
            case["rows"],
            _response_column(),
            [_x1_named_x_column(), _group_column_index_2()],
        )


def test_linear_model_reports_complete_case_exclusions_and_warnings() -> None:
    result = calculate_linear_model(
        [
            ["10", "1", "3"],
            ["", "2", "2"],
            ["15", "3", "bad"],
            ["18", "4", "3"],
            ["21", "5", "5"],
            ["23", "6", "4"],
            ["26", "7", "6"],
            ["29", "8", "5"],
            ["32", "9", "6"],
        ],
        _response_column(),
        [_x1_column(), _x2_column()],
    )

    sample = result["sample"]
    assert isinstance(sample, dict)
    assert sample["n_total"] == 9
    assert sample["n_used"] == 7
    assert sample["n_excluded_missing"] == 1
    assert sample["n_excluded_non_numeric"] == 1
    assert "missing_values_excluded" in result["warnings"]
    assert "non_numeric_values_excluded" in result["warnings"]


def test_linear_model_rejects_invalid_inputs_without_fake_statistics() -> None:
    with pytest.raises(LinearModelError, match="invalid_linear_model_alpha"):
        calculate_linear_model(
            [["1", "1"]],
            _response_column(),
            [_x1_column()],
            alpha=0,
        )

    with pytest.raises(LinearModelError, match="linear_model_predictors_required"):
        calculate_linear_model([["1"]], _response_column(), [])

    with pytest.raises(LinearModelError, match="linear_model_residual_df_too_small"):
        calculate_linear_model(
            [["1", "1"], ["2", "2"]],
            _response_column(),
            [_x1_column()],
        )

    with pytest.raises(LinearModelError, match="linear_model_response_constant"):
        calculate_linear_model(
            [["1", "1"], ["1", "2"], ["1", "3"], ["1", "4"]],
            _response_column(),
            [_x1_column()],
        )

    with pytest.raises(LinearModelError, match="linear_model_predictor_constant"):
        calculate_linear_model(
            [["1", "1"], ["2", "1"], ["3", "1"], ["4", "1"]],
            _response_column(),
            [_x1_column()],
        )

    with pytest.raises(LinearModelError, match="linear_model_design_rank_deficient"):
        calculate_linear_model(
            [["1", "1", "2"], ["2", "2", "4"], ["3", "3", "6"], ["4", "4", "8"]],
            _response_column(),
            [_x1_column(), _x2_column()],
        )

    with pytest.raises(LinearModelError, match="linear_model_factor_single_level"):
        calculate_linear_model(
            [["1", "A"], ["2", "A"], ["3", "A"], ["4", "A"]],
            _response_column(),
            [_group_column()],
        )

    with pytest.raises(LinearModelError, match="linear_model_factor_too_many_levels"):
        calculate_linear_model(
            [[str(index), f"L{index}"] for index in range(1, 27)],
            _response_column(),
            [_group_column()],
        )

    with pytest.raises(
        LinearModelError,
        match="linear_model_predictor_column_unsupported_type",
    ):
        calculate_linear_model(
            [["1", "2026-01-01"], ["2", "2026-01-02"], ["3", "2026-01-03"]],
            _response_column(),
            [_datetime_column()],
        )

    with pytest.raises(LinearModelError, match="linear_model_term_predictor_not_selected"):
        calculate_linear_model(
            [["1", "1"], ["2", "2"], ["3", "3"], ["5", "4"]],
            _response_column(),
            [_x1_column()],
            quadratic_terms=["x2"],
        )

    with pytest.raises(LinearModelError, match="linear_model_term_requires_numeric_predictor"):
        calculate_linear_model(
            [["1", "1", "A"], ["2", "2", "B"], ["3", "3", "A"], ["5", "4", "B"]],
            _response_column(),
            [_x1_column(), _group_column_index_2()],
            interaction_terms=[("x1", "group")],
        )


def _coefficients_by_term(result: dict[str, object]) -> dict[str, dict[str, object]]:
    coefficients = result["coefficients"]
    assert isinstance(coefficients, list)
    by_term: dict[str, dict[str, object]] = {}
    for coefficient in coefficients:
        assert isinstance(coefficient, dict)
        by_term[str(coefficient["term"])] = coefficient
    return by_term


def _assert_nested_approx(actual: object, expected: object) -> None:
    if isinstance(expected, float):
        assert actual == pytest.approx(expected, abs=1e-12)
        return
    if isinstance(expected, list):
        assert actual == expected
        return
    if isinstance(expected, dict):
        assert isinstance(actual, dict)
        for key, nested_expected in expected.items():
            _assert_nested_approx(actual[key], nested_expected)
        return
    assert actual == expected


def _response_column() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="y",
        column_index=0,
        display_name="y",
        data_type="decimal",
        measurement_level="continuous",
        role="response",
        unit=None,
    )


def _x1_column() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="x1",
        column_index=1,
        display_name="x1",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _x1_named_x_column() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="x",
        column_index=1,
        display_name="x",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _x2_column() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="x2",
        column_index=2,
        display_name="x2",
        data_type="decimal",
        measurement_level="continuous",
        role="feature",
        unit=None,
    )


def _group_column() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="group",
        column_index=1,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="factor",
        unit=None,
    )


def _group_column_index_2() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="group",
        column_index=2,
        display_name="group",
        data_type="text",
        measurement_level="nominal",
        role="factor",
        unit=None,
    )


def _datetime_column() -> LinearModelColumn:
    return LinearModelColumn(
        column_id="date",
        column_index=1,
        display_name="date",
        data_type="datetime",
        measurement_level="datetime",
        role="feature",
        unit=None,
    )
