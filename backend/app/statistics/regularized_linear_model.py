from __future__ import annotations

import importlib.metadata
import time
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal

import numpy as np
from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]
from sklearn.linear_model import ElasticNet, Lasso, Ridge  # type: ignore[import-untyped]
from sklearn.model_selection import KFold, LeaveOneOut  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline  # type: ignore[import-untyped]
from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

from app.statistics.linear_model import (
    FloatArray,
    LinearModelColumn,
    LinearModelError,
    _column_payload,
    _equation_payload,
    _histogram_payload,
    _parse_rows,
    _qq_plot_payload,
    _training_domain_payload,
    build_linear_model_design_matrix,
)

EstimatorKind = Literal["ridge", "lasso", "elastic_net"]
MAX_FITS = 10_000
MAX_ROWS = 10_000
MAX_FEATURES = 200
MAX_SOURCE_ROWS = 100_000


@dataclass(frozen=True)
class RegularizationConfig:
    estimator: EstimatorKind = "ridge"
    mode: Literal["automatic_cv", "fixed"] = "automatic_cv"
    validation: Literal["k_fold", "leave_one_out", "none"] = "k_fold"
    outer_folds: int = 5
    inner_folds: int = 5
    shuffle: bool = True
    random_seed: int = 20260907
    alpha_candidates: int = 49
    alpha_min: float = 1e-6
    alpha_max: float = 1e6
    fixed_alpha: float | None = None
    l1_ratio_selection: Literal["automatic_cv", "fixed"] = "automatic_cv"
    fixed_l1_ratio: float | None = None
    l1_ratio_candidates: tuple[float, ...] = (0.1, 0.5, 0.7, 0.9, 0.95, 0.99)
    max_iter: int = 10_000
    tolerance: float = 1e-6
    time_budget_seconds: float = 120.0

    def validate(self) -> None:
        if self.estimator not in {"ridge", "lasso", "elastic_net"}:
            raise LinearModelError("regularized_model_estimator_invalid")
        if self.mode not in {"automatic_cv", "fixed"}:
            raise LinearModelError("regularized_model_alpha_invalid")
        if self.validation not in {"k_fold", "leave_one_out", "none"}:
            raise LinearModelError("regularized_model_cv_folds_invalid")
        if not 2 <= self.outer_folds <= 10 or not 2 <= self.inner_folds <= 10:
            raise LinearModelError("regularized_model_cv_folds_invalid")
        if self.mode == "automatic_cv" and self.validation == "none":
            raise LinearModelError("regularized_model_cv_folds_invalid")
        if self.mode == "fixed" and not _positive(self.fixed_alpha):
            raise LinearModelError("regularized_model_alpha_invalid")
        if (
            not 2 <= self.alpha_candidates <= 100
            or not _positive(self.alpha_min)
            or not _positive(self.alpha_max)
            or self.alpha_min >= self.alpha_max
        ):
            raise LinearModelError("regularized_model_alpha_invalid")
        if self.estimator == "elastic_net":
            fixed_ratio = self.mode == "fixed" or self.l1_ratio_selection == "fixed"
            ratios = (self.fixed_l1_ratio,) if fixed_ratio else self.l1_ratio_candidates
            if (
                not ratios
                or len(ratios) > 10
                or any(not _positive(ratio) or float(ratio or 0) >= 1 for ratio in ratios)
            ):
                raise LinearModelError("regularized_model_l1_ratio_invalid")
        if (
            not 1 <= self.max_iter <= 100_000
            or not _positive(self.tolerance)
            or self.tolerance > 0.1
            or not _positive(self.time_budget_seconds)
            or self.time_budget_seconds > 300
        ):
            raise LinearModelError("regularized_model_search_budget_exceeded")


def _positive(value: float | None) -> bool:
    return value is not None and not isinstance(value, bool) and isfinite(value) and value > 0


