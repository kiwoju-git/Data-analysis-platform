from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from math import isfinite, sqrt
from typing import Any

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

MAX_FACTORIAL_ANALYSIS_POINTS = 256


class FactorialAnalysisError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class FactorialAnalysisRun:
    run_order: int
    standard_order: int
    center_point: bool
    block_index: int | None
    coded_levels: dict[str, int]
    response: float


@dataclass(frozen=True)
class _Term:
    term_id: str
    label: str
    kind: str
    factor_names: tuple[str, ...]
    values: np.ndarray


def calculate_factorial_analysis(
    runs: Sequence[FactorialAnalysisRun],
    factor_names: Sequence[str],
    *,
    response_name: str,
    response_unit: str | None,
    max_interaction_order: int = 2,
    confidence_level: float = 0.95,
    point_limit: int = MAX_FACTORIAL_ANALYSIS_POINTS,
) -> dict[str, object]:
    _validate_inputs(
        runs,
        factor_names,
        max_interaction_order=max_interaction_order,
        confidence_level=confidence_level,
        point_limit=point_limit,
    )
    ordered_runs = sorted(runs, key=lambda run: run.run_order)
    response = np.asarray([run.response for run in ordered_runs], dtype=float)
    if bool(np.all(response == response[0])):
        raise FactorialAnalysisError("doe_factorial_response_variance_zero")

    terms = _model_terms(
        ordered_runs,
        factor_names,
        max_interaction_order=max_interaction_order,
    )
    design_matrix = np.column_stack([term.values for term in terms])
    rank = int(np.linalg.matrix_rank(design_matrix))
    if rank != design_matrix.shape[1]:
        raise FactorialAnalysisError("doe_factorial_model_rank_deficient")

    coefficients, fitted, residuals, sse = _fit(design_matrix, response)
    n_observations = len(ordered_runs)
    parameter_count = design_matrix.shape[1]
    df_residual = n_observations - rank
    df_model = rank - 1
    response_mean = float(np.mean(response))
    total_ss = float(np.sum((response - response_mean) ** 2))
    model_ss = max(0.0, total_ss - sse)
    residual_ms = sse / df_residual if df_residual > 0 else None
    model_ms = model_ss / df_model if df_model > 0 else None
    model_f = (
        model_ms / residual_ms
        if model_ms is not None and residual_ms is not None and residual_ms > 0
        else None
    )
    model_p = float(stats.f.sf(model_f, df_model, df_residual)) if model_f is not None else None
    coefficient_covariance = (
        residual_ms * np.linalg.inv(design_matrix.T @ design_matrix)
        if residual_ms is not None and residual_ms > 0
        else None
    )
    t_critical = (
        float(stats.t.ppf(0.5 + (confidence_level / 2.0), df_residual)) if df_residual > 0 else None
    )
    term_results = _term_results(
        terms,
        design_matrix,
        response,
        coefficients,
        sse=sse,
        df_residual=df_residual,
        residual_ms=residual_ms,
        coefficient_covariance=coefficient_covariance,
        t_critical=t_critical,
        confidence_level=confidence_level,
    )
    lack_of_fit = _lack_of_fit(
        ordered_runs,
        response,
        factor_names,
        sse=sse,
        df_residual=df_residual,
        parameter_count=parameter_count,
    )
    diagnostics = _diagnostics(
        ordered_runs,
        design_matrix,
        response,
        fitted,
        residuals,
        sse=sse,
        df_residual=df_residual,
        point_limit=point_limit,
    )
    warnings = _warnings(
        ordered_runs,
        df_residual=df_residual,
        residual_ms=residual_ms,
        lack_of_fit=lack_of_fit,
        diagnostics=diagnostics,
        max_interaction_order=max_interaction_order,
        factor_count=len(factor_names),
    )
    r_squared = model_ss / total_ss
    adjusted_r_squared = (
        1.0 - ((sse / df_residual) / (total_ss / (n_observations - 1))) if df_residual > 0 else None
    )

    return {
        "schema_version": 1,
        "summary_type": "factorial_analysis",
        "method": "hierarchical_ols_two_level_full_factorial",
        "response": {"name": response_name, "unit": response_unit},
        "factor_names": list(factor_names),
        "coding": {
            "low": -1,
            "high": 1,
            "center": 0,
            "effect_definition": "two_times_regression_coefficient",
        },
        "model_policy": {
            "hierarchy_enforced": True,
            "max_interaction_order": max_interaction_order,
            "automatic_term_selection": False,
            "center_curvature_included": any(run.center_point for run in ordered_runs),
            "block_fixed_effects_included": len(_block_levels(ordered_runs)) > 1,
            "sum_of_squares": "partial_drop_one",
        },
        "sample": {
            "n_observations": n_observations,
            "factorial_point_count": sum(not run.center_point for run in ordered_runs),
            "center_point_count": sum(run.center_point for run in ordered_runs),
            "block_count": len(_block_levels(ordered_runs)),
            "parameter_count": parameter_count,
            "rank": rank,
            "df_model": df_model,
            "df_residual": df_residual,
        },
        "fit": {
            "response_mean": response_mean,
            "sse": sse,
            "model_ss": model_ss,
            "total_ss": total_ss,
            "residual_mean_square": residual_ms,
            "residual_standard_error": sqrt(residual_ms) if residual_ms is not None else None,
            "r_squared": r_squared,
            "adjusted_r_squared": adjusted_r_squared,
            "f_statistic": model_f,
            "f_p_value": model_p,
        },
        "terms": term_results,
        "ranked_effects": sorted(
            [
                {
                    "term_id": term["term_id"],
                    "label": term["label"],
                    "effect": term["effect"],
                    "absolute_effect": abs(float(term["effect"])),
                }
                for term in term_results
                if term["effect"] is not None
            ],
            key=lambda item: (-float(item["absolute_effect"]), str(item["term_id"])),
        ),
        "anova": {
            "sum_of_squares_policy": "partial_drop_one_terms_not_required_to_sum_to_model_ss",
            "model": {
                "df": df_model,
                "sum_squares": model_ss,
                "mean_square": model_ms,
                "f_statistic": model_f,
                "p_value": model_p,
            },
            "residual": {
                "df": df_residual,
                "sum_squares": sse,
                "mean_square": residual_ms,
            },
            "total": {"df": n_observations - 1, "sum_squares": total_ss},
            "lack_of_fit": lack_of_fit,
        },
        "diagnostics": diagnostics,
        "plots": {
            "main_effects": _main_effects(ordered_runs, factor_names),
            "interactions": _interaction_means(ordered_runs, factor_names),
        },
        "warnings": warnings,
    }


