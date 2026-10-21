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

from app.statistics.gp_preprocessing import (
    GpPredictorSpec,
    GpPreprocessingError,
    GpPreprocessor,
    fit_gp_preprocessor,
    transform_gp_rows,
    validate_encoded_gp_matrix,
)
from app.statistics.gp_resource_budget import GpResourceError, estimate_gp_resources
from app.statistics.gp_time_features import LagObservation, build_lag_features
from app.statistics.gp_validation import (
    GpValidationError,
    GpValidationPlan,
    build_validation_plan,
    parse_time_value,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
KernelPreset = Literal[
    "matern_5_2_ard",
    "matern_3_2_ard",
    "rbf_ard",
    "rational_quadratic",
]
NoiseMode = Literal["estimate", "fixed", "near_noiseless"]
ValidationMethod = Literal["k_fold", "group_k_fold", "time_series_split", "leave_one_out", "none"]

MAX_GP_PREDICTORS = 12
MAX_GP_USABLE_ROWS = 500
MAX_GP_LAG_PREPARATION_BYTES = 32 * 1024**2
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
    length_scale_lower: float = 0.01
    length_scale_initial: float = 1.0
    length_scale_upper: float = 100.0
    length_scale_coordinate_system: Literal["standardized", "original"] | None = None
    optimizer: Literal["l_bfgs_b", "bfgs"] = "l_bfgs_b"
    group_column_id: str | None = None
    time_column_id: str | None = None
    time_format: Literal["numeric", "timestamp"] | None = None
    time_unit: str | None = None
    timestamp_timezone: Literal["require_offset", "UTC"] = "require_offset"
    gap_time_blocks: int = 0
    lagged_column_ids: tuple[str, ...] = ()
    lags: tuple[int, ...] = ()
    series_column_id: str | None = None
    resource_profile: Literal["standard_exact", "extended_exact"] = "standard_exact"
    initial_surface_x_column_id: str | None = None
    initial_surface_y_column_id: str | None = None


@dataclass(frozen=True)
class _ParsedRows:
    x: FloatArray
    y: FloatArray
    row_indices: list[int]
    n_total: int
    n_excluded_missing: int
    n_excluded_non_numeric: int
    groups: list[str] | None = None
    times: list[float] | None = None
    lag_source_times: list[list[float]] | None = None
    feature_lineage: dict[str, Any] | None = None
    n_excluded_lag: int = 0
    validation_plan: GpValidationPlan | None = None
    raw_predictor_rows: list[list[float | str]] | None = None
    predictor_specs: tuple[GpPredictorSpec, ...] = ()
    resource_budget: dict[str, object] | None = None


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
    preprocessing: GpPreprocessor | None = None


@dataclass(frozen=True)
class _FitResult:
    state: GaussianProcessFittedState
    fitted: FloatArray
    latent_standard_deviation: FloatArray
    predictive_standard_deviation: FloatArray
    elapsed_seconds: float
    optimizer_runs: list[dict[str, Any]]


@dataclass(frozen=True)
class _ValidationResult:
    mean: FloatArray | None
    latent_std: FloatArray | None
    predictive_std: FloatArray | None
    converged_folds: int
    fold_count: int
    folds: list[dict[str, Any]]
    scored_mask: NDArray[np.bool_] | None = None


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
    metadata_columns: Sequence[GaussianProcessColumn] = (),
) -> dict[str, object]:
    active = options or GaussianProcessOptions()
    _validate_columns(response_column, predictor_columns)
    _validate_options(active)
    predictor_ids = {column.column_id for column in predictor_columns}
    if response_column.column_id in {active.group_column_id, active.time_column_id} or (
        active.group_column_id is not None and active.group_column_id in predictor_ids
    ):
        raise GaussianProcessRegressionError("gp_validation_column_overlap")
    if active.series_column_id is not None and active.series_column_id in {
        response_column.column_id,
        active.time_column_id,
        *predictor_ids,
    }:
        raise GaussianProcessRegressionError("gp_validation_column_overlap")
    try:
        parsed = _parse_rows(
            rows,
            response_column,
            predictor_columns,
            decimal=decimal,
            thousands=thousands,
            options=active,
            metadata_columns=metadata_columns,
        )
        if active.lagged_column_ids:
            predictor_columns = [
                *predictor_columns,
                *_lag_predictor_columns(
                    response_column,
                    predictor_columns,
                    metadata_columns,
                    active,
                ),
            ]
        _validate_sample(parsed, len(predictor_columns), active)
        surface_ids = (active.initial_surface_x_column_id, active.initial_surface_y_column_id)
        numeric_ids = {
            column.column_id
            for column in predictor_columns
            if column.measurement_level != "nominal"
        }
        if any(value is not None for value in surface_ids) and (
            any(value is None or value not in numeric_ids for value in surface_ids)
            or surface_ids[0] == surface_ids[1]
        ):
            raise GaussianProcessRegressionError("gp_surface_axes_invalid")
        plan = build_validation_plan(
            method=active.validation_method,
            row_indices=parsed.row_indices,
            folds=active.cv_folds,
            shuffle=active.cv_shuffle,
            seed=active.random_seed,
            groups=parsed.groups,
            times=parsed.times,
            gap_time_blocks=active.gap_time_blocks,
            lag_source_times=parsed.lag_source_times,
        )
    except (GpValidationError, GpPreprocessingError) as exc:
        raise GaussianProcessRegressionError(exc.code) from exc
    numeric_count = sum(column.measurement_level != "nominal" for column in predictor_columns)
    categorical_count = sum(
        column.measurement_level == "nominal" and len(np.unique(parsed.x[:, i])) > 1
        for i, column in enumerate(predictor_columns)
    )
    presets = (
        active.kernel_candidates
        if active.kernel_selection_mode == "compare"
        else (active.kernel_preset,)
    )
    parameter_counts = [
        (int(_build_signal_kernel(preset, numeric_count, active).n_dims) if numeric_count else 1)
        + categorical_count
        + int(active.noise_mode == "estimate")
        for preset in presets
    ]
    try:
        resource = estimate_gp_resources(
            profile=active.resource_profile,
            n_rows=int(parsed.y.size),
            fold_training_sizes=[len(training) for training, _ in plan.splits],
            kernel_parameter_counts=parameter_counts,
            optimizer_restarts=active.optimizer_restarts,
            cv_optimizer_restarts=active.cv_optimizer_restarts,
            retained_candidate_count=len(presets) - 1 if active.retain_candidate_details else 0,
            prediction_query_count=len(predictor_columns) * active.profile_points
            + (active.surface_grid_size**2 if numeric_count >= 2 else 0),
        )
    except GpResourceError as exc:
        raise GaussianProcessRegressionError(exc.code) from exc
    parsed = replace(parsed, validation_plan=plan, resource_budget=resource.to_payload())
    started = time.monotonic()
    active = replace(active, deadline_monotonic=started + active.time_budget_seconds)
    splits = plan.splits
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
        final = _fit_parsed_model(parsed, active)
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
    fold_records: list[dict[str, Any]] = []
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
                fit = _fit_parsed_model(parsed, cv_options, training)
                predicted = predict_from_gaussian_process_state(
                    fit.state,
                    _prediction_rows(parsed, validation_indices),
                )
                cv_mean[validation_indices] = predicted["mean"]
                cv_latent_std[validation_indices] = predicted["latent_standard_deviation"]
                cv_predictive_std[validation_indices] = predicted["predictive_standard_deviation"]
                converged_folds += int(fit.state.converged)
                fold_records.append(
                    {
                        **(
                            parsed.validation_plan.payload["folds"][fold_index]
                            if parsed.validation_plan is not None
                            else {}
                        ),
                        "fold": fold_index + 1,
                        "training_row_indices": [parsed.row_indices[int(i)] for i in training],
                        "validation_row_indices": [
                            parsed.row_indices[int(i)] for i in validation_indices
                        ],
                        "seed": cv_options.random_seed,
                        "x_mean": fit.state.x_mean.tolist(),
                        "x_scale": fit.state.x_scale.tolist(),
                        "y_mean": fit.state.y_mean,
                        "y_scale": fit.state.y_scale,
                        "optimizer_runs": fit.optimizer_runs,
                        "fit_elapsed_seconds": fit.elapsed_seconds,
                        "converged": fit.state.converged,
                        "preprocessing": fit.state.preprocessing.to_payload()
                        if fit.state.preprocessing is not None
                        else None,
                    }
                )
        scored = (
            parsed.validation_plan.scored_mask
            if parsed.validation_plan is not None
            else np.ones(parsed.y.shape, dtype=np.bool_)
        )
        if not (
            np.all(np.isfinite(cv_mean[scored]))
            and np.all(np.isfinite(cv_latent_std[scored]))
            and np.all(np.isfinite(cv_predictive_std[scored]))
        ):
            raise GaussianProcessRegressionError("gp_cross_validation_failed")

    return _ValidationResult(
        cv_mean,
        cv_latent_std,
        cv_predictive_std,
        converged_folds,
        len(splits),
        fold_records,
        parsed.validation_plan.scored_mask if parsed.validation_plan is not None else None,
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
    validation_metrics = _validation_metrics(
        parsed.y, cv_mean, cv_predictive_std, validation.scored_mask
    )
    plot_indices = _evenly_spaced_indices(parsed.y.size, active.plot_point_limit)
    warnings_list = _warning_codes(
        parsed=parsed,
        state=final.state,
        noise_mode=active.noise_mode,
        training_r_squared=training_metrics["r_squared"],
        validation=validation_metrics,
        cv_converged=cv_converged,
        length_bounds=(active.length_scale_lower, active.length_scale_upper),
    )
    if active.validation_method == "group_k_fold":
        warnings_list.append("gp_group_validation_new_groups")
    if active.validation_method == "time_series_split":
        warnings_list.append("gp_time_validation_partial_coverage")
    if parsed.feature_lineage is not None:
        warnings_list.append("gp_lag_one_step_observed_history")
        if parsed.feature_lineage["irregular_intervals"]:
            warnings_list.append("gp_lag_irregular_observation_intervals")
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
            x_column_id=active.initial_surface_x_column_id,
            y_column_id=active.initial_surface_y_column_id,
        )
        if include_projections
        else None
    )
    fitted_parameters = _fitted_parameter_rows(
        final.state,
        predictor_columns,
        noise_mode=active.noise_mode,
        length_bounds=(active.length_scale_lower, active.length_scale_upper),
    )
    return {
        "schema_version": 4,
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
            "resource_profile": active.resource_profile,
            "elapsed_seconds": elapsed,
            "optimizer": active.optimizer,
            "length_scale": {
                "lower": active.length_scale_lower,
                "initial": active.length_scale_initial,
                "upper": active.length_scale_upper,
                "coordinate_system": "standardized"
                if active.standardize_predictors
                else "original",
                "policy": "common_scalar_applied_to_all_length_scales",
            },
            "scaling_ddof": 1,
            "fixed_noise_standard_deviation": active.fixed_noise_standard_deviation,
            "package_versions": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "scikit-learn")
            },
        },
        "optimization": {
            "final_runs": final.optimizer_runs,
            "cv_folds": validation.folds,
            "final_fit_elapsed_seconds": final.elapsed_seconds,
            "cv_fit_elapsed_seconds": sum(
                float(fold["fit_elapsed_seconds"]) for fold in validation.folds
            ),
            "fit_timing_scope": "model_construction_and_fit_excludes_preprocessing_and_prediction",
        },
        "validation_plan": {
            **(parsed.validation_plan.payload if parsed.validation_plan else {}),
            "group_column_id": active.group_column_id,
            "time_column_id": active.time_column_id,
            "time_format": active.time_format,
            "time_unit": active.time_unit
            if active.time_format == "numeric"
            else "UTC_seconds"
            if active.time_format == "timestamp"
            else None,
            "timestamp_timezone": active.timestamp_timezone
            if active.time_format == "timestamp"
            else None,
        },
        "feature_lineage": parsed.feature_lineage,
        "resource_budget": parsed.resource_budget,
        "preprocessing": final.state.preprocessing.to_payload()
        if final.state.preprocessing is not None
        else None,
        "response": _column_payload(response_column),
        "predictors": [
            {
                **_column_payload(column),
                "kind": "nominal" if column.measurement_level == "nominal" else "numeric",
            }
            for column in predictor_columns
        ],
        "sample": {
            "n_total": parsed.n_total,
            "n_used": int(parsed.y.size),
            "n_excluded": parsed.n_excluded_missing
            + parsed.n_excluded_non_numeric
            + parsed.n_excluded_lag,
            "n_excluded_missing": parsed.n_excluded_missing,
            "n_excluded_non_numeric": parsed.n_excluded_non_numeric,
            "n_excluded_lag": parsed.n_excluded_lag,
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
        "surface_unavailable_reason": "fewer_than_two_numeric_predictors"
        if sum(column.measurement_level != "nominal" for column in predictor_columns) < 2
        else None,
        "training_ranges": _training_range_rows(final.state, parsed.x, predictor_columns),
        **(
            {"prediction_basis": _prediction_basis(final.state, active)}
            if include_projections
            else {}
        ),
        "warnings": warnings_list,
    }


