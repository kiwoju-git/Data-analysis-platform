from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations, product
from math import isfinite, sqrt
from typing import Any

import numpy as np
from scipy import stats  # type: ignore[import-untyped]


class GeneralFactorialAnalysisError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class GeneralFactorialAnalysisRun:
    run_order: int
    level_indices: dict[str, int]
    factor_levels: dict[str, float | str]
    response: float


@dataclass(frozen=True)
class _TermBlock:
    term_id: str
    label: str
    factor_names: tuple[str, ...]
    columns: np.ndarray


def calculate_general_factorial_analysis(
    runs: Sequence[GeneralFactorialAnalysisRun],
    factor_levels: dict[str, Sequence[float | str]],
    *,
    response_name: str,
    response_unit: str | None,
    max_interaction_order: int,
) -> dict[str, Any]:
    factor_names = tuple(factor_levels)
    _validate(runs, factor_levels, max_interaction_order)
    ordered = sorted(runs, key=lambda item: item.run_order)
    y = np.asarray([item.response for item in ordered], dtype=float)
    if bool(np.all(y == y[0])):
        raise GeneralFactorialAnalysisError("doe_general_factorial_response_variance_zero")

    blocks = _term_blocks(ordered, factor_levels, max_interaction_order)
    intercept = np.ones((len(ordered), 1), dtype=float)
    matrix = np.column_stack([intercept, *(block.columns for block in blocks)])
    rank = int(np.linalg.matrix_rank(matrix))
    if rank != matrix.shape[1]:
        raise GeneralFactorialAnalysisError("doe_general_factorial_model_rank_deficient")
    coefficients, fitted, residuals, sse = _fit(matrix, y)
    n = len(ordered)
    df_residual = n - rank
    residual_ms = sse / df_residual if df_residual > 0 else None
    mean = float(np.mean(y))
    total_ss = float(np.sum((y - mean) ** 2))
    model_ss = max(0.0, total_ss - sse)
    df_model = rank - 1
    model_ms = model_ss / df_model if df_model > 0 else None
    model_f = (
        model_ms / residual_ms
        if model_ms is not None and residual_ms is not None and residual_ms > 0
        else None
    )
    model_p = float(stats.f.sf(model_f, df_model, df_residual)) if model_f is not None else None

    rows: list[dict[str, Any]] = []
    offset = 1
    for block in blocks:
        width = block.columns.shape[1]
        keep = [index for index in range(matrix.shape[1]) if not offset <= index < offset + width]
        reduced = matrix[:, keep]
        reduced_rank = int(np.linalg.matrix_rank(reduced))
        _coef, _fit_values, _residuals, reduced_sse = _fit(reduced, y)
        df = rank - reduced_rank
        adjusted_ss = max(0.0, reduced_sse - sse)
        adjusted_ms = adjusted_ss / df if df > 0 else None
        statistic = (
            adjusted_ms / residual_ms
            if adjusted_ms is not None and residual_ms is not None and residual_ms > 0
            else None
        )
        p_value = float(stats.f.sf(statistic, df, df_residual)) if statistic is not None else None
        rows.append(
            {
                "source": block.label,
                "term_id": block.term_id,
                "factor_names": list(block.factor_names),
                "df": df,
                "adjusted_sum_squares": adjusted_ss,
                "adjusted_mean_square": adjusted_ms,
                "f_statistic": statistic,
                "p_value": p_value,
            }
        )
        offset += width

    pure_error = _pure_error(ordered)
    lack_of_fit = _lack_of_fit(sse, df_residual, pure_error)
    leverage = np.diag(matrix @ np.linalg.inv(matrix.T @ matrix) @ matrix.T)
    standardizer = sqrt(residual_ms) if residual_ms is not None and residual_ms > 0 else None
    diagnostic_points = [
        {
            "run_order": run.run_order,
            "observed": float(observed),
            "fitted": float(fit),
            "residual": float(residual),
            "standardized_residual": (
                float(residual / (standardizer * sqrt(max(1.0 - float(h), 1e-12))))
                if standardizer is not None
                else None
            ),
            "leverage": float(h),
        }
        for run, observed, fit, residual, h in zip(
            ordered, y, fitted, residuals, leverage, strict=True
        )
    ]
    group_means = _group_means(ordered, factor_names)
    warnings: list[str] = [
        "Numeric factor levels are analyzed as categorical levels in a general factorial model."
    ]
    if df_residual <= 0:
        warnings.append(
            "Residual degrees of freedom are zero; inferential statistics are unavailable."
        )
    if not lack_of_fit["available"]:
        warnings.append(str(lack_of_fit["reason"]))

    return {
        "schema_version": 1,
        "summary_type": "general_factorial_analysis",
        "method": "categorical_treatment_coding_partial_f_tests",
        "response": {"name": response_name, "unit": response_unit},
        "factor_names": list(factor_names),
        "coding": {
            "policy": "treatment",
            "reference_levels": {name: factor_levels[name][0] for name in factor_names},
        },
        "model_policy": {
            "max_interaction_order": max_interaction_order,
            "automatic_term_selection": False,
            "sum_of_squares": "partial_drop_term_block",
        },
        "sample": {
            "n_observations": n,
            "parameter_count": rank,
            "rank": rank,
            "df_model": df_model,
            "df_residual": df_residual,
        },
        "fit": {
            "response_mean": mean,
            "sse": sse,
            "model_ss": model_ss,
            "total_ss": total_ss,
            "residual_mean_square": residual_ms,
            "residual_standard_error": sqrt(residual_ms) if residual_ms is not None else None,
            "r_squared": model_ss / total_ss,
            "adjusted_r_squared": (
                1.0 - ((sse / df_residual) / (total_ss / (n - 1))) if df_residual > 0 else None
            ),
            "f_statistic": model_f,
            "f_p_value": model_p,
        },
        "coefficients": [float(value) for value in coefficients],
        "anova": {
            "rows": rows,
            "model": {
                "df": df_model,
                "sum_squares": model_ss,
                "mean_square": model_ms,
                "f_statistic": model_f,
                "p_value": model_p,
            },
            "residual": {"df": df_residual, "sum_squares": sse, "mean_square": residual_ms},
            "total": {"df": n - 1, "sum_squares": total_ss},
            "pure_error": pure_error,
            "lack_of_fit": lack_of_fit,
        },
        "group_means": group_means,
        "diagnostics": {"points": diagnostic_points},
        "warnings": warnings,
    }