def _validate_inputs(
    runs: Sequence[FactorialAnalysisRun],
    factor_names: Sequence[str],
    *,
    max_interaction_order: int,
    confidence_level: float,
    point_limit: int,
) -> None:
    if not 2 <= len(factor_names) <= 6 or len(set(factor_names)) != len(factor_names):
        raise FactorialAnalysisError("doe_factorial_analysis_factors_invalid")
    if isinstance(max_interaction_order, bool) or not 1 <= max_interaction_order <= min(
        3, len(factor_names)
    ):
        raise FactorialAnalysisError("doe_factorial_interaction_order_invalid")
    if not isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise FactorialAnalysisError("doe_factorial_confidence_level_invalid")
    if isinstance(point_limit, bool) or not 1 <= point_limit <= MAX_FACTORIAL_ANALYSIS_POINTS:
        raise FactorialAnalysisError("doe_factorial_analysis_point_limit_invalid")
    if len(runs) < 2 or len(runs) > MAX_FACTORIAL_ANALYSIS_POINTS:
        raise FactorialAnalysisError("doe_factorial_analysis_run_count_invalid")
    if len({run.run_order for run in runs}) != len(runs):
        raise FactorialAnalysisError("doe_factorial_analysis_run_order_duplicate")
    expected_factors = set(factor_names)
    for run in runs:
        if not isfinite(run.response):
            raise FactorialAnalysisError("doe_factorial_response_not_finite")
        if set(run.coded_levels) != expected_factors:
            raise FactorialAnalysisError("doe_factorial_coded_levels_invalid")
        levels = set(run.coded_levels.values())
        if run.center_point and levels != {0}:
            raise FactorialAnalysisError("doe_factorial_center_coding_invalid")
        if not run.center_point and not levels.issubset({-1, 1}):
            raise FactorialAnalysisError("doe_factorial_coded_levels_invalid")