def predict_from_gaussian_process_state(
    state: GaussianProcessFittedState,
    x: Any,
) -> dict[str, FloatArray]:
    try:
        if state.preprocessing is not None:
            scaled = transform_gp_rows(state.preprocessing, x)
        else:
            values = np.asarray(x, dtype=np.float64)
            if values.ndim != 2 or values.shape[1] != state.x_mean.size:
                raise GaussianProcessRegressionError("gp_prediction_input_invalid")
            if not np.all(np.isfinite(values)):
                raise GaussianProcessRegressionError("gp_prediction_input_invalid")
            scaled = (values - state.x_mean) / state.x_scale
    except GpPreprocessingError as exc:
        raise GaussianProcessRegressionError(exc.code) from exc
    # Bound query-by-training temporary arrays; no query-by-query covariance is needed.
    if len(scaled) > 256:
        chunks = [
            _predict_scaled(state, scaled[start : start + 256])
            for start in range(0, len(scaled), 256)
        ]
        return {key: np.concatenate([chunk[key] for chunk in chunks]) for key in chunks[0]}
    return _predict_scaled(state, scaled)


def _predict_scaled(state: GaussianProcessFittedState, scaled: FloatArray) -> dict[str, FloatArray]:
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
    preprocessing_payload: dict[str, Any] | None = None,
) -> GaussianProcessFittedState:
    from app.statistics.gp_mixed_kernels import MixedPredictorKernel

    signal_kernel = _kernel_from_payload(signal_kernel_payload)
    preprocessor = None
    if preprocessing_payload is not None:
        try:
            preprocessor = GpPreprocessor.from_payload(preprocessing_payload)
            validate_encoded_gp_matrix(preprocessor, x_train_scaled)
            if not isinstance(signal_kernel, MixedPredictorKernel) or (
                tuple(signal_kernel.numeric_indices) != preprocessor.numeric_indices
                or tuple(signal_kernel.categorical_indices)
                != preprocessor.active_categorical_indices
            ):
                raise GaussianProcessRegressionError("gp_model_artifact_invalid")
            expected_mean = np.array([state.mean for state in preprocessor.states])
            expected_scale = np.array([state.scale for state in preprocessor.states])
            if not np.array_equal(x_mean, expected_mean) or not np.array_equal(
                x_scale, expected_scale
            ):
                raise GaussianProcessRegressionError("gp_model_artifact_invalid")
        except GpPreprocessingError as exc:
            raise GaussianProcessRegressionError("gp_model_artifact_invalid") from exc
    elif isinstance(signal_kernel, MixedPredictorKernel):
        raise GaussianProcessRegressionError("gp_model_artifact_invalid")
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
        preprocessing=preprocessor,
    )


