"""Independent sklearn references: no production fit/scaling helper on expected path."""

import time
import warnings
from dataclasses import replace

import numpy as np
import pytest
from scipy.optimize import minimize
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
from sklearn.model_selection import KFold
from test_gaussian_process_regression import _column, _rows

import app.statistics.gaussian_process_regression as gp
from app.api.v1.schemas.analyses import GaussianProcessRegressionOptions
from app.services.analysis_runner_gaussian_process import _statistics_options


def data():
    rng = np.random.default_rng(872)
    x = rng.normal(size=(24, 2)) * [3, 0.3] + [8, 2]
    y = np.sin(x[:, 0] / 3) + x[:, 1] + rng.normal(0, 0.06, 24)
    return x, y


def calculate(options, x=None, y=None):
    if x is None:
        x, y = data()
    return gp.calculate_gaussian_process_regression(
        _rows(x, y),
        _column("y", x.shape[1], role="response"),
        [_column(f"x{i}", i) for i in range(x.shape[1])],
        options=options,
    )


def independent_fit(x, y, query, lower=0.01, initial=1.0, upper=100, optimizer="fmin_l_bfgs_b"):
    xm, xs = x.mean(axis=0), x.std(axis=0, ddof=1)
    ym, ys = y.mean(), y.std(ddof=1)
    kernel = ConstantKernel(1, (1e-3, 1e3)) * RBF(
        np.full(x.shape[1], initial), (lower, upper)
    ) + WhiteKernel(0.01, (1e-8, 10))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConvergenceWarning)
        model = GaussianProcessRegressor(
            kernel=kernel, alpha=1e-8, optimizer=optimizer, random_state=20260829
        ).fit((x - xm) / xs, (y - ym) / ys)
    mean, std = model.predict((query - xm) / xs, return_std=True)
    return mean * ys + ym, std * ys


def options(**kwargs):
    return gp.GaussianProcessOptions(
        kernel_preset="rbf_ard",
        optimizer_restarts=0,
        validation_method="none",
        profile_points=10,
        surface_grid_size=10,
        **kwargs,
    )


def test_fixed_posterior_matches_independent_sklearn(monkeypatch):
    monkeypatch.setattr(
        gp,
        "_bounded_optimizer",
        lambda *args: lambda objective, theta, bounds: (theta, objective(theta)[0]),
    )
    x, y = data()
    result = calculate(options(), x, y)
    mean, std = independent_fit(x, y, x, optimizer=None)
    assert [p["fitted"] for p in result["diagnostics"]["points"]] == pytest.approx(
        mean, abs=1e-9, rel=1e-9
    )
    assert [
        p["predictive_standard_deviation"] for p in result["diagnostics"]["points"]
    ] == pytest.approx(std, abs=1e-9, rel=1e-9)


@pytest.mark.parametrize("lower,initial,upper", [(0.01, 1, 100), (0.5, 1, 100), (1, 1.5, 6)])
def test_optimized_bounds_and_independent_legacy_reference(lower, initial, upper):
    x, y = data()
    result = calculate(
        options(length_scale_lower=lower, length_scale_initial=initial, length_scale_upper=upper),
        x,
        y,
    )
    mean, std = independent_fit(x, y, x, lower, initial, upper)
    assert [p["fitted"] for p in result["diagnostics"]["points"]] == pytest.approx(
        mean, abs=1e-7, rel=1e-7
    )
    assert [
        p["predictive_standard_deviation"] for p in result["diagnostics"]["points"]
    ] == pytest.approx(std, abs=1e-7, rel=1e-7)
    lengths = [p for p in result["kernel"]["parameters"] if p["parameter"] == "length_scale"]
    assert [p["column_id"] for p in lengths] == ["x0", "x1"]
    assert all(
        p["lower_bound"] == lower
        and p["upper_bound"] == upper
        and lower - 1e-12 <= p["estimate"] <= upper + 1e-12
        for p in lengths
    )
    assert result["method"]["length_scale"]["initial"] == initial


def test_transformed_analytic_gradient_matches_finite_difference():
    bounds = np.array([[-6.0, 4.0], [-2.0, 8.0], [-12.0, 0.0]])
    z = np.array([-1.4, 0.5, 2.1])
    theta, derivative = gp._bounded_theta(z, bounds)
    expected = 2 * (theta - [1, 2, -4]) * derivative

    def objective(value):
        transformed, _ = gp._bounded_theta(value, bounds)
        return np.sum((transformed - [1, 2, -4]) ** 2)

    finite = [
        (objective(z + np.eye(3)[i] * 1e-6) - objective(z - np.eye(3)[i] * 1e-6)) / 2e-6
        for i in range(3)
    ]
    assert expected == pytest.approx(finite, abs=1e-6, rel=1e-5)


