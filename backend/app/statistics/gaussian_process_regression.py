from __future__ import annotations

import importlib.metadata
import time
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from math import isfinite, log, pi, sqrt
from typing import Any, Literal, cast

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import solve_triangular  # type: ignore[import-untyped]
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
KernelPreset = Literal[
    "matern_5_2_ard",
    "matern_3_2_ard",
    "rbf_ard",
    "rational_quadratic",
]
NoiseMode = Literal["estimate", "fixed", "near_noiseless"]
ValidationMethod = Literal["k_fold", "leave_one_out", "none"]

MAX_GP_PREDICTORS = 12
MAX_GP_USABLE_ROWS = 500
MAX_GP_LOO_ROWS = 200
MAX_GP_OPTIMIZER_STARTS = 256
NORMAL_975 = 1.959963984540054
BOUND_WARNING_FRACTION = 0.01


class GaussianProcessRegressionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GaussianProcessColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class GaussianProcessOptions:
    kernel_preset: KernelPreset = "matern_5_2_ard"
    noise_mode: NoiseMode = "estimate"
    fixed_noise_standard_deviation: float | None = None
    standardize_predictors: bool = True
    normalize_response: bool = True
    jitter: float = 1e-8
    optimizer_restarts: int = 3
    cv_optimizer_restarts: int = 0
    random_seed: int = 20260829
    validation_method: ValidationMethod = "k_fold"
    cv_folds: int = 5
    cv_shuffle: bool = True
    plot_point_limit: int = 1000
    profile_points: int = 50
    surface_grid_size: int = 25
    time_budget_seconds: float = 120.0
    kernel_selection_mode: Literal["single", "compare"] = "single"
    kernel_candidates: tuple[KernelPreset, ...] = ()
    selection_criterion: Literal["cv_nlpd", "cv_rmse", "cv_mae"] = "cv_nlpd"
    retain_candidate_details: bool = False
    deadline_monotonic: float | None = None


@dataclass(frozen=True)
class _ParsedRows:
    x: FloatArray
    y: FloatArray
    row_indices: list[int]
    n_total: int
    n_excluded_missing: int
    n_excluded_non_numeric: int


@dataclass(frozen=True)
class GaussianProcessFittedState:
    x_train_scaled: FloatArray
    cholesky: FloatArray
    dual_coefficients: FloatArray
    x_mean: FloatArray
    x_scale: FloatArray
    y_mean: float
    y_scale: float
    predictor_medians: FloatArray
    signal_kernel: Any
    signal_kernel_payload: dict[str, object]
    observation_noise_variance_scaled: float
    fitted_kernel_text: str
    log_marginal_likelihood: float
    converged: bool


@dataclass(frozen=True)
class _FitResult:
    state: GaussianProcessFittedState
    fitted: FloatArray
    latent_standard_deviation: FloatArray
    predictive_standard_deviation: FloatArray
    elapsed_seconds: float


@dataclass(frozen=True)
class _ValidationResult:
    mean: FloatArray | None
    latent_std: FloatArray | None
    predictive_std: FloatArray | None
    converged_folds: int
    fold_count: int


def optimizer_start_count(options: GaussianProcessOptions, fold_count: int) -> int:
    count = len(options.kernel_candidates) if options.kernel_selection_mode == "compare" else 1
    refits = count if options.retain_candidate_details else 1
    return count * fold_count * (1 + options.cv_optimizer_restarts) + refits * (
        1 + options.optimizer_restarts
    )


