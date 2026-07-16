from __future__ import annotations

import hashlib
import json
import random
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations, product
from math import isfinite, sqrt
from typing import Any, Final, Literal

import numpy as np
from scipy import stats  # type: ignore[import-untyped]

RESPONSE_SURFACE_LEGACY_DESIGN_SCHEMA_VERSION: Final[Literal[1]] = 1
RESPONSE_SURFACE_DESIGN_SCHEMA_VERSION: Final[Literal[2]] = 2
RESPONSE_SURFACE_RESULT_SCHEMA_VERSION = 1
RESPONSE_SURFACE_FAMILY: Final[Literal["central_composite"]] = "central_composite"
RESPONSE_SURFACE_LEGACY_FAMILY: Final[Literal["central_composite_inscribed"]] = (
    "central_composite_inscribed"
)
MIN_RESPONSE_SURFACE_FACTORS = 2
MAX_RESPONSE_SURFACE_FACTORS = 5
MAX_RESPONSE_SURFACE_RUNS = 256
MAX_RESPONSE_SURFACE_POINTS = 256
DEFAULT_CONTOUR_GRID_SIZE = 21


class ResponseSurfaceError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ResponseSurfaceFactor:
    name: str
    low: float
    high: float
    unit: str | None = None


@dataclass(frozen=True)
class ResponseSurfaceDesignOptions:
    alpha_mode: Literal["rotatable", "face_centered"]
    factorial_replicates: int
    axial_replicates: int
    center_points: int
    randomize: bool
    randomization_seed: int


@dataclass(frozen=True)
class ResponseSurfaceDesignRun:
    standard_order: int
    run_order: int
    replicate_index: int
    point_type: Literal["factorial", "axial", "center"]
    center_point: bool
    factor_levels: dict[str, float]
    coded_levels: dict[str, float]


@dataclass(frozen=True)
class ResponseSurfaceDesign:
    schema_version: int
    family: str
    alpha: float
    factors: tuple[ResponseSurfaceFactor, ...]
    options: ResponseSurfaceDesignOptions
    runs: tuple[ResponseSurfaceDesignRun, ...]
    design_sha256: str


@dataclass(frozen=True)
class ResponseSurfaceAnalysisRun:
    run_order: int
    standard_order: int
    point_type: Literal["factorial", "axial", "center"]
    coded_levels: dict[str, float]
    response: float


@dataclass(frozen=True)
class _Term:
    term_id: str
    label: str
    kind: Literal["intercept", "main_effect", "interaction", "quadratic"]
    factor_names: tuple[str, ...]
    values: np.ndarray


def generate_central_composite_design(
    factors: list[ResponseSurfaceFactor],
    options: ResponseSurfaceDesignOptions,
) -> ResponseSurfaceDesign:
    _validate_design_inputs(factors, options)
    factor_count = len(factors)
    alpha = (2**factor_count) ** 0.25 if options.alpha_mode == "rotatable" else 1.0
    run_count = (
        (2**factor_count) * options.factorial_replicates
        + (2 * factor_count) * options.axial_replicates
        + options.center_points
    )
    if run_count > MAX_RESPONSE_SURFACE_RUNS:
        raise ResponseSurfaceError("doe_rsm_run_count_exceeds_limit")

    rows: list[ResponseSurfaceDesignRun] = []
    standard_order = 1
    for replicate_index in range(1, options.factorial_replicates + 1):
        for levels in product((-1.0, 1.0), repeat=factor_count):
            coded = dict(zip((factor.name for factor in factors), levels, strict=True))
            rows.append(
                _design_run(
                    factors=factors,
                    alpha=alpha,
                    standard_order=standard_order,
                    replicate_index=replicate_index,
                    point_type="factorial",
                    coded_levels=coded,
                )
            )
            standard_order += 1

    for replicate_index in range(1, options.axial_replicates + 1):
        for factor in factors:
            for level in (-alpha, alpha):
                coded = {item.name: 0.0 for item in factors}
                coded[factor.name] = level
                rows.append(
                    _design_run(
                        factors=factors,
                        alpha=alpha,
                        standard_order=standard_order,
                        replicate_index=replicate_index,
                        point_type="axial",
                        coded_levels=coded,
                    )
                )
                standard_order += 1

    for replicate_index in range(1, options.center_points + 1):
        rows.append(
            _design_run(
                factors=factors,
                alpha=alpha,
                standard_order=standard_order,
                replicate_index=replicate_index,
                point_type="center",
                coded_levels={factor.name: 0.0 for factor in factors},
            )
        )
        standard_order += 1

    order = list(range(len(rows)))
    if options.randomize:
        random.Random(options.randomization_seed).shuffle(order)
    ordered = [rows[index] for index in order]
    runs = tuple(
        ResponseSurfaceDesignRun(
            standard_order=run.standard_order,
            run_order=run_order,
            replicate_index=run.replicate_index,
            point_type=run.point_type,
            center_point=run.center_point,
            factor_levels=run.factor_levels,
            coded_levels=run.coded_levels,
        )
        for run_order, run in enumerate(ordered, start=1)
    )
    payload = canonical_response_surface_design_payload(
        family=RESPONSE_SURFACE_FAMILY,
        alpha=alpha,
        factors=factors,
        options=options,
        runs=runs,
    )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return ResponseSurfaceDesign(
        schema_version=RESPONSE_SURFACE_DESIGN_SCHEMA_VERSION,
        family=RESPONSE_SURFACE_FAMILY,
        alpha=alpha,
        factors=tuple(factors),
        options=options,
        runs=runs,
        design_sha256=hashlib.sha256(encoded).hexdigest(),
    )