def _splits(n: int, config: RegularizationConfig, *, inner: bool = False) -> list[Any]:
    if not inner and config.validation == "none":
        return []
    if not inner and config.validation == "leave_one_out":
        if n > 200:
            raise LinearModelError("regularized_model_leave_one_out_limit")
        return list(LeaveOneOut().split(np.arange(n)))
    folds = config.inner_folds if inner else config.outer_folds
    if n < folds or n - int(np.ceil(n / folds)) < 2:
        raise LinearModelError("regularized_model_cv_folds_invalid")
    return list(
        KFold(
            folds,
            shuffle=config.shuffle,
            random_state=config.random_seed if config.shuffle else None,
        ).split(np.arange(n))
    )


def _candidates(config: RegularizationConfig) -> list[tuple[float, float | None]]:
    alphas = (
        [float(config.fixed_alpha or 0)]
        if config.mode == "fixed"
        else np.logspace(
            np.log10(config.alpha_min), np.log10(config.alpha_max), config.alpha_candidates
        ).tolist()
    )
    ratios: Sequence[float | None] = [None]
    if config.estimator == "elastic_net":
        ratios = (
            [config.fixed_l1_ratio]
            if config.mode == "fixed" or config.l1_ratio_selection == "fixed"
            else config.l1_ratio_candidates
        )
    return [(alpha, ratio) for ratio in ratios for alpha in alphas]


class _FitContext:
    def __init__(self, config: RegularizationConfig) -> None:
        self.config = config
        self.started = time.perf_counter()
        self.fit_count = 0
        self.nonconverged = 0
        self.constant_fold_fits = 0

    def check_budget(self) -> None:
        if time.perf_counter() - self.started > self.config.time_budget_seconds:
            raise LinearModelError("regularized_model_time_budget_exhausted")

    def fit(self, x: FloatArray, y: FloatArray, alpha: float, ratio: float | None) -> Any:
        self.check_budget()
        self.fit_count += 1
        if self.fit_count > MAX_FITS:
            raise LinearModelError("regularized_model_search_budget_exceeded")
        if self.config.estimator == "ridge":
            estimator = Ridge(alpha=alpha, solver="svd", fit_intercept=True)
        elif self.config.estimator == "lasso":
            estimator = Lasso(
                alpha=alpha,
                max_iter=self.config.max_iter,
                tol=self.config.tolerance,
                selection="cyclic",
                fit_intercept=True,
            )
        else:
            estimator = ElasticNet(
                alpha=alpha,
                l1_ratio=ratio,
                max_iter=self.config.max_iter,
                tol=self.config.tolerance,
                selection="cyclic",
                fit_intercept=True,
            )
        model = Pipeline([("scaler", StandardScaler()), ("estimator", estimator)])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            try:
                model.fit(x, y)
            except (ValueError, FloatingPointError, np.linalg.LinAlgError) as exc:
                raise LinearModelError("regularized_model_fit_failed") from exc
        if any(issubclass(item.category, ConvergenceWarning) for item in caught):
            self.nonconverged += 1
        if np.any(model.named_steps["scaler"].var_ == 0):
            self.constant_fold_fits += 1
        if not np.all(np.isfinite(estimator.coef_)) or not isfinite(float(estimator.intercept_)):
            raise LinearModelError("regularized_model_fit_failed")
        self.check_budget()
        return model

    def tune(
        self, x: FloatArray, y: FloatArray
    ) -> tuple[tuple[float, float | None], list[dict[str, Any]]]:
        candidates = _candidates(self.config)
        if self.config.mode == "fixed":
            return candidates[0], []
        splits = _splits(len(y), self.config, inner=True)
        table: list[dict[str, Any]] = []
        for alpha, ratio in candidates:
            errors = []
            for train, test in splits:
                fit = self.fit(x[train], y[train], alpha, ratio)
                errors.append(float(np.mean((y[test] - fit.predict(x[test])) ** 2)))
            table.append(
                {
                    "alpha": alpha,
                    "l1_ratio": ratio,
                    "mean_squared_error": float(np.mean(errors)),
                    "fold_error_sd": float(np.std(errors, ddof=1)),
                    "fold_errors": errors,
                }
            )
        best_error = min(row["mean_squared_error"] for row in table)
        if not isfinite(best_error):
            raise LinearModelError("regularized_model_cv_failed")
        tied = [
            row
            for row in table
            if row["mean_squared_error"] <= best_error + 1e-12 * max(1, abs(best_error))
        ]
        best = min(tied, key=lambda row: (-row["alpha"], row["l1_ratio"] or 0))
        return (best["alpha"], best["l1_ratio"]), table