def calculate_gaussian_process_regression(
    rows: Iterable[Sequence[str | None]],
    response_column: GaussianProcessColumn,
    predictor_columns: Sequence[GaussianProcessColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    options: GaussianProcessOptions | None = None,
) -> dict[str, object]:
    active = options or GaussianProcessOptions()
    _validate_columns(response_column, predictor_columns)
    _validate_options(active)
    parsed = _parse_rows(
        rows,
        response_column,
        predictor_columns,
        decimal=decimal,
        thousands=thousands,
    )
    _validate_sample(parsed, len(predictor_columns), active)
    started = time.monotonic()
    active = replace(active, deadline_monotonic=started + active.time_budget_seconds)
    splits = _validation_splits(parsed.y.size, active)
    if optimizer_start_count(active, len(splits)) > MAX_GP_OPTIMIZER_STARTS:
        raise GaussianProcessRegressionError("gp_kernel_search_budget_exceeded")
    if active.kernel_selection_mode == "compare":
        from app.statistics.gaussian_process_kernel_selection import compare_kernel_candidates

        return compare_kernel_candidates(
            parsed, response_column, predictor_columns, active, splits, started
        )
    validation = _cross_validate(parsed, active, splits, started)
    _check_time_budget(started, active)
    with threadpool_limits(limits=1):
        final = _fit_model(parsed.x, parsed.y, active)
    _check_time_budget(started, active)
    result = _assemble_result(
        parsed,
        response_column,
        predictor_columns,
        active,
        splits,
        validation,
        final,
        time.monotonic() - started,
    )
    result["kernel_selection"] = {
        "mode": "single",
        "criterion": None,
        "candidate_presets": [active.kernel_preset],
        "selected_preset": active.kernel_preset,
        "retain_candidate_details": False,
        "selection_is_external_validation": False,
        "optimizer_starts": optimizer_start_count(active, len(splits)),
        "tie_break_policy": None,
    }
    result["kernel_candidates"] = []
    _check_time_budget(started, active)
    return result


def _cross_validate(
    parsed: _ParsedRows,
    active: GaussianProcessOptions,
    splits: list[tuple[IntArray, IntArray]],
    started: float,
    *,
    preset_index: int | None = None,
) -> _ValidationResult:
    cv_mean: FloatArray | None = None
    cv_latent_std: FloatArray | None = None
    cv_predictive_std: FloatArray | None = None
    converged_folds = 0
    if splits:
        cv_mean = np.full(parsed.y.shape, np.nan, dtype=np.float64)
        cv_latent_std = np.full(parsed.y.shape, np.nan, dtype=np.float64)
        cv_predictive_std = np.full(parsed.y.shape, np.nan, dtype=np.float64)
        cv_options = replace(active, optimizer_restarts=active.cv_optimizer_restarts)
        with threadpool_limits(limits=1):
            for fold_index, (training, validation_indices) in enumerate(splits):
                _check_time_budget(started, active)
                if preset_index is not None:
                    cv_options = replace(
                        cv_options,
                        random_seed=(active.random_seed + preset_index * 104729 + fold_index * 1009)
                        % (2**32 - 1),
                    )
                fit = _fit_model(parsed.x[training], parsed.y[training], cv_options)
                predicted = predict_from_gaussian_process_state(
                    fit.state,
                    parsed.x[validation_indices],
                )
                cv_mean[validation_indices] = predicted["mean"]
                cv_latent_std[validation_indices] = predicted["latent_standard_deviation"]
                cv_predictive_std[validation_indices] = predicted["predictive_standard_deviation"]
                converged_folds += int(fit.state.converged)
        if not (
            np.all(np.isfinite(cv_mean))
            and np.all(np.isfinite(cv_latent_std))
            and np.all(np.isfinite(cv_predictive_std))
        ):
            raise GaussianProcessRegressionError("gp_cross_validation_failed")

    return _ValidationResult(
        cv_mean, cv_latent_std, cv_predictive_std, converged_folds, len(splits)
    )


def _assemble_result(
    parsed: _ParsedRows,
    response_column: GaussianProcessColumn,
    predictor_columns: Sequence[GaussianProcessColumn],
    active: GaussianProcessOptions,
    splits: list[tuple[IntArray, IntArray]],
    validation: _ValidationResult,
    final: _FitResult,
    elapsed: float,
    *,
    include_projections: bool = True,
) -> dict[str, Any]:
    cv_mean, cv_predictive_std = validation.mean, validation.predictive_std
    cv_converged = validation.converged_folds == validation.fold_count
    training_metrics = _point_metrics(parsed.y, final.fitted)
    validation_metrics = _validation_metrics(parsed.y, cv_mean, cv_predictive_std)
    plot_indices = _evenly_spaced_indices(parsed.y.size, active.plot_point_limit)
    warnings_list = _warning_codes(
        parsed=parsed,
        state=final.state,
        noise_mode=active.noise_mode,
        training_r_squared=training_metrics["r_squared"],
        validation=validation_metrics,
        cv_converged=cv_converged,
    )
    profiles = (
        _conditional_profiles(
            final.state,
            parsed.x,
            predictor_columns,
            points=active.profile_points,
        )
        if include_projections
        else []
    )
    surface = (
        _two_predictor_surface(
            final.state,
            parsed.x,
            predictor_columns,
            grid_size=active.surface_grid_size,
        )
        if include_projections
        else None
    )
    fitted_parameters = _fitted_parameter_rows(
        final.state,
        predictor_columns,
        noise_mode=active.noise_mode,
    )
    return {
        "schema_version": 2,
        "summary_type": "gaussian_process_regression",
        "method": {
            "name": "Gaussian Process Regression",
            "engine": "sklearn.gaussian_process.GaussianProcessRegressor",
            "engine_version": importlib.metadata.version("scikit-learn"),
            "kernel_preset": active.kernel_preset,
            "noise_mode": active.noise_mode,
            "standardize_predictors": active.standardize_predictors,
            "normalize_response": active.normalize_response,
            "jitter": active.jitter,
            "optimizer_restarts": active.optimizer_restarts,
            "cv_optimizer_restarts": active.cv_optimizer_restarts,
            "random_seed": active.random_seed,
            "validation_method": active.validation_method,
            "cv_folds": len(splits),
            "cv_shuffle": active.cv_shuffle if active.validation_method == "k_fold" else False,
            "missing_policy": "complete_case",
            "execution_mode": "bounded_inline",
            "elapsed_seconds": elapsed,
        },
        "response": _column_payload(response_column),
        "predictors": [_column_payload(column) for column in predictor_columns],
        "sample": {
            "n_total": parsed.n_total,
            "n_used": int(parsed.y.size),
            "n_excluded": parsed.n_excluded_missing + parsed.n_excluded_non_numeric,
            "n_excluded_missing": parsed.n_excluded_missing,
            "n_excluded_non_numeric": parsed.n_excluded_non_numeric,
            "predictor_count": len(predictor_columns),
        },
        "model_summary": {
            "training_r_squared": training_metrics["r_squared"],
            "training_rmse": training_metrics["rmse"],
            "training_mae": training_metrics["mae"],
            "predicted_r_squared": validation_metrics["predicted_r_squared"],
            "press": validation_metrics["press"],
            "cv_rmse": validation_metrics["rmse"],
            "cv_mae": validation_metrics["mae"],
            "negative_log_predictive_density": validation_metrics["nlpd"],
            "interval_coverage_95": validation_metrics["interval_coverage_95"],
            "mean_predictive_interval_width": validation_metrics["mean_interval_width"],
            "log_marginal_likelihood": final.state.log_marginal_likelihood,
            "fitted_noise_standard_deviation": sqrt(final.state.observation_noise_variance_scaled)
            * final.state.y_scale,
        },
        "kernel": {
            "preset": active.kernel_preset,
            "fitted_kernel": final.state.fitted_kernel_text,
            "signal_kernel": final.state.signal_kernel_payload,
            "observation_noise_variance": (
                final.state.observation_noise_variance_scaled * final.state.y_scale**2
            ),
            "observation_noise_standard_deviation": (
                sqrt(final.state.observation_noise_variance_scaled) * final.state.y_scale
            ),
            "log_marginal_likelihood": final.state.log_marginal_likelihood,
            "parameters": fitted_parameters,
            "converged": final.state.converged and cv_converged,
        },
        "diagnostics": {
            "point_limit": active.plot_point_limit,
            "point_count_total": int(parsed.y.size),
            "truncated": len(plot_indices) < parsed.y.size,
            "points": [
                _diagnostic_point(
                    parsed=parsed,
                    index=index,
                    fitted=final.fitted,
                    latent_std=final.latent_standard_deviation,
                    predictive_std=final.predictive_standard_deviation,
                    cv_mean=cv_mean,
                    cv_predictive_std=cv_predictive_std,
                )
                for index in plot_indices
            ],
        },
        "conditional_profiles": profiles,
        "two_predictor_surface": surface,
        "training_ranges": [
            {
                "column_id": column.column_id,
                "display_name": column.display_name,
                "minimum": float(np.min(parsed.x[:, index])),
                "maximum": float(np.max(parsed.x[:, index])),
                "median": float(np.median(parsed.x[:, index])),
            }
            for index, column in enumerate(predictor_columns)
        ],
        **(
            {"prediction_basis": _prediction_basis(final.state, active)}
            if include_projections
            else {}
        ),
        "warnings": warnings_list,
    }


def predict_from_gaussian_process_state(
    state: GaussianProcessFittedState,
    x: FloatArray,
) -> dict[str, FloatArray]:
    values = np.asarray(x, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] != state.x_mean.size:
        raise GaussianProcessRegressionError("gp_prediction_input_invalid")
    if not np.all(np.isfinite(values)):
        raise GaussianProcessRegressionError("gp_prediction_input_invalid")
    scaled = (values - state.x_mean) / state.x_scale
    cross_covariance = np.asarray(
        state.signal_kernel(scaled, state.x_train_scaled),
        dtype=np.float64,
    )
    normalized_mean = cross_covariance @ state.dual_coefficients
    solved = solve_triangular(
        state.cholesky,
        cross_covariance.T,
        lower=True,
        check_finite=False,
    )
    prior_variance = np.asarray(state.signal_kernel.diag(scaled), dtype=np.float64)
    latent_variance = np.maximum(prior_variance - np.sum(solved**2, axis=0), 0.0)
    predictive_variance = latent_variance + state.observation_noise_variance_scaled
    mean = normalized_mean * state.y_scale + state.y_mean
    latent_std = np.sqrt(latent_variance) * abs(state.y_scale)
    predictive_std = np.sqrt(np.maximum(predictive_variance, 0.0)) * abs(state.y_scale)
    if not (
        np.all(np.isfinite(mean))
        and np.all(np.isfinite(latent_std))
        and np.all(np.isfinite(predictive_std))
    ):
        raise GaussianProcessRegressionError("gp_prediction_failed")
    return {
        "mean": np.asarray(mean, dtype=np.float64),
        "latent_standard_deviation": np.asarray(latent_std, dtype=np.float64),
        "predictive_standard_deviation": np.asarray(predictive_std, dtype=np.float64),
    }


def build_gaussian_process_state(
    *,
    x_train_scaled: FloatArray,
    cholesky: FloatArray,
    dual_coefficients: FloatArray,
    x_mean: FloatArray,
    x_scale: FloatArray,
    y_mean: float,
    y_scale: float,
    predictor_medians: FloatArray,
    signal_kernel_payload: dict[str, object],
    observation_noise_variance_scaled: float,
    fitted_kernel_text: str = "restored",
    log_marginal_likelihood: float = 0.0,
) -> GaussianProcessFittedState:
    signal_kernel = _kernel_from_payload(signal_kernel_payload)
    return GaussianProcessFittedState(
        x_train_scaled=np.asarray(x_train_scaled, dtype=np.float64),
        cholesky=np.asarray(cholesky, dtype=np.float64),
        dual_coefficients=np.asarray(dual_coefficients, dtype=np.float64),
        x_mean=np.asarray(x_mean, dtype=np.float64),
        x_scale=np.asarray(x_scale, dtype=np.float64),
        y_mean=float(y_mean),
        y_scale=float(y_scale),
        predictor_medians=np.asarray(predictor_medians, dtype=np.float64),
        signal_kernel=signal_kernel,
        signal_kernel_payload=signal_kernel_payload,
        observation_noise_variance_scaled=float(observation_noise_variance_scaled),
        fitted_kernel_text=fitted_kernel_text,
        log_marginal_likelihood=float(log_marginal_likelihood),
        converged=True,
    )


def _fit_model(x: FloatArray, y: FloatArray, options: GaussianProcessOptions) -> _FitResult:
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]
    from sklearn.gaussian_process import GaussianProcessRegressor  # type: ignore[import-untyped]

    x_mean = np.mean(x, axis=0) if options.standardize_predictors else np.zeros(x.shape[1])
    x_scale = np.std(x, axis=0, ddof=1) if options.standardize_predictors else np.ones(x.shape[1])
    if np.any(~np.isfinite(x_scale)) or np.any(x_scale <= 0.0):
        raise GaussianProcessRegressionError("gp_constant_predictor")
    y_mean = float(np.mean(y)) if options.normalize_response else 0.0
    y_scale = float(np.std(y, ddof=1)) if options.normalize_response else 1.0
    if not isfinite(y_scale) or y_scale <= 0.0:
        raise GaussianProcessRegressionError("gp_constant_response")
    scaled_x = (x - x_mean) / x_scale
    scaled_y = (y - y_mean) / y_scale
    signal_kernel = _build_signal_kernel(options.kernel_preset, x.shape[1])
    kernel: Any = signal_kernel
    alpha = options.jitter
    fixed_noise_scaled = 0.0
    if options.noise_mode == "estimate":
        from sklearn.gaussian_process.kernels import WhiteKernel  # type: ignore[import-untyped]

        kernel = kernel + WhiteKernel(
            noise_level=1e-2,
            noise_level_bounds=(1e-8, 1e1),
        )
    elif options.noise_mode == "fixed":
        if options.fixed_noise_standard_deviation is None:
            raise GaussianProcessRegressionError("gp_noise_value_invalid")
        fixed_noise_scaled = (options.fixed_noise_standard_deviation / y_scale) ** 2
        alpha += fixed_noise_scaled
    started = time.monotonic()
    model = GaussianProcessRegressor(
        kernel=kernel,
        alpha=alpha,
        optimizer=_bounded_optimizer(options.deadline_monotonic),
        n_restarts_optimizer=options.optimizer_restarts,
        normalize_y=False,
        copy_X_train=True,
        random_state=options.random_seed,
    )
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(scaled_x, scaled_y)
    except GaussianProcessRegressionError:
        raise
    except np.linalg.LinAlgError as exc:
        raise GaussianProcessRegressionError("gp_covariance_not_positive_definite") from exc
    except (FloatingPointError, ValueError) as exc:
        raise GaussianProcessRegressionError("gp_fit_failed") from exc
    convergence_failures = [
        item
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
        and (
            "failed to converge" in str(item.message).lower()
            or "abnormal" in str(item.message).lower()
        )
    ]
    converged = not convergence_failures
    fitted_signal, estimated_noise = _split_fitted_kernel(
        model.kernel_, options.noise_mode, fixed_noise_scaled
    )
    signal_payload = _kernel_payload(fitted_signal, options.kernel_preset)
    state = GaussianProcessFittedState(
        x_train_scaled=np.asarray(model.X_train_, dtype=np.float64),
        cholesky=np.asarray(model.L_, dtype=np.float64),
        dual_coefficients=np.asarray(model.alpha_, dtype=np.float64).reshape(-1),
        x_mean=np.asarray(x_mean, dtype=np.float64),
        x_scale=np.asarray(x_scale, dtype=np.float64),
        y_mean=y_mean,
        y_scale=y_scale,
        predictor_medians=np.asarray(np.median(x, axis=0), dtype=np.float64),
        signal_kernel=fitted_signal,
        signal_kernel_payload=signal_payload,
        observation_noise_variance_scaled=estimated_noise,
        fitted_kernel_text=str(model.kernel_),
        log_marginal_likelihood=float(model.log_marginal_likelihood_value_),
        converged=converged,
    )
    predicted = predict_from_gaussian_process_state(state, x)
    return _FitResult(
        state=state,
        fitted=predicted["mean"],
        latent_standard_deviation=predicted["latent_standard_deviation"],
        predictive_standard_deviation=predicted["predictive_standard_deviation"],
        elapsed_seconds=time.monotonic() - started,
    )