def canonical_response_surface_design_payload(
    *,
    schema_version: int = RESPONSE_SURFACE_DESIGN_SCHEMA_VERSION,
    family: str,
    alpha: float,
    factors: Sequence[ResponseSurfaceFactor],
    options: ResponseSurfaceDesignOptions,
    runs: Sequence[ResponseSurfaceDesignRun],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "family": family,
        "alpha": alpha,
        "factors": [response_surface_factor_payload(factor) for factor in factors],
        "options": response_surface_options_payload(options),
        "runs": [
            response_surface_run_payload(run)
            for run in sorted(runs, key=lambda item: item.run_order)
        ],
    }


def response_surface_factor_payload(factor: ResponseSurfaceFactor) -> dict[str, Any]:
    return {"name": factor.name, "low": factor.low, "high": factor.high, "unit": factor.unit}


def response_surface_options_payload(options: ResponseSurfaceDesignOptions) -> dict[str, Any]:
    return {
        "alpha_mode": options.alpha_mode,
        "factorial_replicates": options.factorial_replicates,
        "axial_replicates": options.axial_replicates,
        "center_points": options.center_points,
        "randomize": options.randomize,
        "randomization_seed": options.randomization_seed,
    }


def response_surface_run_payload(run: ResponseSurfaceDesignRun) -> dict[str, Any]:
    return {
        "standard_order": run.standard_order,
        "run_order": run.run_order,
        "replicate_index": run.replicate_index,
        "point_type": run.point_type,
        "center_point": run.center_point,
        "factor_levels": run.factor_levels,
        "coded_levels": run.coded_levels,
    }