def _model_terms(
    runs: Sequence[FactorialAnalysisRun],
    factor_names: Sequence[str],
    *,
    max_interaction_order: int,
) -> list[_Term]:
    terms = [
        _Term(
            term_id="intercept",
            label="Intercept",
            kind="intercept",
            factor_names=(),
            values=np.ones(len(runs), dtype=float),
        )
    ]
    for order in range(1, max_interaction_order + 1):
        for indexes in combinations(range(len(factor_names)), order):
            names = tuple(factor_names[index] for index in indexes)
            values = np.asarray(
                [np.prod([run.coded_levels[name] for name in names], dtype=float) for run in runs],
                dtype=float,
            )
            terms.append(
                _Term(
                    term_id=":".join(f"factor_{index + 1}" for index in indexes),
                    label=" * ".join(names),
                    kind="main_effect" if order == 1 else "interaction",
                    factor_names=names,
                    values=values,
                )
            )
    if any(run.center_point for run in runs):
        terms.append(
            _Term(
                term_id="center_curvature",
                label="Center curvature",
                kind="curvature",
                factor_names=(),
                values=np.asarray([1.0 if run.center_point else 0.0 for run in runs]),
            )
        )
    blocks = _block_levels(runs)
    for block in blocks[1:]:
        terms.append(
            _Term(
                term_id=f"block_{block}",
                label=f"Block {block}",
                kind="block",
                factor_names=(),
                values=np.asarray([1.0 if run.block_index == block else 0.0 for run in runs]),
            )
        )
    return terms