def _bounded_optimizer(deadline: float | None) -> Any:
    from scipy.optimize import minimize  # type: ignore[import-untyped]
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]

    def optimize(objective: Any, theta: FloatArray, bounds: FloatArray) -> tuple[FloatArray, float]:
        if not np.all(np.isfinite(bounds)):
            raise GaussianProcessRegressionError("gp_kernel_bounds_invalid")

        def checked(parameters: FloatArray) -> Any:
            if deadline is not None and time.monotonic() >= deadline:
                raise GaussianProcessRegressionError("gp_time_budget_exhausted")
            return objective(parameters)

        result = minimize(checked, theta, method="L-BFGS-B", jac=True, bounds=bounds)
        if result.status != 0:
            warnings.warn(
                "Gaussian Process optimizer failed to converge.", ConvergenceWarning, stacklevel=2
            )
        return np.asarray(result.x, dtype=np.float64), float(result.fun)

    return optimize


def _build_signal_kernel(preset: KernelPreset, predictor_count: int) -> Any:
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        RBF,
        ConstantKernel,
        Matern,
        RationalQuadratic,
    )

    amplitude = ConstantKernel(1.0, (1e-3, 1e3))
    length_scale = np.ones(predictor_count, dtype=np.float64)
    if preset == "matern_5_2_ard":
        base = Matern(length_scale=length_scale, length_scale_bounds=(1e-2, 1e2), nu=2.5)
    elif preset == "matern_3_2_ard":
        base = Matern(length_scale=length_scale, length_scale_bounds=(1e-2, 1e2), nu=1.5)
    elif preset == "rbf_ard":
        base = RBF(length_scale=length_scale, length_scale_bounds=(1e-2, 1e2))
    elif preset == "rational_quadratic":
        base = RationalQuadratic(
            length_scale=1.0,
            alpha=1.0,
            length_scale_bounds=(1e-2, 1e2),
            alpha_bounds=(1e-2, 1e2),
        )
    else:
        raise GaussianProcessRegressionError("gp_kernel_policy_invalid")
    return amplitude * base