def calculate_regularized_linear_model(
    rows: Iterable[Sequence[str | None]],
    response_column: LinearModelColumn,
    predictor_columns: Sequence[LinearModelColumn],
    *,
    config: RegularizationConfig,
    decimal: str = ".",
    thousands: str | None = None,
    quadratic_terms: Sequence[str] = (),
    interaction_terms: Sequence[tuple[str, str]] = (),
) -> dict[str, Any]:
    config.validate()
    context = _FitContext(config)

    def bounded_rows() -> Iterable[Sequence[str | None]]:
        for index, row in enumerate(rows):
            if index >= MAX_SOURCE_ROWS:
                raise LinearModelError("regularized_model_row_count_limit")
            yield row

    parsed = _parse_rows(
        bounded_rows(),
        response_column=response_column,
        predictor_columns=predictor_columns,
        decimal=decimal,
        thousands=thousands,
    )
    y = np.asarray(parsed.y_values, dtype=float)
    if len(y) < 5:
        raise LinearModelError("regularized_model_usable_rows_too_few")
    if len(y) > MAX_ROWS:
        raise LinearModelError("regularized_model_row_count_limit")
    if np.ptp(y) == 0:
        raise LinearModelError("linear_model_response_constant")
    matrix = build_linear_model_design_matrix(
        parsed.x_rows,
        predictor_columns,
        quadratic_terms=quadratic_terms,
        interaction_terms=interaction_terms,
    )
    x = matrix.predictors
    if x.shape[1] > MAX_FEATURES:
        raise LinearModelError("regularized_model_feature_count_limit")
    if not np.all(np.isfinite(x)) or not np.all(np.isfinite(y)):
        raise LinearModelError("regularized_model_fit_failed")
    outer = _splits(len(y), config)
    if config.mode == "automatic_cv":
        for train, _ in outer:
            _splits(len(train), config, inner=True)
    path_alphas = np.logspace(
        np.log10(config.alpha_min), np.log10(config.alpha_max), config.alpha_candidates
    )
    candidates = _candidates(config)
    search_fits = len(candidates) * config.inner_folds if config.mode == "automatic_cv" else 0
    estimated_fits = (len(outer) + 1) * (search_fits + 1) + len(path_alphas)
    if estimated_fits > MAX_FITS:
        raise LinearModelError("regularized_model_search_budget_exceeded")

    with threadpool_limits(limits=1):
        oof = np.full(len(y), np.nan)
        fold_rows = []
        for fold_index, (train, test) in enumerate(outer):
            selected, _ = context.tune(x[train], y[train])
            model = context.fit(x[train], y[train], *selected)
            oof[test] = model.predict(x[test])
            scaler = model.named_steps["scaler"]
            fold_rows.append(
                {
                    "fold": fold_index + 1,
                    "training_n": len(train),
                    "validation_n": len(test),
                    "test_row_indices": [parsed.row_indices[int(i)] for i in test],
                    "selected_alpha": selected[0],
                    "selected_l1_ratio": selected[1],
                    "scaler_means": scaler.mean_.tolist(),
                    "scaler_scales": scaler.scale_.tolist(),
                    "constant_feature_indices": np.flatnonzero(scaler.var_ == 0).tolist(),
                }
            )
        selected, curve = context.tune(x, y)
        before_final = context.nonconverged
        final = context.fit(x, y, *selected)
        final_converged = context.nonconverged == before_final
        fitted = np.asarray(final.predict(x), dtype=float)
        if outer and not np.all(np.isfinite(oof)):
            raise LinearModelError("regularized_model_cv_failed")
        path = []
        for alpha in path_alphas:
            path_fit = context.fit(x, y, float(alpha), selected[1])
            path.append(
                {
                    "alpha": float(alpha),
                    "l1_ratio": selected[1],
                    "standardized_coefficients": path_fit.named_steps["estimator"].coef_.tolist(),
                }
            )

    estimator = final.named_steps["estimator"]
    scaler = final.named_steps["scaler"]
    original = estimator.coef_ / scaler.scale_
    intercept = float(estimator.intercept_ - scaler.mean_ @ original)
    all_coefficients = np.r_[intercept, original]
    coefficient_rows: list[dict[str, Any]] = []
    for index, term in enumerate(matrix.coefficient_terms):
        coefficient_rows.append(
            {
                "term": term.term,
                "term_kind": term.term_kind,
                "column_id": term.column.column_id if term.column else None,
                "source_column_ids": [column.column_id for column in term.source_columns],
                "response_column_id": response_column.column_id,
                "level": term.level,
                "reference_level": term.reference_level,
                "coding": term.coding,
                "estimate": float(all_coefficients[index]),
                "standardized_estimate": float(
                    estimator.intercept_ if index == 0 else estimator.coef_[index - 1]
                ),
                "is_zero": bool(index > 0 and estimator.coef_[index - 1] == 0),
            }
        )
    warning_codes = ["regularized_model_predictive_not_causal"]
    if matrix.categorical_predictor_count:
        warning_codes.append("regularized_model_categorical_levelwise_penalty")
    if config.estimator in {"lasso", "elastic_net"}:
        warning_codes.append("regularized_model_hierarchy_not_enforced")
    if config.estimator == "lasso":
        warning_codes.append("lasso_correlated_predictor_instability")
    zero_count = int(np.count_nonzero(estimator.coef_ == 0))
    if zero_count >= x.shape[1] / 2:
        warning_codes.append("lasso_all_or_most_coefficients_zero")
    if context.nonconverged:
        warning_codes.append("regularized_model_convergence_warning")
    if context.constant_fold_fits:
        warning_codes.append("regularized_model_constant_fold_feature")
    if parsed.n_excluded_missing:
        warning_codes.append("missing_values_excluded")
    if parsed.n_excluded_non_numeric:
        warning_codes.append("non_numeric_values_excluded")
    training = _metrics(y, fitted)
    validation = None
    if outer:
        metrics = _metrics(y, oof)
        validation = {
            "method": config.validation,
            "nested": config.mode == "automatic_cv",
            "outer_folds": len(outer),
            "inner_folds": config.inner_folds if config.mode == "automatic_cv" else None,
            "shuffle": config.shuffle,
            "random_seed": config.random_seed,
            "folds": fold_rows,
            "press": metrics["sse"],
            "predicted_r_squared": metrics["r_squared"],
            "rmse": metrics["rmse"],
            "mae": metrics["mae"],
            "oof_predictions": oof.tolist(),
            "row_indices": parsed.row_indices,
        }
        if metrics["r_squared"] < 0:
            warning_codes.append("regularized_model_negative_predicted_r_squared")
        if training["r_squared"] - metrics["r_squared"] > 0.2:
            warning_codes.append("regularized_model_training_cv_gap")
    residual = y - fitted
    point_indices = np.unique(np.linspace(0, len(y) - 1, min(500, len(y)), dtype=int))
    points = [
        {
            "row_index": parsed.row_indices[int(i)],
            "observed": float(y[i]),
            "fitted": float(fitted[i]),
            "residual": float(residual[i]),
            "oof_predicted": float(oof[i]) if outer else None,
            "oof_residual": float(y[i] - oof[i]) if outer else None,
        }
        for i in point_indices
    ]
    return {
        "schema_version": 6,
        "summary_type": "linear_model",
        "estimator": {
            "kind": config.estimator,
            "penalty": {"ridge": "l2", "lasso": "l1", "elastic_net": "elastic_net"}[
                config.estimator
            ],
        },
        "method": f"regularized_{config.estimator}",
        "missing_policy": "complete_case",
        "response": _column_payload(response_column),
        "predictors": [_column_payload(column) for column in predictor_columns],
        "model_specification": {"intercept": True, "terms": matrix.model_terms},
        "sample": {
            "n_total": parsed.n_total,
            "n_used": len(y),
            "n_excluded_missing": parsed.n_excluded_missing,
            "n_excluded_non_numeric": parsed.n_excluded_non_numeric,
            "feature_count": int(x.shape[1]),
        },
        "equation": _equation_payload(
            response_column=response_column, coefficient_rows=coefficient_rows
        ),
        "coefficients": coefficient_rows,
        "fit": training,
        "validation": validation,
        "training_domain": _training_domain_payload(parsed.x_rows, predictor_columns),
        "prediction_basis": {
            "basis_schema_version": 2,
            "kind": "point_only",
            "coefficient_order": [term.term for term in matrix.coefficient_terms],
        },
        "regularization": {
            "mode": config.mode,
            "selected_alpha": selected[0],
            "selected_l1_ratio": selected[1],
            "standardization": "all_design_features_ddof_0_fold_local",
            "response_scale": "original",
            "scaler_means": scaler.mean_.tolist(),
            "scaler_scales": scaler.scale_.tolist(),
            "alpha_min": config.alpha_min,
            "alpha_max": config.alpha_max,
            "alpha_candidates": config.alpha_candidates,
            "l1_ratio_selection": config.l1_ratio_selection
            if config.estimator == "elastic_net"
            else None,
            "candidate_grid": [{"alpha": a, "l1_ratio": r} for a, r in candidates],
            "cv_curve": curve,
            "coefficient_path": path,
            "feature_order": [term.term for term in matrix.coefficient_terms[1:]],
            "zero_coefficient_count": zero_count,
            "max_iter": config.max_iter,
            "tolerance": config.tolerance,
            "converged": final_converged,
            "iterations": int(estimator.n_iter_)
            if getattr(estimator, "n_iter_", None) is not None
            else None,
            "dual_gap": float(estimator.dual_gap_) if hasattr(estimator, "dual_gap_") else None,
            "nonconverged_fits": context.nonconverged,
            "constant_fold_fits": context.constant_fold_fits,
            "estimated_fit_count": estimated_fits,
            "completed_fit_count": context.fit_count,
            "elapsed_seconds": time.perf_counter() - context.started,
            "time_budget_seconds": config.time_budget_seconds,
            "numerical_threads": 1,
        },
        "diagnostics": {
            "points": points,
            "point_count_total": len(y),
            "truncated": len(points) < len(y),
            "histogram": _histogram_payload(residual),
            "qq_plot": _qq_plot_payload(residual, parsed.row_indices),
        },
        "warnings": warning_codes,
        "package_versions": {
            name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn")
        },
    }


def _metrics(y: FloatArray, prediction: FloatArray) -> dict[str, float]:
    residual = y - prediction
    sse = float(residual @ residual)
    tss = float(np.sum((y - np.mean(y)) ** 2))
    return {
        "sse": sse,
        "tss": tss,
        "r_squared": 1 - sse / tss,
        "rmse": float(np.sqrt(sse / len(y))),
        "mae": float(np.mean(np.abs(residual))),
    }