def calculate_response_surface_analysis(
    runs: Sequence[ResponseSurfaceAnalysisRun],
    factors: Sequence[ResponseSurfaceFactor],
    *,
    alpha: float,
    response_name: str,
    response_unit: str | None,
    confidence_level: float = 0.95,
    point_limit: int = MAX_RESPONSE_SURFACE_POINTS,
    contour_grid_size: int = DEFAULT_CONTOUR_GRID_SIZE,
) -> dict[str, object]:
    factor_names = [factor.name for factor in factors]
    _validate_analysis_inputs(
        runs,
        factor_names,
        alpha=alpha,
        confidence_level=confidence_level,
        point_limit=point_limit,
        contour_grid_size=contour_grid_size,
    )
    ordered_runs = sorted(runs, key=lambda run: run.run_order)
    response = np.asarray([run.response for run in ordered_runs], dtype=float)
    if bool(np.all(response == response[0])):
        raise ResponseSurfaceError("doe_rsm_response_variance_zero")

    terms = _quadratic_terms(ordered_runs, factor_names)
    matrix = np.column_stack([term.values for term in terms])
    rank = int(np.linalg.matrix_rank(matrix))
    if rank != matrix.shape[1]:
        raise ResponseSurfaceError("doe_rsm_model_rank_deficient")

    coefficients, fitted, residuals, sse = _fit(matrix, response)
    n_observations = len(ordered_runs)
    parameter_count = matrix.shape[1]
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
        residual_ms * np.linalg.inv(matrix.T @ matrix)
        if residual_ms is not None and residual_ms > 0
        else None
    )
    t_critical = (
        float(stats.t.ppf(0.5 + confidence_level / 2.0, df_residual)) if df_residual > 0 else None
    )
    term_results = _term_results(
        terms,
        matrix,
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
        matrix,
        response,
        fitted,
        residuals,
        sse=sse,
        df_residual=df_residual,
        point_limit=point_limit,
    )
    stationary = _stationary_point(coefficients, terms, factors, alpha=alpha)
    contour = _contour_grid(
        coefficients,
        terms,
        factors,
        alpha=alpha,
        grid_size=contour_grid_size,
    )
    warnings = _analysis_warnings(
        df_residual=df_residual,
        residual_ms=residual_ms,
        lack_of_fit=lack_of_fit,
        diagnostics=diagnostics,
        stationary=stationary,
        factor_count=len(factors),
    )
    r_squared = model_ss / total_ss
    adjusted_r_squared = (
        1.0 - ((sse / df_residual) / (total_ss / (n_observations - 1))) if df_residual > 0 else None
    )
    point_counts = {
        point_type: sum(run.point_type == point_type for run in ordered_runs)
        for point_type in ("factorial", "axial", "center")
    }
    return {
        "schema_version": RESPONSE_SURFACE_RESULT_SCHEMA_VERSION,
        "summary_type": "response_surface_analysis",
        "method": "full_quadratic_ordinary_least_squares",
        "response": {"name": response_name, "unit": response_unit},
        "factor_names": factor_names,
        "coding": {
            "center": 0.0,
            "factorial_low": -1.0,
            "factorial_high": 1.0,
            "axial_distance": alpha,
            "actual_bounds_are_axial_bounds": True,
        },
        "model_policy": {
            "full_quadratic": True,
            "automatic_term_selection": False,
            "hierarchy_enforced": True,
            "sum_of_squares": "partial_drop_one",
            "contour_other_factors_held_at_center": True,
        },
        "sample": {
            "n_observations": n_observations,
            "factorial_point_count": point_counts["factorial"],
            "axial_point_count": point_counts["axial"],
            "center_point_count": point_counts["center"],
            "unique_design_point_count": lack_of_fit["unique_design_point_count"],
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
        "stationary_point": stationary,
        "contour": contour,
        "diagnostics": diagnostics,
        "warnings": warnings,
    }


def _validate_design_inputs(
    factors: Sequence[ResponseSurfaceFactor], options: ResponseSurfaceDesignOptions
) -> None:
    if not MIN_RESPONSE_SURFACE_FACTORS <= len(factors) <= MAX_RESPONSE_SURFACE_FACTORS:
        raise ResponseSurfaceError("doe_rsm_factor_count_out_of_range")
    seen: set[str] = set()
    for factor in factors:
        name = factor.name.strip()
        if not name:
            raise ResponseSurfaceError("doe_rsm_factor_name_required")
        normalized = name.casefold()
        if normalized in seen:
            raise ResponseSurfaceError("doe_rsm_factor_names_not_unique")
        seen.add(normalized)
        if not isfinite(factor.low) or not isfinite(factor.high) or factor.low >= factor.high:
            raise ResponseSurfaceError("doe_rsm_factor_range_invalid")
    if options.alpha_mode not in {"rotatable", "face_centered"}:
        raise ResponseSurfaceError("doe_rsm_alpha_mode_invalid")
    if options.factorial_replicates < 1 or options.axial_replicates < 1:
        raise ResponseSurfaceError("doe_rsm_replicates_invalid")
    if options.center_points < 1:
        raise ResponseSurfaceError("doe_rsm_center_points_invalid")
    if options.randomization_seed < 0:
        raise ResponseSurfaceError("doe_rsm_seed_invalid")


def _design_run(
    *,
    factors: Sequence[ResponseSurfaceFactor],
    alpha: float,
    standard_order: int,
    replicate_index: int,
    point_type: Literal["factorial", "axial", "center"],
    coded_levels: dict[str, float],
) -> ResponseSurfaceDesignRun:
    factor_levels = {
        factor.name: _coded_to_actual(factor, coded_levels[factor.name], alpha)
        for factor in factors
    }
    return ResponseSurfaceDesignRun(
        standard_order=standard_order,
        run_order=0,
        replicate_index=replicate_index,
        point_type=point_type,
        center_point=point_type == "center",
        factor_levels=factor_levels,
        coded_levels=coded_levels,
    )


def _coded_to_actual(factor: ResponseSurfaceFactor, coded: float, alpha: float) -> float:
    midpoint = (factor.low + factor.high) / 2.0
    half_range = (factor.high - factor.low) / 2.0
    return float(midpoint + (coded / alpha) * half_range)


def _validate_analysis_inputs(
    runs: Sequence[ResponseSurfaceAnalysisRun],
    factor_names: Sequence[str],
    *,
    alpha: float,
    confidence_level: float,
    point_limit: int,
    contour_grid_size: int,
) -> None:
    if not MIN_RESPONSE_SURFACE_FACTORS <= len(factor_names) <= MAX_RESPONSE_SURFACE_FACTORS:
        raise ResponseSurfaceError("doe_rsm_analysis_factors_invalid")
    if len(set(factor_names)) != len(factor_names):
        raise ResponseSurfaceError("doe_rsm_analysis_factors_invalid")
    if not isfinite(alpha) or alpha < 1.0:
        raise ResponseSurfaceError("doe_rsm_alpha_invalid")
    if not isfinite(confidence_level) or not 0 < confidence_level < 1:
        raise ResponseSurfaceError("doe_rsm_confidence_level_invalid")
    if not 1 <= point_limit <= MAX_RESPONSE_SURFACE_POINTS:
        raise ResponseSurfaceError("doe_rsm_point_limit_invalid")
    if not 11 <= contour_grid_size <= 51 or contour_grid_size % 2 == 0:
        raise ResponseSurfaceError("doe_rsm_contour_grid_size_invalid")
    if not 1 <= len(runs) <= MAX_RESPONSE_SURFACE_RUNS:
        raise ResponseSurfaceError("doe_rsm_run_count_invalid")
    if len({run.run_order for run in runs}) != len(runs):
        raise ResponseSurfaceError("doe_rsm_run_order_duplicate")
    expected = set(factor_names)
    for run in runs:
        if not isfinite(run.response):
            raise ResponseSurfaceError("doe_rsm_response_not_finite")
        if run.point_type not in {"factorial", "axial", "center"}:
            raise ResponseSurfaceError("doe_rsm_point_type_invalid")
        if set(run.coded_levels) != expected or any(
            not isfinite(value) or abs(value) > alpha + 1e-10 for value in run.coded_levels.values()
        ):
            raise ResponseSurfaceError("doe_rsm_coded_levels_invalid")


def _quadratic_terms(
    runs: Sequence[ResponseSurfaceAnalysisRun], factor_names: Sequence[str]
) -> list[_Term]:
    terms = [_Term("intercept", "Intercept", "intercept", (), np.ones(len(runs), dtype=float))]
    for index, name in enumerate(factor_names, start=1):
        terms.append(
            _Term(
                f"factor_{index}",
                name,
                "main_effect",
                (name,),
                np.asarray([run.coded_levels[name] for run in runs], dtype=float),
            )
        )
    for (first_index, first), (second_index, second) in combinations(
        enumerate(factor_names, start=1), 2
    ):
        terms.append(
            _Term(
                f"factor_{first_index}:factor_{second_index}",
                f"{first} * {second}",
                "interaction",
                (first, second),
                np.asarray(
                    [run.coded_levels[first] * run.coded_levels[second] for run in runs],
                    dtype=float,
                ),
            )
        )
    for index, name in enumerate(factor_names, start=1):
        terms.append(
            _Term(
                f"factor_{index}^2",
                f"{name}^2",
                "quadratic",
                (name,),
                np.asarray([run.coded_levels[name] ** 2 for run in runs], dtype=float),
            )
        )
    return terms


def _fit(
    matrix: np.ndarray, response: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    coefficients, _, _, _ = np.linalg.lstsq(matrix, response, rcond=None)
    fitted = matrix @ coefficients
    residuals = response - fitted
    return coefficients, fitted, residuals, max(0.0, float(residuals @ residuals))


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
        confidence_interval = (
            {
                "level": confidence_level,
                "lower": float(coefficient - t_critical * standard_error),
                "upper": float(coefficient + t_critical * standard_error),
            }
            if t_critical is not None and standard_error is not None
            else None
        )
        partial_ss = None
        term_f = None
        term_p = None
        if index > 0:
            reduced = np.delete(matrix, index, axis=1)
            _, _, _, reduced_sse = _fit(reduced, response)
            partial_ss = max(0.0, reduced_sse - sse)
            if residual_ms is not None and residual_ms > 0:
                term_f = partial_ss / residual_ms
                term_p = float(stats.f.sf(term_f, 1, df_residual))
        results.append(
            {
                "term_id": term.term_id,
                "label": term.label,
                "kind": term.kind,
                "factor_names": list(term.factor_names),
                "coefficient": float(coefficient),
                "standard_error": standard_error,
                "statistic": statistic,
                "p_value": p_value,
                "confidence_interval": confidence_interval,
                "partial_sum_squares": partial_ss,
                "f_statistic": term_f,
                "f_p_value": term_p,
            }
        )
    return results


def _lack_of_fit(
    runs: Sequence[ResponseSurfaceAnalysisRun],
    response: np.ndarray,
    factor_names: Sequence[str],
    *,
    sse: float,
    df_residual: int,
    parameter_count: int,
) -> dict[str, Any]:
    grouped: dict[tuple[float, ...], list[float]] = defaultdict(list)
    for run, value in zip(runs, response, strict=True):
        grouped[tuple(run.coded_levels[name] for name in factor_names)].append(float(value))
    pure_error_ss = float(
        sum(
            sum((value - float(np.mean(values))) ** 2 for value in values)
            for values in grouped.values()
        )
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
    return {
        "available": pure_error_df > 0 and lack_of_fit_df > 0,
        "unique_design_point_count": len(grouped),
        "pure_error": {
            "df": pure_error_df,
            "sum_squares": float(pure_error_ss),
            "mean_square": pure_error_ms,
        },
        "lack_of_fit": {
            "df": max(0, lack_of_fit_df),
            "sum_squares": float(lack_of_fit_ss),
            "mean_square": lack_of_fit_ms,
            "f_statistic": f_statistic,
            "p_value": p_value,
        },
        "residual_df": df_residual,
    }


def _diagnostics(
    runs: Sequence[ResponseSurfaceAnalysisRun],
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
            standardized_value**2
            * float(hat)
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
    return {
        "residual_mean": float(np.mean(residuals)),
        "residual_min": float(np.min(residuals)),
        "residual_max": float(np.max(residuals)),
        "max_abs_standardized_residual": max(
            (abs(value) for value in standardized if value is not None), default=None
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
        "durbin_watson": (
            float(np.sum(np.diff(residuals) ** 2) / sse) if len(residuals) > 1 and sse > 0 else None
        ),
        "shapiro_wilk": {"statistic": shapiro_statistic, "p_value": shapiro_p_value},
        "point_limit": point_limit,
        "points_truncated": len(runs) > point_limit,
        "points": [
            {
                "run_order": run.run_order,
                "standard_order": run.standard_order,
                "point_type": run.point_type,
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
        ][:point_limit],
        "qq_points": [
            {"theoretical": float(x), "ordered_residual": float(y)}
            for x, y in zip(theoretical[:point_limit], ordered[:point_limit], strict=True)
        ],
    }


def _stationary_point(
    coefficients: np.ndarray,
    terms: Sequence[_Term],
    factors: Sequence[ResponseSurfaceFactor],
    *,
    alpha: float,
) -> dict[str, Any]:
    factor_names = [factor.name for factor in factors]
    index_by_id = {term.term_id: index for index, term in enumerate(terms)}
    linear = np.asarray(
        [coefficients[index_by_id[f"factor_{index}"]] for index in range(1, len(factors) + 1)]
    )
    hessian = np.zeros((len(factors), len(factors)), dtype=float)
    for index in range(1, len(factors) + 1):
        hessian[index - 1, index - 1] = 2.0 * coefficients[index_by_id[f"factor_{index}^2"]]
    for first, second in combinations(range(1, len(factors) + 1), 2):
        value = coefficients[index_by_id[f"factor_{first}:factor_{second}"]]
        hessian[first - 1, second - 1] = value
        hessian[second - 1, first - 1] = value
    rank = int(np.linalg.matrix_rank(hessian))
    eigenvalues = np.linalg.eigvalsh(hessian)
    if rank != len(factors):
        return {
            "available": False,
            "classification": "indeterminate",
            "coded_coordinates": {},
            "actual_coordinates": {},
            "predicted_response": None,
            "within_axial_bounds": False,
            "within_factorial_cube": False,
            "hessian_eigenvalues": [float(value) for value in eigenvalues],
        }
    coded = np.linalg.solve(hessian, -linear)
    coded_coordinates = dict(zip(factor_names, (float(value) for value in coded), strict=True))
    actual_coordinates = {
        factor.name: _coded_to_actual(factor, coded_coordinates[factor.name], alpha)
        for factor in factors
    }
    if bool(np.all(eigenvalues > 0)):
        classification = "minimum"
    elif bool(np.all(eigenvalues < 0)):
        classification = "maximum"
    else:
        classification = "saddle"
    return {
        "available": True,
        "classification": classification,
        "coded_coordinates": coded_coordinates,
        "actual_coordinates": actual_coordinates,
        "predicted_response": _predict(coefficients, terms, coded_coordinates),
        "within_axial_bounds": all(abs(value) <= alpha + 1e-10 for value in coded),
        "within_factorial_cube": all(abs(value) <= 1.0 + 1e-10 for value in coded),
        "hessian_eigenvalues": [float(value) for value in eigenvalues],
    }


def _contour_grid(
    coefficients: np.ndarray,
    terms: Sequence[_Term],
    factors: Sequence[ResponseSurfaceFactor],
    *,
    alpha: float,
    grid_size: int,
) -> dict[str, Any]:
    x_factor, y_factor = factors[0], factors[1]
    held = {factor.name: 0.0 for factor in factors[2:]}
    grid = np.linspace(-1.0, 1.0, grid_size)
    points: list[dict[str, float]] = []
    for y_coded in grid:
        for x_coded in grid:
            coded = {factor.name: 0.0 for factor in factors}
            coded[x_factor.name] = float(x_coded)
            coded[y_factor.name] = float(y_coded)
            points.append(
                {
                    "x_coded": float(x_coded),
                    "y_coded": float(y_coded),
                    "x_actual": _coded_to_actual(x_factor, float(x_coded), alpha),
                    "y_actual": _coded_to_actual(y_factor, float(y_coded), alpha),
                    "predicted": _predict(coefficients, terms, coded),
                }
            )
    return {
        "x_factor": x_factor.name,
        "y_factor": y_factor.name,
        "held_coded_levels": held,
        "grid_size": grid_size,
        "coded_range": [-1.0, 1.0],
        "points": points,
    }


def _predict(coefficients: np.ndarray, terms: Sequence[_Term], coded: dict[str, float]) -> float:
    values: list[float] = []
    for term in terms:
        if term.kind == "intercept":
            values.append(1.0)
        elif term.kind == "main_effect":
            values.append(coded[term.factor_names[0]])
        elif term.kind == "interaction":
            values.append(coded[term.factor_names[0]] * coded[term.factor_names[1]])
        else:
            values.append(coded[term.factor_names[0]] ** 2)
    return float(np.asarray(values) @ coefficients)


def _analysis_warnings(
    *,
    df_residual: int,
    residual_ms: float | None,
    lack_of_fit: dict[str, Any],
    diagnostics: dict[str, Any],
    stationary: dict[str, Any],
    factor_count: int,
) -> list[str]:
    warnings = [
        "doe_rsm_randomization_and_independence_not_proven",
        "doe_rsm_model_is_associational_not_causal",
        "doe_rsm_predictions_are_limited_to_declared_design_region",
    ]
    if factor_count > 2:
        warnings.append("doe_rsm_contour_holds_other_factors_at_center")
    if df_residual == 0:
        warnings.append("doe_rsm_model_saturated_no_inference")
    elif df_residual < 5:
        warnings.append("doe_rsm_residual_df_small")
    if residual_ms is not None and residual_ms <= np.finfo(float).eps:
        warnings.append("doe_rsm_residual_variance_zero")
    pure_error = lack_of_fit["pure_error"]
    lack_of_fit_row = lack_of_fit["lack_of_fit"]
    if isinstance(pure_error, dict) and int(pure_error["df"]) == 0:
        warnings.append("doe_rsm_pure_error_unavailable_without_replication")
    if isinstance(lack_of_fit_row, dict) and int(lack_of_fit_row["df"]) == 0:
        warnings.append("doe_rsm_lack_of_fit_df_unavailable")
    if not bool(stationary["available"]):
        warnings.append("doe_rsm_stationary_point_indeterminate")
    elif not bool(stationary["within_axial_bounds"]):
        warnings.append("doe_rsm_stationary_point_outside_design_region")
    elif not bool(stationary["within_factorial_cube"]):
        warnings.append("doe_rsm_stationary_point_outside_factorial_cube")
    if int(diagnostics["high_standardized_residual_count"]) > 0:
        warnings.append("doe_rsm_large_standardized_residual")
    if int(diagnostics["high_cooks_distance_count"]) > 0:
        warnings.append("doe_rsm_influential_run_detected")
    return warnings