def _prediction_rows(parsed: _ParsedRows, indices: IntArray | None = None) -> Any:
    if parsed.raw_predictor_rows is None:
        return parsed.x if indices is None else parsed.x[indices]
    return (
        parsed.raw_predictor_rows
        if indices is None
        else [parsed.raw_predictor_rows[int(i)] for i in indices]
    )


def _fit_parsed_model(
    parsed: _ParsedRows, options: GaussianProcessOptions, indices: IntArray | None = None
) -> _FitResult:
    x = parsed.x if indices is None else parsed.x[indices]
    y = parsed.y if indices is None else parsed.y[indices]
    if parsed.raw_predictor_rows is None:
        return _fit_model(x, y, options)
    return _fit_model(
        x,
        y,
        options,
        raw_predictors=_prediction_rows(parsed, indices),
        predictor_specs=parsed.predictor_specs,
    )


def _fit_model(
    x: FloatArray,
    y: FloatArray,
    options: GaussianProcessOptions,
    *,
    raw_predictors: list[list[float | str]] | None = None,
    predictor_specs: tuple[GpPredictorSpec, ...] = (),
) -> _FitResult:
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]
    from sklearn.gaussian_process import GaussianProcessRegressor  # type: ignore[import-untyped]

    from app.statistics.gp_mixed_kernels import MixedPredictorKernel

    preprocessor = None
    if raw_predictors is not None:
        try:
            preprocessor, scaled_x = fit_gp_preprocessor(
                raw_predictors,
                predictor_specs,
                standardize_numeric=options.standardize_predictors,
                allow_constant_numeric=not options.standardize_predictors,
            )
        except GpPreprocessingError as exc:
            raise GaussianProcessRegressionError(exc.code) from exc
        x_mean = np.array([state.mean for state in preprocessor.states])
        x_scale = np.array([state.scale for state in preprocessor.states])
    else:
        x_mean = np.mean(x, axis=0) if options.standardize_predictors else np.zeros(x.shape[1])
        x_scale = (
            np.std(x, axis=0, ddof=1) if options.standardize_predictors else np.ones(x.shape[1])
        )
        scaled_x = (x - x_mean) / x_scale
    if np.any(~np.isfinite(x_scale)) or np.any(x_scale <= 0.0):
        raise GaussianProcessRegressionError("gp_constant_predictor")
    y_mean = float(np.mean(y)) if options.normalize_response else 0.0
    y_scale = float(np.std(y, ddof=1)) if options.normalize_response else 1.0
    if not isfinite(y_scale) or y_scale <= 0.0:
        raise GaussianProcessRegressionError("gp_constant_response")
    scaled_y = (y - y_mean) / y_scale
    if preprocessor is None:
        signal_kernel = _build_signal_kernel(options.kernel_preset, x.shape[1], options)
    else:
        from sklearn.gaussian_process.kernels import ConstantKernel  # type: ignore[import-untyped]

        numeric_count = len(preprocessor.numeric_indices)
        numeric_kernel = (
            _build_signal_kernel(options.kernel_preset, numeric_count, options)
            if numeric_count
            else ConstantKernel(1.0, (1e-3, 1e3))
        )
        signal_kernel = MixedPredictorKernel(
            numeric_kernel, preprocessor.numeric_indices, preprocessor.active_categorical_indices
        )
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
    optimizer_runs: list[dict[str, Any]] = []
    model = GaussianProcessRegressor(
        kernel=kernel,
        alpha=alpha,
        optimizer=_bounded_optimizer(options.deadline_monotonic, options.optimizer, optimizer_runs),
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
    fit_elapsed_seconds = time.monotonic() - started
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
        predictor_medians=np.asarray(np.median(x, axis=0), dtype=np.float64)
        if preprocessor is None
        else np.array(
            [
                state.median
                if state.spec.kind == "numeric"
                else state.vocabulary.index(str(state.mode))
                for state in preprocessor.states
            ],
            dtype=np.float64,
        ),
        signal_kernel=fitted_signal,
        signal_kernel_payload=signal_payload,
        observation_noise_variance_scaled=estimated_noise,
        fitted_kernel_text=str(model.kernel_),
        log_marginal_likelihood=float(model.log_marginal_likelihood_value_),
        converged=converged,
        preprocessing=preprocessor,
    )
    predicted = predict_from_gaussian_process_state(
        state, raw_predictors if raw_predictors is not None else x
    )
    return _FitResult(
        state=state,
        fitted=predicted["mean"],
        latent_standard_deviation=predicted["latent_standard_deviation"],
        predictive_standard_deviation=predicted["predictive_standard_deviation"],
        elapsed_seconds=fit_elapsed_seconds,
        optimizer_runs=optimizer_runs,
    )