def _fit(
    matrix: np.ndarray, response: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    coefficients, _, _, _ = np.linalg.lstsq(matrix, response, rcond=None)
    fitted = matrix @ coefficients
    residuals = response - fitted
    sse = max(0.0, float(residuals @ residuals))
    return coefficients, fitted, residuals, sse


def _term_results(
    terms: Sequence[_Term],
    matrix: np.ndarray,
    response: np.ndarray,
    coefficients: np.ndarray,
    *,
    sse: float,
    df_residual: int,
    residual_ms: float | None,
    coefficient_covariance: np.ndarray | None,
    t_critical: float | None,
    confidence_level: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for index, (term, coefficient) in enumerate(zip(terms, coefficients, strict=True)):
        standard_error = (
            sqrt(max(0.0, float(coefficient_covariance[index, index])))
            if coefficient_covariance is not None
            else None
        )
        statistic = (
            float(coefficient / standard_error)
            if standard_error is not None and standard_error > 0
            else None
        )
        p_value = (
            float(2.0 * stats.t.sf(abs(statistic), df_residual))
            if statistic is not None and df_residual > 0
            else None
        )
        coefficient_ci = (
            {
                "level": confidence_level,
                "lower": float(coefficient - (t_critical * standard_error)),
                "upper": float(coefficient + (t_critical * standard_error)),
            }
            if t_critical is not None and standard_error is not None
            else None
        )
        effect = float(2.0 * coefficient) if term.kind in {"main_effect", "interaction"} else None
        effect_ci = (
            {
                "level": confidence_level,
                "lower": 2.0 * float(coefficient_ci["lower"]),
                "upper": 2.0 * float(coefficient_ci["upper"]),
            }
            if effect is not None and coefficient_ci is not None
            else None
        )
        partial_ss = None
        f_statistic = None
        term_p_value = None
        if index > 0:
            reduced = np.delete(matrix, index, axis=1)
            _, _, _, reduced_sse = _fit(reduced, response)
            partial_ss = max(0.0, reduced_sse - sse)
            if residual_ms is not None and residual_ms > 0:
                f_statistic = partial_ss / residual_ms
                term_p_value = float(stats.f.sf(f_statistic, 1, df_residual))
        results.append(
            {
                "term_id": term.term_id,
                "label": term.label,
                "kind": term.kind,
                "factor_names": list(term.factor_names),
                "coefficient": float(coefficient),
                "effect": effect,
                "standard_error": standard_error,
                "statistic": statistic,
                "p_value": p_value,
                "confidence_interval": coefficient_ci,
                "effect_confidence_interval": effect_ci,
                "partial_sum_squares": partial_ss,
                "f_statistic": f_statistic,
                "f_p_value": term_p_value,
            }
        )
    return results


def _lack_of_fit(
    runs: Sequence[FactorialAnalysisRun],
    response: np.ndarray,
    factor_names: Sequence[str],
    *,
    sse: float,
    df_residual: int,
    parameter_count: int,
) -> dict[str, Any]:
    grouped: dict[tuple[object, ...], list[float]] = defaultdict(list)
    include_block = len(_block_levels(runs)) > 1
    for run, value in zip(runs, response, strict=True):
        key: tuple[object, ...] = tuple(run.coded_levels[name] for name in factor_names)
        if include_block:
            key += (run.block_index,)
        grouped[key].append(float(value))
    pure_error_ss = sum(
        sum((value - (sum(values) / len(values))) ** 2 for value in values)
        for values in grouped.values()
    )
    pure_error_df = len(runs) - len(grouped)
    lack_of_fit_df = len(grouped) - parameter_count
    lack_of_fit_ss = max(0.0, sse - pure_error_ss)
    pure_error_ms = pure_error_ss / pure_error_df if pure_error_df > 0 else None
    lack_of_fit_ms = lack_of_fit_ss / lack_of_fit_df if lack_of_fit_df > 0 else None
    f_statistic = (
        lack_of_fit_ms / pure_error_ms
        if lack_of_fit_ms is not None and pure_error_ms is not None and pure_error_ms > 0
        else None
    )
    p_value = (
        float(stats.f.sf(f_statistic, lack_of_fit_df, pure_error_df))
        if f_statistic is not None
        else None
    )
    available = pure_error_df > 0 and lack_of_fit_df > 0 and pure_error_ms is not None
    return {
        "available": available,
        "unique_design_point_count": len(grouped),
        "pure_error": {
            "df": pure_error_df,
            "sum_squares": pure_error_ss,
            "mean_square": pure_error_ms,
        },
        "lack_of_fit": {
            "df": max(0, lack_of_fit_df),
            "sum_squares": lack_of_fit_ss,
            "mean_square": lack_of_fit_ms,
            "f_statistic": f_statistic,
            "p_value": p_value,
        },
        "residual_df": df_residual,
    }


def _diagnostics(
    runs: Sequence[FactorialAnalysisRun],
    matrix: np.ndarray,
    response: np.ndarray,
    fitted: np.ndarray,
    residuals: np.ndarray,
    *,
    sse: float,
    df_residual: int,
    point_limit: int,
) -> dict[str, Any]:
    parameter_count = matrix.shape[1]
    leverage = np.diag(matrix @ np.linalg.inv(matrix.T @ matrix) @ matrix.T)
    residual_ms = sse / df_residual if df_residual > 0 else None
    standardized: list[float | None] = []
    cooks: list[float | None] = []
    for residual, hat in zip(residuals, leverage, strict=True):
        denominator = residual_ms * max(np.finfo(float).eps, 1.0 - float(hat)) if residual_ms else 0
        standardized_value = float(residual / sqrt(denominator)) if denominator > 0 else None
        cook = (
            (standardized_value**2 * float(hat))
            / (parameter_count * max(np.finfo(float).eps, 1.0 - float(hat)))
            if standardized_value is not None
            else None
        )
        standardized.append(standardized_value)
        cooks.append(cook)
    theoretical, ordered = stats.probplot(residuals, dist="norm", fit=False)
    shapiro_statistic = None
    shapiro_p_value = None
    if 3 <= len(residuals) <= 5000 and float(np.var(residuals)) > np.finfo(float).eps:
        shapiro = stats.shapiro(residuals)
        shapiro_statistic = float(shapiro.statistic)
        shapiro_p_value = float(shapiro.pvalue)
    durbin_watson = (
        float(np.sum(np.diff(residuals) ** 2) / sse) if len(residuals) > 1 and sse > 0 else None
    )
    points = [
        {
            "run_order": run.run_order,
            "standard_order": run.standard_order,
            "observed": float(observed),
            "fitted": float(fitted_value),
            "residual": float(residual),
            "standardized_residual": standardized_value,
            "leverage": float(hat),
            "cooks_distance": cook,
        }
        for run, observed, fitted_value, residual, standardized_value, hat, cook in zip(
            runs,
            response,
            fitted,
            residuals,
            standardized,
            leverage,
            cooks,
            strict=True,
        )
    ][:point_limit]
    return {
        "residual_mean": float(np.mean(residuals)),
        "residual_min": float(np.min(residuals)),
        "residual_max": float(np.max(residuals)),
        "max_abs_standardized_residual": max(
            (abs(value) for value in standardized if value is not None),
            default=None,
        ),
        "high_standardized_residual_count": sum(
            abs(value) > 3 for value in standardized if value is not None
        ),
        "max_leverage": float(np.max(leverage)),
        "high_leverage_threshold": 2.0 * parameter_count / len(runs),
        "high_leverage_count": sum(
            float(value) > 2.0 * parameter_count / len(runs) for value in leverage
        ),
        "max_cooks_distance": max((value for value in cooks if value is not None), default=None),
        "cooks_distance_threshold": 4.0 / len(runs),
        "high_cooks_distance_count": sum(
            value > 4.0 / len(runs) for value in cooks if value is not None
        ),
        "durbin_watson": durbin_watson,
        "shapiro_wilk": {"statistic": shapiro_statistic, "p_value": shapiro_p_value},
        "point_limit": point_limit,
        "points_truncated": len(runs) > point_limit,
        "points": points,
        "qq_points": [
            {"theoretical": float(x), "ordered_residual": float(y)}
            for x, y in zip(theoretical[:point_limit], ordered[:point_limit], strict=True)
        ],
    }


def _main_effects(
    runs: Sequence[FactorialAnalysisRun], factor_names: Sequence[str]
) -> list[dict[str, object]]:
    factorial_runs = [run for run in runs if not run.center_point]
    return [
        {
            "factor": name,
            "low_mean": float(
                np.mean([run.response for run in factorial_runs if run.coded_levels[name] == -1])
            ),
            "high_mean": float(
                np.mean([run.response for run in factorial_runs if run.coded_levels[name] == 1])
            ),
        }
        for name in factor_names
    ]


def _interaction_means(
    runs: Sequence[FactorialAnalysisRun], factor_names: Sequence[str]
) -> list[dict[str, object]]:
    factorial_runs = [run for run in runs if not run.center_point]
    results: list[dict[str, object]] = []
    for first, second in combinations(factor_names, 2):
        cells = []
        for first_level, second_level in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            values = [
                run.response
                for run in factorial_runs
                if run.coded_levels[first] == first_level
                and run.coded_levels[second] == second_level
            ]
            cells.append(
                {
                    "first_level": first_level,
                    "second_level": second_level,
                    "mean": float(np.mean(values)),
                    "n": len(values),
                }
            )
        results.append({"first_factor": first, "second_factor": second, "cells": cells})
    return results


def _warnings(
    runs: Sequence[FactorialAnalysisRun],
    *,
    df_residual: int,
    residual_ms: float | None,
    lack_of_fit: dict[str, Any],
    diagnostics: dict[str, Any],
    max_interaction_order: int,
    factor_count: int,
) -> list[str]:
    warnings = [
        "doe_factorial_randomization_and_independence_not_proven",
        "doe_factorial_effects_are_associations_within_experiment",
    ]
    if max_interaction_order < factor_count:
        warnings.append("doe_factorial_higher_order_interactions_excluded_by_policy")
    if df_residual == 0:
        warnings.append("doe_factorial_model_saturated_no_inference")
    elif df_residual < 5:
        warnings.append("doe_factorial_residual_df_small")
    if residual_ms is not None and residual_ms <= np.finfo(float).eps:
        warnings.append("doe_factorial_residual_variance_zero")
    pure_error = lack_of_fit["pure_error"]
    lack_of_fit_row = lack_of_fit["lack_of_fit"]
    if isinstance(pure_error, dict) and int(pure_error["df"]) == 0:
        warnings.append("doe_factorial_pure_error_unavailable_without_replication")
    if isinstance(lack_of_fit_row, dict) and int(lack_of_fit_row["df"]) == 0:
        warnings.append("doe_factorial_lack_of_fit_df_unavailable")
    if len(_block_levels(runs)) > 1:
        warnings.append("doe_factorial_block_fixed_effects_included")
    if int(diagnostics["high_standardized_residual_count"]) > 0:
        warnings.append("doe_factorial_large_standardized_residual")
    if int(diagnostics["high_cooks_distance_count"]) > 0:
        warnings.append("doe_factorial_influential_run_detected")
    return warnings


def _block_levels(runs: Sequence[FactorialAnalysisRun]) -> list[int]:
    levels = sorted({run.block_index for run in runs if run.block_index is not None})
    return levels or [1]