def _split_fitted_kernel(
    kernel: Any,
    noise_mode: NoiseMode,
    fixed_noise_scaled: float,
) -> tuple[Any, float]:
    if noise_mode == "estimate":
        signal = getattr(kernel, "k1", None)
        noise = getattr(kernel, "k2", None)
        noise_level = getattr(noise, "noise_level", None)
        if signal is None or not isinstance(noise_level, int | float):
            raise GaussianProcessRegressionError("gp_fit_failed")
        return signal, float(noise_level)
    return kernel, fixed_noise_scaled


def _kernel_payload(kernel: Any, preset: KernelPreset) -> dict[str, object]:
    amplitude_kernel = getattr(kernel, "k1", None)
    base_kernel = getattr(kernel, "k2", None)
    amplitude = getattr(amplitude_kernel, "constant_value", None)
    length_scale = getattr(base_kernel, "length_scale", None)
    if not isinstance(amplitude, int | float) or length_scale is None:
        raise GaussianProcessRegressionError("gp_fit_failed")
    values = np.asarray(length_scale, dtype=np.float64).reshape(-1)
    payload: dict[str, object] = {
        "preset": preset,
        "amplitude": float(amplitude),
        "length_scales": [float(value) for value in values],
    }
    if preset == "rational_quadratic":
        alpha = getattr(base_kernel, "alpha", None)
        if not isinstance(alpha, int | float):
            raise GaussianProcessRegressionError("gp_fit_failed")
        payload["rational_quadratic_alpha"] = float(alpha)
    return payload