def _bounded_theta(z: FloatArray, bounds: FloatArray) -> tuple[FloatArray, FloatArray]:
    from scipy.special import expit  # type: ignore[import-untyped]

    sigmoid = expit(z)
    complement = expit(-z)
    width = bounds[:, 1] - bounds[:, 0]
    # Evaluate from the nearer endpoint to avoid cancellation/roundoff overshoot.
    theta = np.where(z < 0, bounds[:, 0] + width * sigmoid, bounds[:, 1] - width * complement)
    return theta, width * sigmoid * complement


def _bounded_optimizer(
    deadline: float | None,
    algorithm: Literal["l_bfgs_b", "bfgs"] = "l_bfgs_b",
    records: list[dict[str, Any]] | None = None,
) -> Any:
    from scipy.optimize import minimize  # type: ignore[import-untyped]
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]

    def optimize(objective: Any, theta: FloatArray, bounds: FloatArray) -> tuple[FloatArray, float]:
        if not np.all(np.isfinite(bounds)) or np.any(bounds[:, 0] >= bounds[:, 1]):
            raise GaussianProcessRegressionError("gp_kernel_bounds_invalid")

        def checked(parameters: FloatArray) -> Any:
            if deadline is not None and time.monotonic() >= deadline:
                raise GaussianProcessRegressionError("gp_time_budget_exhausted")
            return objective(parameters)

        if algorithm == "bfgs":
            fraction = (theta - bounds[:, 0]) / (bounds[:, 1] - bounds[:, 0])
            if np.any(fraction <= 0) or np.any(fraction >= 1):
                raise GaussianProcessRegressionError("gp_bfgs_initial_on_boundary")
            initial_z = np.log(fraction) - np.log1p(-fraction)

            def transformed(z: FloatArray) -> tuple[float, FloatArray]:
                parameters, derivative = _bounded_theta(z, bounds)
                value, gradient = checked(parameters)
                return float(value), np.asarray(gradient, dtype=np.float64) * derivative

            applied_options: dict[str, Any] = {"gtol": 1e-5}
            result = minimize(
                transformed, initial_z, method="BFGS", jac=True, options=applied_options
            )
            final_theta, _derivative = _bounded_theta(result.x, bounds)
        else:
            applied_options = {}
            result = minimize(checked, theta, method="L-BFGS-B", jac=True, bounds=bounds)
            final_theta = np.asarray(result.x, dtype=np.float64)
        value, gradient = checked(final_theta)
        gradient = np.asarray(gradient, dtype=np.float64)
        if not (
            np.isfinite(value)
            and np.all(np.isfinite(final_theta))
            and np.all(np.isfinite(gradient))
        ):
            raise GaussianProcessRegressionError("gp_fit_failed")
        distance = np.minimum(final_theta - bounds[:, 0], bounds[:, 1] - final_theta)
        near = distance <= 1e-6 * (bounds[:, 1] - bounds[:, 0])
        projected = gradient.copy()
        projected[(final_theta - bounds[:, 0] <= 1e-6) & (gradient > 0)] = 0
        projected[(bounds[:, 1] - final_theta <= 1e-6) & (gradient < 0)] = 0
        saturation = algorithm == "bfgs" and bool(np.any(near & (np.abs(projected) > 1e-3)))
        converged = bool(result.success) and not saturation
        if records is not None:
            records.append(
                {
                    "optimizer": algorithm,
                    "scipy_method": "BFGS" if algorithm == "bfgs" else "L-BFGS-B",
                    "options": applied_options,
                    "defaults": "SciPy " + importlib.metadata.version("scipy"),
                    "initial_log_theta": theta.tolist(),
                    "final_log_theta": final_theta.tolist(),
                    "log_bounds": bounds.tolist(),
                    "converged": converged,
                    "status": int(result.status),
                    "termination": "transformed_boundary_saturation"
                    if saturation
                    else "converged"
                    if converged
                    else "optimizer_not_converged",
                    "iterations": int(result.nit),
                    "evaluations": int(result.nfev),
                    "objective": float(value),
                    "theta_gradient_inf_norm": float(np.max(np.abs(gradient))),
                    "optimizer_gradient_inf_norm": float(np.max(np.abs(result.jac))),
                    "near_bound": bool(np.any(near)),
                }
            )
        if not converged:
            warnings.warn(
                "Gaussian Process optimizer failed to converge.", ConvergenceWarning, stacklevel=2
            )
        return final_theta, float(value)

    return optimize