def _validate(
    runs: Sequence[GeneralFactorialAnalysisRun],
    factor_levels: dict[str, Sequence[float | str]],
    max_interaction_order: int,
) -> None:
    if len(factor_levels) < 2 or not 1 <= max_interaction_order <= min(3, len(factor_levels)):
        raise GeneralFactorialAnalysisError("doe_general_factorial_analysis_config_invalid")
    if len(runs) < 2 or len({run.run_order for run in runs}) != len(runs):
        raise GeneralFactorialAnalysisError("doe_general_factorial_analysis_runs_invalid")
    for run in runs:
        if not isfinite(run.response) or set(run.level_indices) != set(factor_levels):
            raise GeneralFactorialAnalysisError("doe_general_factorial_analysis_runs_invalid")
        for name, index in run.level_indices.items():
            if index < 0 or index >= len(factor_levels[name]):
                raise GeneralFactorialAnalysisError("doe_general_factorial_analysis_runs_invalid")


def _term_blocks(
    runs: Sequence[GeneralFactorialAnalysisRun],
    factor_levels: dict[str, Sequence[float | str]],
    max_interaction_order: int,
) -> list[_TermBlock]:
    factor_names = tuple(factor_levels)
    main_columns: dict[str, np.ndarray] = {}
    for name in factor_names:
        main_columns[name] = np.column_stack(
            [
                np.asarray([float(run.level_indices[name] == index) for run in runs])
                for index in range(1, len(factor_levels[name]))
            ]
        )
    blocks: list[_TermBlock] = []
    for order in range(1, max_interaction_order + 1):
        for names in combinations(factor_names, order):
            columns = main_columns[names[0]]
            for name in names[1:]:
                column_pairs = product(
                    range(columns.shape[1]),
                    range(main_columns[name].shape[1]),
                )
                columns = np.column_stack(
                    [
                        columns[:, left] * main_columns[name][:, right]
                        for left, right in column_pairs
                    ]
                )
            blocks.append(
                _TermBlock(
                    term_id=":".join(names),
                    label=" * ".join(names),
                    factor_names=names,
                    columns=columns,
                )
            )
    return blocks


def _fit(
    matrix: np.ndarray, response: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    coefficients, *_ = np.linalg.lstsq(matrix, response, rcond=None)
    fitted = matrix @ coefficients
    residuals = response - fitted
    return coefficients, fitted, residuals, float(residuals @ residuals)


def _pure_error(runs: Sequence[GeneralFactorialAnalysisRun]) -> dict[str, Any]:
    grouped: dict[tuple[tuple[str, int], ...], list[float]] = {}
    for run in runs:
        key = tuple(sorted(run.level_indices.items()))
        grouped.setdefault(key, []).append(run.response)
    ss = 0.0
    df = 0
    for values in grouped.values():
        if len(values) < 2:
            continue
        mean = float(np.mean(values))
        ss += sum((value - mean) ** 2 for value in values)
        df += len(values) - 1
    return {"df": df, "sum_squares": ss, "mean_square": ss / df if df > 0 else None}


def _lack_of_fit(sse: float, df_residual: int, pure_error: dict[str, Any]) -> dict[str, Any]:
    pure_df = int(pure_error["df"])
    pure_ms = pure_error["mean_square"]
    df = df_residual - pure_df
    if pure_df <= 0 or df <= 0 or pure_ms is None or float(pure_ms) <= 0:
        return {
            "available": False,
            "reason": (
                "Repeated factor combinations are insufficient to separate pure error "
                "and lack of fit."
            ),
            "df": max(df, 0),
            "sum_squares": None,
            "mean_square": None,
            "f_statistic": None,
            "p_value": None,
        }
    ss = max(0.0, sse - float(pure_error["sum_squares"]))
    ms = ss / df
    statistic = ms / float(pure_ms)
    return {
        "available": True,
        "reason": None,
        "df": df,
        "sum_squares": ss,
        "mean_square": ms,
        "f_statistic": statistic,
        "p_value": float(stats.f.sf(statistic, df, pure_df)),
    }


def _group_means(
    runs: Sequence[GeneralFactorialAnalysisRun], factor_names: Sequence[str]
) -> list[dict[str, Any]]:
    grouped: dict[tuple[tuple[str, str], ...], list[float]] = {}
    raw_values: dict[tuple[tuple[str, str], ...], dict[str, float | str]] = {}
    for run in runs:
        key = tuple((name, str(run.factor_levels[name])) for name in factor_names)
        grouped.setdefault(key, []).append(run.response)
        raw_values[key] = {name: run.factor_levels[name] for name in factor_names}
    return [
        {"levels": raw_values[key], "n": len(values), "mean": float(np.mean(values))}
        for key, values in grouped.items()
    ]