def _kernel_from_payload(payload: dict[str, object]) -> Any:
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        RBF,
        ConstantKernel,
        Matern,
        RationalQuadratic,
    )

    preset = payload.get("preset")
    amplitude = _finite_float(payload.get("amplitude"), "gp_model_artifact_invalid")
    length_scales_value = payload.get("length_scales")
    if not isinstance(length_scales_value, list) or not length_scales_value:
        raise GaussianProcessRegressionError("gp_model_artifact_invalid")
    length_scales = np.asarray(
        [_finite_float(value, "gp_model_artifact_invalid") for value in length_scales_value],
        dtype=np.float64,
    )
    constant = ConstantKernel(amplitude, constant_value_bounds="fixed")
    if preset == "matern_5_2_ard":
        base = Matern(length_scale=length_scales, length_scale_bounds="fixed", nu=2.5)
    elif preset == "matern_3_2_ard":
        base = Matern(length_scale=length_scales, length_scale_bounds="fixed", nu=1.5)
    elif preset == "rbf_ard":
        base = RBF(length_scale=length_scales, length_scale_bounds="fixed")
    elif preset == "rational_quadratic":
        alpha = _finite_float(payload.get("rational_quadratic_alpha"), "gp_model_artifact_invalid")
        base = RationalQuadratic(
            length_scale=float(length_scales[0]),
            alpha=alpha,
            length_scale_bounds="fixed",
            alpha_bounds="fixed",
        )
    else:
        raise GaussianProcessRegressionError("gp_model_artifact_invalid")
    return constant * base


def _prediction_basis(
    state: GaussianProcessFittedState,
    options: GaussianProcessOptions,
) -> dict[str, object]:
    return {
        "artifact_arrays": {
            "x_train_scaled": state.x_train_scaled,
            "cholesky": state.cholesky,
            "dual_coefficients": state.dual_coefficients,
            "x_mean": state.x_mean,
            "x_scale": state.x_scale,
            "predictor_medians": state.predictor_medians,
        },
        "y_mean": state.y_mean,
        "y_scale": state.y_scale,
        "signal_kernel": state.signal_kernel_payload,
        "observation_noise_variance_scaled": state.observation_noise_variance_scaled,
        "noise_mode": options.noise_mode,
        "jitter": options.jitter,
    }


def _validation_splits(
    n_samples: int,
    options: GaussianProcessOptions,
) -> list[tuple[IntArray, IntArray]]:
    from sklearn.model_selection import KFold, LeaveOneOut  # type: ignore[import-untyped]

    if options.validation_method == "none":
        return []
    if options.validation_method == "leave_one_out":
        if n_samples > MAX_GP_LOO_ROWS:
            raise GaussianProcessRegressionError("gp_leave_one_out_limit")
        splitter = LeaveOneOut()
    elif options.validation_method == "k_fold":
        if options.cv_folds < 2 or options.cv_folds > 10 or options.cv_folds >= n_samples:
            raise GaussianProcessRegressionError("gp_cv_fold_invalid")
        splitter = KFold(
            n_splits=options.cv_folds,
            shuffle=options.cv_shuffle,
            random_state=options.random_seed if options.cv_shuffle else None,
        )
    else:
        raise GaussianProcessRegressionError("gp_cv_fold_invalid")
    indices = np.arange(n_samples)
    return [
        (
            np.asarray(training, dtype=np.int64),
            np.asarray(validation, dtype=np.int64),
        )
        for training, validation in splitter.split(indices)
    ]


