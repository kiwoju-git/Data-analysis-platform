from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from app.statistics.gaussian_process_regression import (
    GaussianProcessColumn,
    GaussianProcessOptions,
    GaussianProcessRegressionError,
    build_gaussian_process_state,
    calculate_gaussian_process_regression,
    predict_from_gaussian_process_state,
)


def _columns():
    return [
        GaussianProcessColumn("y", 0, "Response", "decimal", "continuous", "response", "kg"),
        GaussianProcessColumn("category", 1, "Batch kind", "string", "nominal", "feature", None),
        GaussianProcessColumn("x", 2, "Numeric", "decimal", "continuous", "feature", "mm"),
        GaussianProcessColumn("z", 3, "Second numeric", "decimal", "continuous", "feature", None),
    ]


def _rows():
    return [
        [
            str(np.sin(i / 5) + (i % 2) * 0.7),
            "first" if i % 2 else "second",
            str(i / 5),
            str((i * 7) % 11),
        ]
        for i in range(24)
    ]


def _options(**updates):
    return replace(
        GaussianProcessOptions(
            optimizer_restarts=0,
            cv_optimizer_restarts=0,
            cv_folds=3,
            profile_points=10,
            surface_grid_size=10,
        ),
        **updates,
    )


def test_mixed_calculation_preserves_identity_profile_surface_and_restored_prediction():
    columns = _columns()
    rows = _rows()
    result = calculate_gaussian_process_regression(
        rows, columns[0], columns[1:], options=_options()
    )
    assert result["predictors"][0]["kind"] == "nominal"
    assert result["preprocessing"]["predictors"][0]["vocabulary"] == ["second", "first"]
    profile = result["conditional_profiles"][0]
    assert profile["kind"] == "nominal"
    assert {point["value"] for point in profile["points"]} == {"first", "second"}
    surface = result["two_predictor_surface"]
    assert (surface["x_column_id"], surface["y_column_id"]) == ("x", "z")
    assert all(
        point["predictive_standard_deviation"] >= point["latent_standard_deviation"]
        for point in surface["points"]
    )
    basis = result["prediction_basis"]
    state = build_gaussian_process_state(
        **basis["artifact_arrays"],
        y_mean=basis["y_mean"],
        y_scale=basis["y_scale"],
        signal_kernel_payload=basis["signal_kernel"],
        observation_noise_variance_scaled=basis["observation_noise_variance_scaled"],
        preprocessing_payload=result["preprocessing"],
    )
    prediction = predict_from_gaussian_process_state(
        state, [[row[1], float(row[2]), float(row[3])] for row in rows]
    )
    assert prediction["mean"] == pytest.approx(
        [p["fitted"] for p in result["diagnostics"]["points"]], abs=1e-10
    )
    with pytest.raises(GaussianProcessRegressionError, match="category_unknown"):
        predict_from_gaussian_process_state(state, [["never observed", 1.0, 1.0]])


def test_category_label_bijection_does_not_change_fit_or_cv():
    columns = _columns()
    rows = _rows()
    renamed = [[row[0], {"first": "999999", "second": "-10"}[row[1]], *row[2:]] for row in rows]
    left = calculate_gaussian_process_regression(rows, columns[0], columns[1:3], options=_options())
    right = calculate_gaussian_process_regression(
        renamed, columns[0], columns[1:3], options=_options()
    )
    for key in ("training_rmse", "cv_rmse", "negative_log_predictive_density"):
        assert left["model_summary"][key] == pytest.approx(
            right["model_summary"][key], rel=1e-8, abs=1e-10
        )


def test_nominal_only_is_supported_without_fake_numeric_surface():
    columns = _columns()
    result = calculate_gaussian_process_regression(
        _rows(), columns[0], [columns[1]], options=_options()
    )
    assert result["two_predictor_surface"] is None
    assert result["surface_unavailable_reason"] == "fewer_than_two_numeric_predictors"
    assert result["kernel"]["signal_kernel"]["length_scales"] == []
    assert "gp_nominal_only_signal" in result["warnings"]
    from app.services.report_warnings import report_warning_text

    assert "do not represent distinct" in report_warning_text("gp_nominal_only_signal", "", "en")
    assert "서로 다른 커널 계열" in report_warning_text("gp_nominal_only_signal", "", "ko")


def test_fold_unseen_category_is_explicit_failure_not_dropped_row():
    columns = _columns()
    rows = _rows()
    rows[0][1] = "singleton"
    with pytest.raises(GaussianProcessRegressionError, match="category_unknown"):
        calculate_gaussian_process_regression(rows, columns[0], columns[1:3], options=_options())


def test_initial_surface_axes_must_be_numeric_and_use_requested_order():
    columns = _columns()
    result = calculate_gaussian_process_regression(
        _rows(),
        columns[0],
        columns[1:],
        options=_options(
            validation_method="none",
            initial_surface_x_column_id="z",
            initial_surface_y_column_id="x",
        ),
    )
    assert result["two_predictor_surface"]["x_column_id"] == "z"
    assert result["two_predictor_surface"]["y_column_id"] == "x"
    with pytest.raises(GaussianProcessRegressionError, match="surface_axes_invalid"):
        calculate_gaussian_process_regression(
            _rows(),
            columns[0],
            columns[1:],
            options=_options(
                validation_method="none",
                initial_surface_x_column_id="category",
                initial_surface_y_column_id="x",
            ),
        )


def test_extended_resource_admission_rejects_before_any_kernel_fit(monkeypatch):
    import app.statistics.gaussian_process_regression as gp

    columns = [
        GaussianProcessColumn(f"c{i}", i, f"c{i}", "decimal", "continuous", "feature", None)
        for i in range(5)
    ]
    rows = [
        [str(np.sin(i / 10)), *[str((i * (j + 1)) % 101 + i / 1000) for j in range(4)]]
        for i in range(2000)
    ]
    monkeypatch.setattr(
        gp, "_fit_model", lambda *args, **kwargs: pytest.fail("fit before resource admission")
    )
    with pytest.raises(GaussianProcessRegressionError, match="memory_budget_exceeded"):
        calculate_gaussian_process_regression(
            rows,
            columns[0],
            columns[1:],
            options=_options(validation_method="none", resource_profile="extended_exact"),
        )