@pytest.mark.parametrize("algorithm", ["l_bfgs_b", "bfgs"])
def test_actual_optimizer_path_all_bounds_and_deterministic_restarts(algorithm):
    active = replace(options(optimizer=algorithm, length_scale_lower=0.5), optimizer_restarts=1)
    first, second = calculate(active), calculate(active)
    assert first["diagnostics"] == second["diagnostics"]
    runs = first["optimization"]["final_runs"]
    assert len(runs) == 2
    for run in runs:
        assert run["scipy_method"] == ("BFGS" if algorithm == "bfgs" else "L-BFGS-B")
        theta, bounds = np.array(run["final_log_theta"]), np.array(run["log_bounds"])
        assert np.all(theta >= bounds[:, 0]) and np.all(theta <= bounds[:, 1])
        assert run["iterations"] >= 0 and run["evaluations"] > 0


def test_cv_is_independent_fold_local_reference_and_records_actual_splits():
    x, y = data()
    active = replace(options(length_scale_lower=0.5), validation_method="k_fold", cv_folds=3)
    result = calculate(active, x, y)
    expected_mean, expected_std = np.empty(len(y)), np.empty(len(y))
    for i, (train, test) in enumerate(
        KFold(3, shuffle=True, random_state=active.random_seed).split(x)
    ):
        expected_mean[test], expected_std[test] = independent_fit(
            x[train], y[train], x[test], lower=0.5
        )
        fold = result["optimization"]["cv_folds"][i]
        assert fold["validation_row_indices"] == test.tolist()
        assert fold["x_scale"] == pytest.approx(x[train].std(axis=0, ddof=1))
        assert not np.allclose(fold["x_scale"], x.std(axis=0, ddof=1))
    points = result["diagnostics"]["points"]
    assert [p["cross_validated_fitted"] for p in points] == pytest.approx(expected_mean, abs=1e-7)
    assert [p["cross_validated_predictive_standard_deviation"] for p in points] == pytest.approx(
        expected_std, abs=1e-7
    )


def test_compare_propagates_bounds_optimizer_to_cv_final_and_details():
    active = replace(
        options(optimizer="bfgs", length_scale_lower=0.5),
        validation_method="k_fold",
        cv_folds=2,
        kernel_selection_mode="compare",
        kernel_candidates=("rbf_ard", "rational_quadratic"),
        retain_candidate_details=True,
    )
    result = calculate(active)
    for candidate in result["kernel_candidates"]:
        assert candidate["status"] == "succeeded"
        detail = candidate["details"]
        assert detail["method"]["length_scale"]["lower"] == 0.5
        assert detail["method"]["optimizer"] == "bfgs"
        assert all(
            run["optimizer"] == "bfgs"
            for fold in detail["optimization"]["cv_folds"]
            for run in fold["optimizer_runs"]
        )
    assert (
        result["kernel_candidates"][0]["details"]["optimization"]["cv_folds"][0][
            "validation_row_indices"
        ]
        == result["kernel_candidates"][1]["details"]["optimization"]["cv_folds"][0][
            "validation_row_indices"
        ]
    )


@pytest.mark.parametrize(
    "change",
    [
        dict(length_scale_lower=0),
        dict(length_scale_initial=float("nan")),
        dict(length_scale_upper=float("inf")),
        dict(length_scale_lower=2),
        dict(length_scale_coordinate_system="original"),
        dict(optimizer="bfgs", length_scale_lower=1),
    ],
)
def test_invalid_settings_rejected_before_fit(change):
    with pytest.raises(gp.GaussianProcessRegressionError):
        calculate(options(**change))


def test_request_legacy_defaults_and_explicit_coordinate_validation():
    base = {"response_column_id": "y", "predictor_column_ids": ["x"]}
    assert (
        _statistics_options(
            GaussianProcessRegressionOptions.model_validate(base)
        ).length_scale_lower
        == 0.01
    )
    with pytest.raises(ValueError, match="gp_length_scale_coordinate_mismatch"):
        GaussianProcessRegressionOptions.model_validate(
            {
                **base,
                "length_scale": {
                    "lower": 0.5,
                    "initial": 1,
                    "upper": 100,
                    "coordinate_system": "original",
                },
            }
        )


def test_optimizer_timeout_and_nonconvergence_are_not_success(monkeypatch):
    def objective(theta):
        return float(theta @ theta), 2 * theta

    with pytest.raises(gp.GaussianProcessRegressionError, match="gp_time_budget_exhausted"):
        gp._bounded_optimizer(time.monotonic() - 1, "bfgs")(
            objective, np.array([1.0]), np.array([[-2.0, 2.0]])
        )
    import scipy.optimize

    def failed(*args, **kwargs):
        result = minimize(*args, **kwargs)
        result.success, result.status = False, 2
        return result

    monkeypatch.setattr(scipy.optimize, "minimize", failed)
    records = []
    with pytest.warns(ConvergenceWarning):
        gp._bounded_optimizer(None, "bfgs", records)(
            objective, np.array([1.0]), np.array([[-2.0, 2.0]])
        )
    assert records[0]["converged"] is False