def _point_metrics(observed: FloatArray, predicted: FloatArray) -> dict[str, float]:
    residual = observed - predicted
    sse = float(np.sum(residual**2))
    tss = float(np.sum((observed - np.mean(observed)) ** 2))
    return {
        "r_squared": 1.0 - sse / tss,
        "rmse": sqrt(sse / observed.size),
        "mae": float(np.mean(np.abs(residual))),
    }


def _validation_metrics(
    observed: FloatArray,
    predicted: FloatArray | None,
    predictive_std: FloatArray | None,
) -> dict[str, float | None]:
    if predicted is None or predictive_std is None:
        return {
            "predicted_r_squared": None,
            "press": None,
            "rmse": None,
            "mae": None,
            "nlpd": None,
            "interval_coverage_95": None,
            "mean_interval_width": None,
        }
    residual = observed - predicted
    press = float(np.sum(residual**2))
    tss = float(np.sum((observed - np.mean(observed)) ** 2))
    variance = np.maximum(predictive_std**2, np.finfo(np.float64).tiny)
    nlpd = float(np.mean(0.5 * (np.log(2.0 * pi * variance) + residual**2 / variance)))
    half_width = NORMAL_975 * predictive_std
    coverage = float(np.mean(np.abs(residual) <= half_width))
    return {
        "predicted_r_squared": 1.0 - press / tss,
        "press": press,
        "rmse": sqrt(press / observed.size),
        "mae": float(np.mean(np.abs(residual))),
        "nlpd": nlpd,
        "interval_coverage_95": coverage,
        "mean_interval_width": float(np.mean(2.0 * half_width)),
    }


def _diagnostic_point(
    *,
    parsed: _ParsedRows,
    index: int,
    fitted: FloatArray,
    latent_std: FloatArray,
    predictive_std: FloatArray,
    cv_mean: FloatArray | None,
    cv_predictive_std: FloatArray | None,
) -> dict[str, object]:
    observed = float(parsed.y[index])
    fit = float(fitted[index])
    predictive = float(predictive_std[index])
    result: dict[str, object] = {
        "row_index": parsed.row_indices[index],
        "observed": observed,
        "fitted": fit,
        "residual": observed - fit,
        "latent_standard_deviation": float(latent_std[index]),
        "predictive_standard_deviation": predictive,
        "predictive_interval_95": _interval(fit, predictive),
        "cross_validated_fitted": None,
        "cross_validated_residual": None,
        "cross_validated_predictive_standard_deviation": None,
        "standardized_predictive_residual": None,
    }
    if cv_mean is not None and cv_predictive_std is not None:
        cv_fit = float(cv_mean[index])
        cv_std = float(cv_predictive_std[index])
        result.update(
            {
                "cross_validated_fitted": cv_fit,
                "cross_validated_residual": observed - cv_fit,
                "cross_validated_predictive_standard_deviation": cv_std,
                "standardized_predictive_residual": (
                    (observed - cv_fit) / cv_std if cv_std > 1e-15 else None
                ),
            }
        )
    return result