def _build_signal_kernel(
    preset: KernelPreset, predictor_count: int, options: GaussianProcessOptions | None = None
) -> Any:
    from sklearn.gaussian_process.kernels import (  # type: ignore[import-untyped]
        RBF,
        ConstantKernel,
        Matern,
        RationalQuadratic,
    )

    amplitude = ConstantKernel(1.0, (1e-3, 1e3))
    active = options or GaussianProcessOptions()
    length_scale = np.full(predictor_count, active.length_scale_initial, dtype=np.float64)
    length_bounds = (active.length_scale_lower, active.length_scale_upper)
    if preset == "matern_5_2_ard":
        base = Matern(length_scale=length_scale, length_scale_bounds=length_bounds, nu=2.5)
    elif preset == "matern_3_2_ard":
        base = Matern(length_scale=length_scale, length_scale_bounds=length_bounds, nu=1.5)
    elif preset == "rbf_ard":
        base = RBF(length_scale=length_scale, length_scale_bounds=length_bounds)
    elif preset == "rational_quadratic":
        base = RationalQuadratic(
            length_scale=active.length_scale_initial,
            alpha=1.0,
            length_scale_bounds=length_bounds,
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
    from app.statistics.gp_mixed_kernels import MixedPredictorKernel, mixed_kernel_to_payload

    if isinstance(kernel, MixedPredictorKernel):
        mixed = mixed_kernel_to_payload(kernel)
        signal = mixed["signal"]
        return {
            "preset": preset,
            "amplitude": signal["amplitude"],
            "length_scales": signal.get("length_scales", []),
            **(
                {"rational_quadratic_alpha": signal["rational_quadratic_alpha"]}
                if "rational_quadratic_alpha" in signal
                else {}
            ),
            "mixed_kernel": mixed,
        }
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

    from app.statistics.gp_mixed_kernels import mixed_kernel_from_payload

    if "mixed_kernel" in payload:
        try:
            if payload.get("preset") not in {
                "matern_5_2_ard",
                "matern_3_2_ard",
                "rbf_ard",
                "rational_quadratic",
            }:
                raise ValueError("unknown numeric kernel policy")
            kernel = mixed_kernel_from_payload(payload["mixed_kernel"])
            restored = _kernel_payload(kernel, cast(KernelPreset, payload.get("preset")))
            if restored != payload:
                raise ValueError("mixed signal metadata mismatch")
            return kernel
        except ValueError as exc:
            raise GaussianProcessRegressionError("gp_model_artifact_invalid") from exc
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
        "preprocessing": state.preprocessing.to_payload()
        if state.preprocessing is not None
        else None,
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
    scored_mask: NDArray[np.bool_] | None = None,
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
    if scored_mask is not None:
        if not np.any(scored_mask):
            raise GaussianProcessRegressionError("gp_cross_validation_failed")
        observed, predicted, predictive_std = (
            observed[scored_mask],
            predicted[scored_mask],
            predictive_std[scored_mask],
        )
    residual = observed - predicted
    press = float(np.sum(residual**2))
    tss = float(np.sum((observed - np.mean(observed)) ** 2))
    variance = np.maximum(predictive_std**2, np.finfo(np.float64).tiny)
    nlpd = float(np.mean(0.5 * (np.log(2.0 * pi * variance) + residual**2 / variance)))
    half_width = NORMAL_975 * predictive_std
    coverage = float(np.mean(np.abs(residual) <= half_width))
    return {
        "predicted_r_squared": 1.0 - press / tss if tss > 0 else None,
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
    if (
        cv_mean is not None
        and cv_predictive_std is not None
        and isfinite(float(cv_mean[index]))
        and isfinite(float(cv_predictive_std[index]))
    ):
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
    hold = _hold_values(state)
    for index, predictor in enumerate(predictors):
        nominal = predictor.measurement_level == "nominal"
        values: list[float | str] = (
            list(state.preprocessing.states[index].vocabulary)
            if nominal and state.preprocessing is not None
            else [
                float(value)
                for value in np.linspace(np.min(x[:, index]), np.max(x[:, index]), points)
            ]
        )
        grid = [list(hold) for _ in values]
        for row, value in enumerate(values):
            grid[row][index] = value
        prediction = predict_from_gaussian_process_state(state, grid)
        output.append(
            {
                "column_id": predictor.column_id,
                "display_name": predictor.display_name,
                "kind": "nominal" if nominal else "numeric",
                "fixed_values": hold,
                "fixed_value_policy": "numeric_median_nominal_mode",
                "points": [
                    _prediction_point(value, prediction, row) for row, value in enumerate(values)
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
    x_column_id: str | None = None,
    y_column_id: str | None = None,
) -> dict[str, object] | None:
    numeric = [i for i, column in enumerate(predictors) if column.measurement_level != "nominal"]
    if len(numeric) < 2:
        if x_column_id is not None or y_column_id is not None:
            raise GaussianProcessRegressionError("gp_surface_axes_invalid")
        return None
    indices = {column.column_id: i for i, column in enumerate(predictors)}
    xi = indices.get(x_column_id, -1) if x_column_id is not None else numeric[0]
    yi = indices.get(y_column_id, -1) if y_column_id is not None else numeric[1]
    if xi not in numeric or yi not in numeric or xi == yi:
        raise GaussianProcessRegressionError("gp_surface_axes_invalid")
    x_values = np.linspace(np.min(x[:, xi]), np.max(x[:, xi]), grid_size)
    y_values = np.linspace(np.min(x[:, yi]), np.max(x[:, yi]), grid_size)
    hold = _hold_values(state)
    grid = [list(hold) for _ in range(grid_size * grid_size)]
    row = 0
    for y_value in y_values:
        for x_value in x_values:
            grid[row][xi] = float(x_value)
            grid[row][yi] = float(y_value)
            row += 1
    prediction = predict_from_gaussian_process_state(state, grid)
    return {
        "x_column_id": predictors[xi].column_id,
        "x_display_name": predictors[xi].display_name,
        "y_column_id": predictors[yi].column_id,
        "y_display_name": predictors[yi].display_name,
        "grid_size": grid_size,
        "fixed_values": hold,
        "fixed_value_policy": "numeric_median_nominal_mode",
        "points": [
            {
                "x": float(grid[index][xi]),
                "y": float(grid[index][yi]),
                "predicted_mean": float(prediction["mean"][index]),
                "predictive_standard_deviation": float(
                    prediction["predictive_standard_deviation"][index]
                ),
                "latent_standard_deviation": float(prediction["latent_standard_deviation"][index]),
            }
            for index in range(len(grid))
        ],
    }


def _hold_values(state: GaussianProcessFittedState) -> list[float | str]:
    return (
        list(state.preprocessing.hold_values)
        if state.preprocessing is not None
        else [float(value) for value in state.predictor_medians]
    )


def _training_range_rows(
    state: GaussianProcessFittedState, x: FloatArray, predictors: Sequence[GaussianProcessColumn]
) -> list[dict[str, Any]]:
    rows = []
    for i, column in enumerate(predictors):
        item: dict[str, Any] = {"column_id": column.column_id, "display_name": column.display_name}
        if column.measurement_level == "nominal" and state.preprocessing is not None:
            trained = state.preprocessing.states[i]
            item.update(kind="nominal", levels=list(trained.vocabulary), mode=trained.mode)
        else:
            item.update(
                kind="numeric",
                minimum=float(np.min(x[:, i])),
                maximum=float(np.max(x[:, i])),
                median=float(np.median(x[:, i])),
            )
        rows.append(item)
    return rows


def _prediction_point(
    value: float | str, prediction: dict[str, FloatArray], index: int
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
    length_bounds: tuple[float, float] = (0.01, 100.0),
) -> list[dict[str, object]]:
    payload = state.signal_kernel_payload
    rows = [
        _parameter_row(
            "signal_amplitude", None, float(cast(float, payload["amplitude"])), 1e-3, 1e3
        )
    ]
    length_scales = cast(list[float], payload["length_scales"])
    numeric_predictors = [column for column in predictors if column.measurement_level != "nominal"]
    if len(length_scales) == 1 and len(numeric_predictors) > 1:
        rows.append(_parameter_row("shared_length_scale", None, length_scales[0], *length_bounds))
    else:
        rows.extend(
            _parameter_row("length_scale", predictor.column_id, value, *length_bounds)
            for predictor, value in zip(numeric_predictors, length_scales, strict=True)
        )
    mixed = payload.get("mixed_kernel")
    if isinstance(mixed, dict):
        rows.extend(
            _parameter_row("categorical_theta", predictors[index].column_id, theta, 1e-4, 1e2)
            for index, theta in zip(
                mixed["categorical_indices"], mixed["categorical_theta"], strict=True
            )
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
    length_bounds: tuple[float, float] = (0.01, 100.0),
) -> list[str]:
    from app.statistics.gp_mixed_kernels import MixedPredictorKernel, mixed_kernel_warning_codes

    codes = ["gp_predictive_not_causal", "gp_uncertainty_conditional_on_kernel"]
    if state.preprocessing is not None:
        codes.extend(state.preprocessing.warning_codes)
        if not state.preprocessing.numeric_indices:
            codes.append("gp_nominal_only_signal")
    if isinstance(state.signal_kernel, MixedPredictorKernel):
        codes.extend(mixed_kernel_warning_codes(state.signal_kernel))
    if parsed.n_excluded_missing + parsed.n_excluded_non_numeric > 0:
        codes.append("missing_values_excluded")
    if not state.converged or not cv_converged:
        codes.append("gp_not_converged")
    payload = state.signal_kernel_payload
    amplitude = float(cast(float, payload["amplitude"]))
    length_scales = [float(value) for value in cast(list[float], payload["length_scales"])]
    if _near_bound(amplitude, 1e-3, 1e3):
        codes.append("gp_amplitude_near_bound")
    if any(_near_bound(value, *length_bounds) for value in length_scales):
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
    if sum(column.measurement_level == "nominal" for column in predictors) > 4:
        raise GaussianProcessRegressionError("gp_nominal_predictor_count_limit")
    ids = [column.column_id for column in predictors]
    if len(set(ids)) != len(ids):
        raise GaussianProcessRegressionError("gp_duplicate_predictor")
    if response.column_id in ids:
        raise GaussianProcessRegressionError("gp_response_in_predictors")


def _validate_options(options: GaussianProcessOptions) -> None:
    if options.resource_profile not in {"standard_exact", "extended_exact"}:
        raise GaussianProcessRegressionError("gp_resource_options_invalid")
    if options.validation_method in {"group_k_fold", "time_series_split"} and options.cv_shuffle:
        raise GaussianProcessRegressionError("gp_validation_shuffle_unsupported")
    if (options.validation_method == "group_k_fold") != (options.group_column_id is not None):
        raise GaussianProcessRegressionError("gp_validation_group_required")
    if options.validation_method == "time_series_split":
        if options.time_column_id is None or options.time_format not in {"numeric", "timestamp"}:
            raise GaussianProcessRegressionError("gp_validation_time_required")
        if options.time_format == "numeric" and not (
            options.time_unit and options.time_unit.strip()
        ):
            raise GaussianProcessRegressionError("gp_validation_time_unit_required")
        if options.time_format == "timestamp" and options.time_unit is not None:
            raise GaussianProcessRegressionError("gp_validation_time_options_invalid")
        if options.timestamp_timezone not in {"require_offset", "UTC"}:
            raise GaussianProcessRegressionError("gp_validation_time_options_invalid")
    elif (
        options.time_column_id is not None
        or options.time_format is not None
        or options.time_unit is not None
        or options.gap_time_blocks
    ):
        raise GaussianProcessRegressionError("gp_validation_time_options_invalid")
    if options.lagged_column_ids or options.lags or options.series_column_id is not None:
        if options.validation_method != "time_series_split":
            raise GaussianProcessRegressionError("gp_lag_time_validation_required")
        if (
            not options.lagged_column_ids
            or not options.lags
            or len(set(options.lags)) != len(options.lags)
            or len(set(options.lagged_column_ids)) != len(options.lagged_column_ids)
            or any(
                isinstance(lag, bool) or not isinstance(lag, int) or not 1 <= lag <= 100
                for lag in options.lags
            )
        ):
            raise GaussianProcessRegressionError("gp_lag_definition_invalid")
    lengths = (options.length_scale_lower, options.length_scale_initial, options.length_scale_upper)
    if not all(isfinite(value) and value > 0 for value in lengths) or not (
        options.length_scale_lower < options.length_scale_upper
        and options.length_scale_lower <= options.length_scale_initial <= options.length_scale_upper
    ):
        raise GaussianProcessRegressionError("gp_length_scale_invalid")
    coordinate = "standardized" if options.standardize_predictors else "original"
    if options.length_scale_coordinate_system not in {None, coordinate}:
        raise GaussianProcessRegressionError("gp_length_scale_coordinate_mismatch")
    if options.optimizer not in {"l_bfgs_b", "bfgs"}:
        raise GaussianProcessRegressionError("gp_optimizer_invalid")
    if options.optimizer == "bfgs" and options.length_scale_initial in {
        options.length_scale_lower,
        options.length_scale_upper,
    }:
        raise GaussianProcessRegressionError("gp_bfgs_initial_on_boundary")
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
    if predictor_count > MAX_GP_PREDICTORS:
        raise GaussianProcessRegressionError("gp_derived_predictor_count_limit")
    if parsed.y.size < max(5, predictor_count + 2):
        raise GaussianProcessRegressionError("gp_usable_rows_too_few")
    row_limit = 2000 if options.resource_profile == "extended_exact" else MAX_GP_USABLE_ROWS
    if parsed.y.size > row_limit:
        raise GaussianProcessRegressionError("gp_usable_rows_limit")
    if not np.all(np.isfinite(parsed.x)) or not np.all(np.isfinite(parsed.y)):
        raise GaussianProcessRegressionError("gp_fit_failed")
    if float(np.var(parsed.y, ddof=1)) <= 0.0:
        raise GaussianProcessRegressionError("gp_constant_response")
    numeric_indices = (
        [i for i, spec in enumerate(parsed.predictor_specs) if spec.kind == "numeric"]
        if parsed.predictor_specs
        else list(range(predictor_count))
    )
    if np.any(np.var(parsed.x[:, numeric_indices], axis=0, ddof=1) <= 0.0):
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
    options: GaussianProcessOptions | None = None,
    metadata_columns: Sequence[GaussianProcessColumn] = (),
) -> _ParsedRows:
    active = options or GaussianProcessOptions()
    by_id = {column.column_id: column for column in (response, *predictors, *metadata_columns)}
    required_ids = [
        value
        for value in (active.group_column_id, active.time_column_id, active.series_column_id)
        if value is not None
    ]
    if any(value not in by_id for value in [*required_ids, *active.lagged_column_ids]):
        raise GpValidationError("gp_validation_metadata_column_missing")
    for column_id in active.lagged_column_ids:
        column = by_id[column_id]
        if (
            column.data_type not in {"integer", "decimal"}
            or column.measurement_level == "nominal"
            or column.role == "id"
        ):
            raise GpValidationError("gp_lag_source_type_unsupported")
    lag_features = None
    if active.lagged_column_ids:
        source_rows: list[Sequence[str | None]] = []
        preparation_bytes = 0
        derived_count = len(active.lagged_column_ids) * len(active.lags)
        for source_row in rows:
            # Reserve for strings, row containers, sorted observations, and lag lineage.
            preparation_bytes += (
                2048
                + 64 * len(source_row)
                + sum(4 * len(value) for value in source_row if value is not None)
                + 512 * derived_count
            )
            if preparation_bytes > MAX_GP_LAG_PREPARATION_BYTES:
                raise GaussianProcessRegressionError("gp_parse_memory_budget_exceeded")
            source_rows.append(source_row)
        observations: list[LagObservation] = []
        for index, row in enumerate(source_rows):
            series = (
                _row_value(row, by_id[active.series_column_id].column_index)
                if active.series_column_id
                else ""
            )
            if active.series_column_id and (series is None or not str(series).strip()):
                raise GpValidationError("gp_lag_series_missing")
            assert active.time_column_id is not None and active.time_format is not None
            observations.append(
                LagObservation(
                    index,
                    parse_time_value(
                        _row_value(row, by_id[active.time_column_id].column_index),
                        time_format=active.time_format,
                        timestamp_timezone=active.timestamp_timezone,
                        decimal=decimal,
                        thousands=thousands,
                    ),
                    str(series or ""),
                    {
                        column_id: _parse_number(
                            _row_value(row, by_id[column_id].column_index), decimal, thousands
                        )
                        for column_id in active.lagged_column_ids
                    },
                )
            )
        lag_features = build_lag_features(
            observations, column_ids=active.lagged_column_ids, lags=active.lags
        )
        rows = source_rows
    mixed = any(column.measurement_level == "nominal" for column in predictors)
    specs = tuple(
        GpPredictorSpec(
            column.column_id, "nominal" if column.measurement_level == "nominal" else "numeric"
        )
        for column in predictors
    )
    if active.lagged_column_ids:
        specs += tuple(
            GpPredictorSpec(f"gp_lag:{column_id}:{lag}", "numeric")
            for column_id in active.lagged_column_ids
            for lag in active.lags
        )
    x_rows: list[list[Any]] = []
    y_values: list[float] = []
    row_indices: list[int] = []
    n_total = 0
    n_missing = 0
    n_non_numeric = 0
    n_lag = 0
    group_values: list[str] | None = [] if active.group_column_id else None
    time_values: list[float] | None = [] if active.time_column_id else None
    lag_times: list[list[float]] | None = [] if lag_features is not None else None
    lineage_rows: list[dict[str, object]] = []
    excluded_lag_rows: list[int] = []
    for row_index, row in enumerate(rows):
        n_total += 1
        raw = [_row_value(row, column.column_index) for column in (response, *predictors)]
        if any(value is None or not str(value).strip() for value in raw):
            n_missing += 1
            continue
        parsed: list[float | str | None] = [_parse_number(raw[0], decimal, thousands)]
        parsed.extend(
            str(value)
            if column.measurement_level == "nominal"
            else _parse_number(value, decimal, thousands)
            for column, value in zip(predictors, raw[1:], strict=True)
        )
        if any(value is None for value in parsed):
            n_non_numeric += 1
            continue
        finite = [cast(float | str, value) for value in parsed]
        if lag_features is not None:
            if row_index not in lag_features.values_by_row:
                n_lag += 1
                excluded_lag_rows.append(row_index)
                continue
            finite.extend(lag_features.values_by_row[row_index])
            assert lag_times is not None
            lag_times.append(lag_features.source_times_by_row[row_index])
            lineage_rows.append(
                {
                    "row_index": row_index,
                    "source_row_indices": lag_features.source_rows_by_row[row_index],
                    "source_times": lag_features.source_times_by_row[row_index],
                    "target_time": observations[row_index].time,
                }
            )
        if group_values is not None:
            assert active.group_column_id is not None
            value = _row_value(row, by_id[active.group_column_id].column_index)
            if value is None or not str(value).strip():
                raise GpValidationError("gp_validation_group_missing")
            group_values.append(str(value))
        if time_values is not None:
            assert active.time_column_id is not None and active.time_format is not None
            time_values.append(
                parse_time_value(
                    _row_value(row, by_id[active.time_column_id].column_index),
                    time_format=active.time_format,
                    timestamp_timezone=active.timestamp_timezone,
                    decimal=decimal,
                    thousands=thousands,
                )
            )
        y_values.append(cast(float, finite[0]))
        x_rows.append(finite[1:])
        row_indices.append(row_index)
        row_limit = 2000 if active.resource_profile == "extended_exact" else MAX_GP_USABLE_ROWS
        if len(y_values) > row_limit:
            raise GaussianProcessRegressionError("gp_usable_rows_limit")
    if mixed and len(x_rows) >= 2:
        _, numeric_x = fit_gp_preprocessor(
            x_rows, specs, standardize_numeric=False, allow_constant_numeric=True
        )
    elif mixed:
        numeric_x = np.empty((len(x_rows), len(specs)), dtype=np.float64)
    else:
        numeric_x = np.asarray(x_rows, dtype=np.float64)
    return _ParsedRows(
        x=numeric_x,
        y=np.asarray(y_values, dtype=np.float64),
        row_indices=row_indices,
        n_total=n_total,
        n_excluded_missing=n_missing,
        n_excluded_non_numeric=n_non_numeric,
        groups=group_values,
        times=time_values,
        lag_source_times=lag_times,
        n_excluded_lag=n_lag,
        raw_predictor_rows=x_rows if mixed else None,
        predictor_specs=specs if mixed else (),
        feature_lineage=(
            {
                "kind": "positive_observation_order_lags",
                "prediction_horizon": 1,
                "time_column_id": active.time_column_id,
                "series_column_id": active.series_column_id,
                "gap_policy": "exclude_embargo_sources",
                "prediction_input_policy": "explicit_past_lag_values",
                "irregular_intervals": lag_features.irregular_intervals,
                "definitions": [
                    {
                        "column_id": f"gp_lag:{column_id}:{lag}",
                        "source_column_id": column_id,
                        "lag": lag,
                        "interval": "observation_order",
                    }
                    for column_id in active.lagged_column_ids
                    for lag in active.lags
                ],
                "excluded_row_indices": excluded_lag_rows,
                "exclusion_reason": "insufficient_or_missing_past_observation",
                "row_identity": "filtered_snapshot_zero_based_row_index",
                "rows": lineage_rows,
            }
            if lag_features is not None
            else None
        ),
    )


def _lag_predictor_columns(
    response: GaussianProcessColumn,
    predictors: Sequence[GaussianProcessColumn],
    metadata: Sequence[GaussianProcessColumn],
    options: GaussianProcessOptions,
) -> list[GaussianProcessColumn]:
    by_id = {column.column_id: column for column in (response, *predictors, *metadata)}
    return [
        GaussianProcessColumn(
            f"gp_lag:{column_id}:{lag}",
            -1,
            f"{by_id[column_id].display_name} [lag {lag}]",
            "decimal",
            "continuous",
            "feature",
            by_id[column_id].unit,
        )
        for column_id in options.lagged_column_ids
        for lag in options.lags
    ]


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