def _conditional_profiles(
    state: GaussianProcessFittedState,
    x: FloatArray,
    predictors: Sequence[GaussianProcessColumn],
    *,
    points: int,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for index, predictor in enumerate(predictors):
        values = np.linspace(np.min(x[:, index]), np.max(x[:, index]), points)
        grid = np.tile(state.predictor_medians, (points, 1))
        grid[:, index] = values
        prediction = predict_from_gaussian_process_state(state, grid)
        output.append(
            {
                "column_id": predictor.column_id,
                "display_name": predictor.display_name,
                "fixed_values": [float(value) for value in state.predictor_medians],
                "points": [
                    _prediction_point(float(value), prediction, row)
                    for row, value in enumerate(values)
                ],
            }
        )
    return output


def _two_predictor_surface(
    state: GaussianProcessFittedState,
    x: FloatArray,
    predictors: Sequence[GaussianProcessColumn],
    *,
    grid_size: int,
) -> dict[str, object] | None:
    if len(predictors) < 2:
        return None
    x_values = np.linspace(np.min(x[:, 0]), np.max(x[:, 0]), grid_size)
    y_values = np.linspace(np.min(x[:, 1]), np.max(x[:, 1]), grid_size)
    grid = np.tile(state.predictor_medians, (grid_size * grid_size, 1))
    row = 0
    for y_value in y_values:
        for x_value in x_values:
            grid[row, 0] = x_value
            grid[row, 1] = y_value
            row += 1
    prediction = predict_from_gaussian_process_state(state, grid)
    return {
        "x_column_id": predictors[0].column_id,
        "x_display_name": predictors[0].display_name,
        "y_column_id": predictors[1].column_id,
        "y_display_name": predictors[1].display_name,
        "grid_size": grid_size,
        "fixed_values": [float(value) for value in state.predictor_medians],
        "points": [
            {
                "x": float(grid[index, 0]),
                "y": float(grid[index, 1]),
                "predicted_mean": float(prediction["mean"][index]),
                "predictive_standard_deviation": float(
                    prediction["predictive_standard_deviation"][index]
                ),
            }
            for index in range(grid.shape[0])
        ],
    }


def _prediction_point(
    value: float, prediction: dict[str, FloatArray], index: int
) -> dict[str, object]:
    mean = float(prediction["mean"][index])
    latent = float(prediction["latent_standard_deviation"][index])
    predictive = float(prediction["predictive_standard_deviation"][index])
    return {
        "value": value,
        "predicted_mean": mean,
        "latent_standard_deviation": latent,
        "latent_interval_95": _interval(mean, latent),
        "predictive_standard_deviation": predictive,
        "predictive_interval_95": _interval(mean, predictive),
    }


def _fitted_parameter_rows(
    state: GaussianProcessFittedState,
    predictors: Sequence[GaussianProcessColumn],
    *,
    noise_mode: NoiseMode,
) -> list[dict[str, object]]:
    payload = state.signal_kernel_payload
    rows = [
        _parameter_row(
            "signal_amplitude", None, float(cast(float, payload["amplitude"])), 1e-3, 1e3
        )
    ]
    length_scales = cast(list[float], payload["length_scales"])
    if len(length_scales) == 1 and len(predictors) > 1:
        rows.append(_parameter_row("shared_length_scale", None, length_scales[0], 1e-2, 1e2))
    else:
        rows.extend(
            _parameter_row("length_scale", predictor.column_id, value, 1e-2, 1e2)
            for predictor, value in zip(predictors, length_scales, strict=True)
        )
    if "rational_quadratic_alpha" in payload:
        rows.append(
            _parameter_row(
                "rational_quadratic_alpha",
                None,
                float(cast(float, payload["rational_quadratic_alpha"])),
                1e-2,
                1e2,
            )
        )
    if noise_mode == "estimate":
        rows.append(
            _parameter_row(
                "observation_noise_variance_scaled",
                None,
                state.observation_noise_variance_scaled,
                1e-8,
                1e1,
            )
        )
    else:
        rows.append(
            {
                "parameter": "observation_noise_variance_scaled",
                "column_id": None,
                "estimate": state.observation_noise_variance_scaled,
                "lower_bound": 0.0,
                "upper_bound": None,
                "near_bound": False,
            }
        )
    return rows


def _parameter_row(
    name: str,
    column_id: str | None,
    estimate: float,
    lower: float,
    upper: float,
) -> dict[str, object]:
    return {
        "parameter": name,
        "column_id": column_id,
        "estimate": estimate,
        "lower_bound": lower,
        "upper_bound": upper,
        "near_bound": _near_bound(estimate, lower, upper),
    }


def _warning_codes(
    *,
    parsed: _ParsedRows,
    state: GaussianProcessFittedState,
    noise_mode: NoiseMode,
    training_r_squared: float | None,
    validation: dict[str, float | None],
    cv_converged: bool,
) -> list[str]:
    codes = ["gp_predictive_not_causal", "gp_uncertainty_conditional_on_kernel"]
    if parsed.n_excluded_missing + parsed.n_excluded_non_numeric > 0:
        codes.append("missing_values_excluded")
    if not state.converged or not cv_converged:
        codes.append("gp_not_converged")
    payload = state.signal_kernel_payload
    amplitude = float(cast(float, payload["amplitude"]))
    length_scales = [float(value) for value in cast(list[float], payload["length_scales"])]
    if _near_bound(amplitude, 1e-3, 1e3):
        codes.append("gp_amplitude_near_bound")
    if any(_near_bound(value, 1e-2, 1e2) for value in length_scales):
        codes.append("gp_length_scale_near_bound")
    if noise_mode == "estimate" and _near_bound(
        state.observation_noise_variance_scaled,
        1e-8,
        1e1,
    ):
        codes.append("gp_noise_level_near_bound")
    predicted_r = validation["predicted_r_squared"]
    if predicted_r is not None and predicted_r < 0.0:
        codes.append("gp_negative_cv_r_squared")
    coverage = validation["interval_coverage_95"]
    if coverage is not None and coverage < 0.8:
        codes.append("gp_interval_undercoverage")
    if (
        training_r_squared is not None
        and predicted_r is not None
        and training_r_squared - predicted_r > 0.25
    ):
        codes.append("gp_training_cv_gap")
    return sorted(set(codes))


def _validate_columns(
    response: GaussianProcessColumn,
    predictors: Sequence[GaussianProcessColumn],
) -> None:
    if not predictors:
        raise GaussianProcessRegressionError("gp_predictor_required")
    if len(predictors) > MAX_GP_PREDICTORS:
        raise GaussianProcessRegressionError("gp_predictor_count_limit")
    ids = [column.column_id for column in predictors]
    if len(set(ids)) != len(ids):
        raise GaussianProcessRegressionError("gp_duplicate_predictor")
    if response.column_id in ids:
        raise GaussianProcessRegressionError("gp_response_in_predictors")


def _validate_options(options: GaussianProcessOptions) -> None:
    if options.kernel_preset not in {
        "matern_5_2_ard",
        "matern_3_2_ard",
        "rbf_ard",
        "rational_quadratic",
    }:
        raise GaussianProcessRegressionError("gp_kernel_policy_invalid")
    if options.noise_mode not in {"estimate", "fixed", "near_noiseless"}:
        raise GaussianProcessRegressionError("gp_noise_mode_invalid")
    if options.noise_mode == "fixed" and (
        options.fixed_noise_standard_deviation is None
        or not isfinite(options.fixed_noise_standard_deviation)
        or options.fixed_noise_standard_deviation <= 0.0
    ):
        raise GaussianProcessRegressionError("gp_noise_value_invalid")
    if not 1e-12 <= options.jitter <= 1e-3:
        raise GaussianProcessRegressionError("gp_jitter_invalid")
    if not 0 <= options.optimizer_restarts <= 10 or not 0 <= options.cv_optimizer_restarts <= 5:
        raise GaussianProcessRegressionError("gp_kernel_policy_invalid")
    if options.kernel_selection_mode not in {"single", "compare"}:
        raise GaussianProcessRegressionError("gp_kernel_policy_invalid")
    if options.kernel_selection_mode == "compare":
        if not 2 <= len(options.kernel_candidates) <= 4 or len(
            set(options.kernel_candidates)
        ) != len(options.kernel_candidates):
            raise GaussianProcessRegressionError("gp_kernel_candidates_invalid")
        if any(
            preset not in {"matern_5_2_ard", "matern_3_2_ard", "rbf_ard", "rational_quadratic"}
            for preset in options.kernel_candidates
        ):
            raise GaussianProcessRegressionError("gp_kernel_candidates_invalid")
        if options.validation_method == "none":
            raise GaussianProcessRegressionError("gp_kernel_comparison_requires_validation")
        if options.selection_criterion not in {"cv_nlpd", "cv_rmse", "cv_mae"}:
            raise GaussianProcessRegressionError("gp_kernel_criterion_invalid")
    if not 100 <= options.plot_point_limit <= 2000:
        raise GaussianProcessRegressionError("gp_kernel_policy_invalid")
    if not 10 <= options.profile_points <= 80 or not 10 <= options.surface_grid_size <= 40:
        raise GaussianProcessRegressionError("gp_kernel_policy_invalid")
    if not isfinite(options.time_budget_seconds) or not 5.0 <= options.time_budget_seconds <= 600.0:
        raise GaussianProcessRegressionError("gp_time_budget_exhausted")


def _validate_sample(
    parsed: _ParsedRows,
    predictor_count: int,
    options: GaussianProcessOptions,
) -> None:
    if parsed.y.size < max(5, predictor_count + 2):
        raise GaussianProcessRegressionError("gp_usable_rows_too_few")
    if parsed.y.size > MAX_GP_USABLE_ROWS:
        raise GaussianProcessRegressionError("gp_usable_rows_limit")
    if not np.all(np.isfinite(parsed.x)) or not np.all(np.isfinite(parsed.y)):
        raise GaussianProcessRegressionError("gp_fit_failed")
    if float(np.var(parsed.y, ddof=1)) <= 0.0:
        raise GaussianProcessRegressionError("gp_constant_response")
    if np.any(np.var(parsed.x, axis=0, ddof=1) <= 0.0):
        raise GaussianProcessRegressionError("gp_constant_predictor")
    if options.validation_method == "leave_one_out" and parsed.y.size > MAX_GP_LOO_ROWS:
        raise GaussianProcessRegressionError("gp_leave_one_out_limit")


def _parse_rows(
    rows: Iterable[Sequence[str | None]],
    response: GaussianProcessColumn,
    predictors: Sequence[GaussianProcessColumn],
    *,
    decimal: str,
    thousands: str | None,
) -> _ParsedRows:
    x_rows: list[list[float]] = []
    y_values: list[float] = []
    row_indices: list[int] = []
    n_total = 0
    n_missing = 0
    n_non_numeric = 0
    for row_index, row in enumerate(rows):
        n_total += 1
        raw = [_row_value(row, column.column_index) for column in (response, *predictors)]
        if any(value is None or not str(value).strip() for value in raw):
            n_missing += 1
            continue
        parsed = [_parse_number(value, decimal, thousands) for value in raw]
        if any(value is None for value in parsed):
            n_non_numeric += 1
            continue
        finite = [cast(float, value) for value in parsed]
        y_values.append(finite[0])
        x_rows.append(finite[1:])
        row_indices.append(row_index)
    return _ParsedRows(
        x=np.asarray(x_rows, dtype=np.float64),
        y=np.asarray(y_values, dtype=np.float64),
        row_indices=row_indices,
        n_total=n_total,
        n_excluded_missing=n_missing,
        n_excluded_non_numeric=n_non_numeric,
    )


def _parse_number(value: str | None, decimal: str, thousands: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if thousands:
        text = text.replace(thousands, "")
    if decimal != ".":
        text = text.replace(decimal, ".")
    try:
        number = float(Decimal(text))
    except (InvalidOperation, ValueError):
        return None
    return number if isfinite(number) else None


def _row_value(row: Sequence[str | None], index: int) -> str | None:
    return row[index] if 0 <= index < len(row) else None


def _column_payload(column: GaussianProcessColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _interval(mean: float, standard_deviation: float) -> dict[str, float]:
    half_width = NORMAL_975 * standard_deviation
    return {"lower": mean - half_width, "upper": mean + half_width}


def _evenly_spaced_indices(count: int, limit: int) -> list[int]:
    if count <= limit:
        return list(range(count))
    return sorted(set(int(value) for value in np.linspace(0, count - 1, limit)))


def _near_bound(value: float, lower: float, upper: float) -> bool:
    log_value = log(value)
    log_lower = log(lower)
    log_upper = log(upper)
    span = log_upper - log_lower
    return min(log_value - log_lower, log_upper - log_value) <= BOUND_WARNING_FRACTION * span


def _finite_float(value: object, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not isfinite(float(value)):
        raise GaussianProcessRegressionError(code)
    return float(value)


def _check_time_budget(started: float, options: GaussianProcessOptions) -> None:
    if time.monotonic() - started > options.time_budget_seconds:
        raise GaussianProcessRegressionError("gp_time_budget_exhausted")
