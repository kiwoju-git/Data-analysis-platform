from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite, log, pi, sqrt
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy import stats  # type: ignore[import-untyped]

from app.statistics.linear_model_columns import classify_linear_model_predictor

MIN_RESIDUAL_DF = 1
CONDITION_NUMBER_WARNING_THRESHOLD = 30.0
VIF_WARNING_THRESHOLD = 5.0
STANDARDIZED_RESIDUAL_WARNING_THRESHOLD = 3.0
DIAGNOSTIC_POINT_LIMIT = 500
MAX_CATEGORICAL_LEVELS = 25
PRESS_LEVERAGE_TOLERANCE = 1e-10
MODEL_SELECTION_TIE_TOLERANCE = 1e-12
FloatArray = NDArray[np.float64]


class LinearModelError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class LinearModelColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class _ParsedCell:
    missing: bool
    non_numeric: bool
    value: float | str | None


@dataclass(frozen=True)
class _ParsedRows:
    n_total: int
    n_excluded_missing: int
    n_excluded_non_numeric: int
    y_values: list[float]
    x_rows: list[list[float | str]]
    row_indices: list[int]


@dataclass(frozen=True)
class _CoefficientTerm:
    term: str
    term_kind: str
    column: LinearModelColumn | None
    source_columns: tuple[LinearModelColumn, ...] = ()
    level: str | None = None
    reference_level: str | None = None
    coding: str | None = None


@dataclass(frozen=True)
class _InteractionTerm:
    left_column_id: str
    right_column_id: str


@dataclass(frozen=True)
class _DesignMatrix:
    design: FloatArray
    predictors: FloatArray
    coefficient_terms: list[_CoefficientTerm]
    model_terms: list[dict[str, object]]
    df_model: int
    parameter_count: int
    categorical_predictor_count: int
    interaction_term_count: int
    quadratic_term_count: int


@dataclass(frozen=True)
class _TermBlock:
    block_id: str
    term: str
    kind: str
    source_column_ids: tuple[str, ...]
    column_indices: tuple[int, ...]
    model_term: dict[str, object]
    initial_order: int


@dataclass(frozen=True)
class _OlsFit:
    design: FloatArray
    coefficients: FloatArray
    fitted: FloatArray
    residuals: FloatArray
    sse: float
    tss: float
    ssr: float
    mse: float
    residual_df: int
    df_model: int
    rank: int
    parameter_count: int
    xtx_inverse: FloatArray
    covariance_matrix: FloatArray
    r_squared: float
    adjusted_r_squared: float
    residual_standard_error: float
    f_statistic: float | None
    f_p_value: float | None
    leverage: FloatArray
    press: float | None
    predicted_r_squared: float | None


def calculate_linear_model(
    rows: Iterable[Sequence[str | None]],
    response_column: LinearModelColumn,
    predictor_columns: Sequence[LinearModelColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    alpha: float = 0.05,
    confidence_level: float = 0.95,
    interaction_terms: Sequence[tuple[str, str]] | None = None,
    quadratic_terms: Sequence[str] | None = None,
    model_selection_method: str = "none",
    alpha_to_remove: float = 0.10,
    hierarchy_policy: str = "strong",
) -> dict[str, object]:
    if alpha <= 0.0 or alpha >= 1.0:
        raise LinearModelError("invalid_linear_model_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise LinearModelError("invalid_linear_model_confidence_level")
    if not predictor_columns:
        raise LinearModelError("linear_model_predictors_required")
    if model_selection_method not in {"none", "backward_elimination"}:
        raise LinearModelError("invalid_linear_model_selection_method")
    if not 0.0 < alpha_to_remove < 1.0:
        raise LinearModelError("invalid_linear_model_alpha_to_remove")
    if hierarchy_policy != "strong":
        raise LinearModelError("invalid_linear_model_hierarchy_policy")

    parsed = _parse_rows(
        rows,
        response_column=response_column,
        predictor_columns=predictor_columns,
        decimal=decimal,
        thousands=thousands,
    )
    y_values = parsed.y_values
    x_rows = parsed.x_rows

    n_used = len(y_values)
    initial_design_matrix = _build_design_matrix(
        x_rows,
        predictor_columns,
        interaction_terms=interaction_terms or (),
        quadratic_terms=quadratic_terms or (),
    )
    if min(y_values) == max(y_values):
        raise LinearModelError("linear_model_response_constant")

    y: FloatArray = np.asarray(y_values, dtype=float)
    initial_fit = _fit_ols(initial_design_matrix.design, y)
    term_blocks = _term_blocks(initial_design_matrix)
    design_matrix, fit, model_selection = _select_linear_model(
        initial_design_matrix=initial_design_matrix,
        initial_fit=initial_fit,
        term_blocks=term_blocks,
        y=y,
        method=model_selection_method,
        alpha_to_remove=alpha_to_remove,
        hierarchy_policy=hierarchy_policy,
    )
    standard_errors: FloatArray = np.sqrt(np.diag(fit.covariance_matrix))
    if not np.all(np.isfinite(standard_errors)) or np.any(standard_errors <= 0.0):
        raise LinearModelError("linear_model_standard_error_not_finite")

    t_critical = float(stats.t.ppf(1.0 - ((1.0 - confidence_level) / 2.0), df=fit.residual_df))
    coefficient_rows = _coefficient_payloads(
        fit.coefficients,
        standard_errors,
        response_column=response_column,
        terms=design_matrix.coefficient_terms,
        residual_df=fit.residual_df,
        t_critical=t_critical,
        confidence_level=confidence_level,
        vif_values=_vif_values(design_matrix.predictors),
    )
    condition_number = float(np.linalg.cond(fit.design))
    vif_candidates: list[float] = []
    for coefficient in coefficient_rows:
        vif_value = coefficient.get("vif")
        if isinstance(vif_value, float):
            vif_candidates.append(vif_value)
    max_vif = max(vif_candidates, default=None)
    diagnostics = _diagnostics_payload(
        fitted=fit.fitted,
        residuals=fit.residuals,
        design=fit.design,
        xtx_inverse=fit.xtx_inverse,
        mse=fit.mse,
        parameter_count=fit.parameter_count,
        row_indices=parsed.row_indices,
    )
    residual_plots = _residual_plots_payload(
        fitted=fit.fitted,
        residuals=fit.residuals,
        leverage=fit.leverage,
        mse=fit.mse,
        row_indices=parsed.row_indices,
    )
    anova = _anova_payload(
        y=y,
        fit=fit,
        design_matrix=design_matrix,
        term_blocks=_term_blocks(design_matrix),
        original_predictor_rows=parsed.x_rows,
    )
    equation = _equation_payload(
        response_column=response_column,
        coefficient_rows=coefficient_rows,
    )

    return {
        "schema_version": 5,
        "summary_type": "linear_model",
        "method": (
            "ordinary_least_squares_safe_terms"
            if design_matrix.interaction_term_count > 0 or design_matrix.quadratic_term_count > 0
            else "ordinary_least_squares_main_effects"
            if design_matrix.categorical_predictor_count > 0
            else "ordinary_least_squares_numeric_predictors"
        ),
        "missing_policy": "complete_case",
        "alpha": alpha,
        "confidence_level": confidence_level,
        "package_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "scipy": importlib.metadata.version("scipy"),
        },
        "warnings": _result_warnings(
            n_excluded_missing=parsed.n_excluded_missing,
            n_excluded_non_numeric=parsed.n_excluded_non_numeric,
            condition_number=condition_number,
            max_vif=max_vif,
            diagnostics=diagnostics,
            categorical_predictor_count=design_matrix.categorical_predictor_count,
            interaction_term_count=design_matrix.interaction_term_count,
            quadratic_term_count=design_matrix.quadratic_term_count,
            press_available=fit.press is not None,
            model_selection_method=model_selection_method,
            intercept_only=fit.df_model == 0,
        ),
        "response": _column_payload(response_column),
        "predictors": [_column_payload(column) for column in predictor_columns],
        "model_specification": {
            "intercept": True,
            "terms": design_matrix.model_terms,
        },
        "initial_model_specification": {
            "intercept": True,
            "terms": initial_design_matrix.model_terms,
        },
        "model_selection": model_selection,
        "equation": equation,
        "training_domain": _training_domain_payload(parsed.x_rows, predictor_columns),
        "prediction_basis": {
            "basis_schema_version": 1,
            "coefficient_order": [term.term for term in design_matrix.coefficient_terms],
            "xtx_inverse": [[float(value) for value in row] for row in fit.xtx_inverse.tolist()],
            "sigma_squared": fit.mse,
            "df_residual": fit.residual_df,
        },
        "sample": {
            "n_total": parsed.n_total,
            "n_used": n_used,
            "n_excluded_missing": parsed.n_excluded_missing,
            "n_excluded_non_numeric": parsed.n_excluded_non_numeric,
            "df_model": fit.df_model,
            "df_residual": fit.residual_df,
        },
        "fit": {
            "r_squared": fit.r_squared,
            "adjusted_r_squared": fit.adjusted_r_squared,
            "residual_standard_error": fit.residual_standard_error,
            "sigma_squared": fit.mse,
            "sse": fit.sse,
            "ssr": fit.ssr,
            "tss": fit.tss,
            "f_statistic": fit.f_statistic,
            "f_p_value": fit.f_p_value,
            "press": fit.press,
            "predicted_r_squared": fit.predicted_r_squared,
            "predicted_r_squared_definition": (
                "1 - PRESS / TSS using leave-one-out deleted residuals"
            ),
        },
        "coefficients": coefficient_rows,
        "anova": anova,
        "residual_plots": residual_plots,
        "diagnostics": {
            "rank": fit.rank,
            "parameter_count": fit.parameter_count,
            "condition_number": condition_number,
            "max_vif": max_vif,
            **diagnostics,
        },
    }


def _fit_ols(design: FloatArray, y: FloatArray) -> _OlsFit:
    n_used = int(len(y))
    parameter_count = int(design.shape[1])
    residual_df = n_used - parameter_count
    if residual_df < MIN_RESIDUAL_DF:
        raise LinearModelError("linear_model_residual_df_too_small")
    rank = int(np.linalg.matrix_rank(design))
    if rank < parameter_count:
        raise LinearModelError("linear_model_design_rank_deficient")

    xtx = design.T @ design
    try:
        xtx_inverse: FloatArray = np.asarray(np.linalg.inv(xtx), dtype=float)
    except np.linalg.LinAlgError as exc:
        raise LinearModelError("linear_model_design_rank_deficient") from exc

    coefficients: FloatArray = np.asarray(np.linalg.lstsq(design, y, rcond=None)[0], dtype=float)
    fitted = design @ coefficients
    residuals = y - fitted
    sse = float(np.dot(residuals, residuals))
    if sse <= 0.0 or not isfinite(sse):
        raise LinearModelError("linear_model_residual_variance_zero")

    centered_y = y - float(np.mean(y))
    tss = float(np.dot(centered_y, centered_y))
    if tss <= 0.0 or not isfinite(tss):
        raise LinearModelError("linear_model_response_constant")

    mse = sse / residual_df
    covariance_matrix = xtx_inverse * mse
    ssr = max(0.0, tss - sse)
    df_model = rank - 1
    r_squared = 1.0 - (sse / tss)
    adjusted_r_squared = 1.0 - ((1.0 - r_squared) * ((n_used - 1) / residual_df))
    f_statistic: float | None = None
    f_p_value: float | None = None
    if df_model > 0:
        f_statistic = (ssr / df_model) / mse
        f_p_value = float(stats.f.sf(f_statistic, df_model, residual_df))

    leverage = np.asarray(np.einsum("ij,jk,ik->i", design, xtx_inverse, design), dtype=float)
    leverage = np.clip(leverage, 0.0, 1.0)
    press = _press_value(residuals, leverage)
    predicted_r_squared = None if press is None else 1.0 - (press / tss)
    return _OlsFit(
        design=design,
        coefficients=coefficients,
        fitted=fitted,
        residuals=residuals,
        sse=sse,
        tss=tss,
        ssr=ssr,
        mse=mse,
        residual_df=residual_df,
        df_model=df_model,
        rank=rank,
        parameter_count=parameter_count,
        xtx_inverse=xtx_inverse,
        covariance_matrix=np.asarray(covariance_matrix, dtype=float),
        r_squared=r_squared,
        adjusted_r_squared=adjusted_r_squared,
        residual_standard_error=sqrt(mse),
        f_statistic=f_statistic,
        f_p_value=f_p_value,
        leverage=leverage,
        press=press,
        predicted_r_squared=predicted_r_squared,
    )


def _press_value(residuals: FloatArray, leverage: FloatArray) -> float | None:
    denominators = 1.0 - leverage
    if np.any(denominators <= PRESS_LEVERAGE_TOLERANCE):
        return None
    deleted_residuals = residuals / denominators
    press = float(np.dot(deleted_residuals, deleted_residuals))
    return press if isfinite(press) else None


def _term_blocks(design_matrix: _DesignMatrix) -> list[_TermBlock]:
    blocks: list[_TermBlock] = []
    for initial_order, model_term in enumerate(design_matrix.model_terms):
        kind = str(model_term.get("kind"))
        term = str(model_term.get("term"))
        source_value = model_term.get("source_column_ids")
        if isinstance(source_value, list):
            source_column_ids = tuple(str(value) for value in source_value)
        else:
            column_id = model_term.get("column_id")
            source_column_ids = (str(column_id),) if isinstance(column_id, str) else ()

        column_indices: list[int] = []
        for coefficient_index, coefficient_term in enumerate(
            design_matrix.coefficient_terms[1:],
            start=1,
        ):
            if kind == "categorical_main_effect":
                source_column = coefficient_term.column
                if (
                    coefficient_term.term_kind == "categorical_level"
                    and source_column is not None
                    and source_column.column_id in source_column_ids
                ):
                    column_indices.append(coefficient_index)
            elif (
                coefficient_term.term_kind == kind
                and coefficient_term.term == term
                and tuple(column.column_id for column in coefficient_term.source_columns)
                == source_column_ids
            ):
                column_indices.append(coefficient_index)
        if not column_indices:
            raise LinearModelError("linear_model_term_block_invalid")
        blocks.append(
            _TermBlock(
                block_id=f"{kind}:{'|'.join(source_column_ids)}:{term}",
                term=term,
                kind=kind,
                source_column_ids=source_column_ids,
                column_indices=tuple(column_indices),
                model_term=dict(model_term),
                initial_order=initial_order,
            )
        )
    return blocks


def _select_linear_model(
    *,
    initial_design_matrix: _DesignMatrix,
    initial_fit: _OlsFit,
    term_blocks: Sequence[_TermBlock],
    y: FloatArray,
    method: str,
    alpha_to_remove: float,
    hierarchy_policy: str,
) -> tuple[_DesignMatrix, _OlsFit, dict[str, object]]:
    initial_terms = [block.term for block in term_blocks]
    if method == "none":
        return (
            initial_design_matrix,
            initial_fit,
            {
                "method": "none",
                "alpha_to_remove": alpha_to_remove,
                "hierarchy_policy": hierarchy_policy,
                "tie_break_policy": "later_initial_term_order_within_1e-12",
                "initial_terms": initial_terms,
                "final_terms": initial_terms,
                "stop_reason": "not_requested",
                "steps": [],
            },
        )

    active_blocks = list(term_blocks)
    current_design = initial_design_matrix
    current_fit = initial_fit
    full_model_mse = initial_fit.mse
    steps = [
        _model_selection_step_payload(
            step=0,
            design_matrix=current_design,
            fit=current_fit,
            full_model_mse=full_model_mse,
            removed_term=None,
            removal_p_value=None,
        )
    ]
    stop_reason = "all_remaining_terms_significant"

    while active_blocks:
        candidates: list[tuple[_TermBlock, _DesignMatrix, _OlsFit, float]] = []
        for block in active_blocks:
            if not _term_is_removable(block, active_blocks):
                continue
            reduced_blocks = [candidate for candidate in active_blocks if candidate != block]
            reduced_design = _subset_design_matrix(initial_design_matrix, reduced_blocks)
            reduced_fit = _fit_ols(reduced_design.design, y)
            removal_p_value = _partial_f_removal_p_value(current_fit, reduced_fit)
            candidates.append((block, reduced_design, reduced_fit, removal_p_value))

        if not candidates:
            stop_reason = "hierarchy_protected_terms" if active_blocks else "intercept_only"
            break
        best = candidates[0]
        for candidate in candidates[1:]:
            candidate_p = candidate[3]
            best_p = best[3]
            if candidate_p > best_p + MODEL_SELECTION_TIE_TOLERANCE or (
                abs(candidate_p - best_p) <= MODEL_SELECTION_TIE_TOLERANCE
                and candidate[0].initial_order > best[0].initial_order
            ):
                best = candidate
        if best[3] <= alpha_to_remove:
            stop_reason = "all_remaining_terms_significant"
            break

        removed_block, current_design, current_fit, removal_p_value = best
        active_blocks = [block for block in active_blocks if block != removed_block]
        steps.append(
            _model_selection_step_payload(
                step=len(steps),
                design_matrix=current_design,
                fit=current_fit,
                full_model_mse=full_model_mse,
                removed_term=removed_block.term,
                removal_p_value=removal_p_value,
            )
        )
        if not active_blocks:
            stop_reason = "intercept_only"
            break

    return (
        current_design,
        current_fit,
        {
            "method": "backward_elimination",
            "alpha_to_remove": alpha_to_remove,
            "hierarchy_policy": hierarchy_policy,
            "tie_break_policy": "later_initial_term_order_within_1e-12",
            "initial_terms": initial_terms,
            "final_terms": [block.term for block in active_blocks],
            "stop_reason": stop_reason,
            "steps": steps,
        },
    )


def _term_is_removable(block: _TermBlock, active_blocks: Sequence[_TermBlock]) -> bool:
    if block.kind not in {"numeric_main_effect", "categorical_main_effect"}:
        return True
    source_ids = set(block.source_column_ids)
    for other in active_blocks:
        if other == block:
            continue
        if other.kind in {"numeric_quadratic", "numeric_interaction"} and source_ids.intersection(
            other.source_column_ids
        ):
            return False
    return True


def _subset_design_matrix(
    initial_design_matrix: _DesignMatrix,
    active_blocks: Sequence[_TermBlock],
) -> _DesignMatrix:
    ordered_blocks = sorted(active_blocks, key=lambda block: block.initial_order)
    selected_indices = [0]
    for block in ordered_blocks:
        selected_indices.extend(block.column_indices)
    selected_indices = sorted(set(selected_indices))
    design = np.asarray(initial_design_matrix.design[:, selected_indices], dtype=float)
    coefficient_terms = [
        initial_design_matrix.coefficient_terms[index] for index in selected_indices
    ]
    model_terms = [dict(block.model_term) for block in ordered_blocks]
    return _DesignMatrix(
        design=design,
        predictors=np.asarray(design[:, 1:], dtype=float),
        coefficient_terms=coefficient_terms,
        model_terms=model_terms,
        df_model=max(0, int(design.shape[1]) - 1),
        parameter_count=int(design.shape[1]),
        categorical_predictor_count=sum(
            block.kind == "categorical_main_effect" for block in ordered_blocks
        ),
        interaction_term_count=sum(block.kind == "numeric_interaction" for block in ordered_blocks),
        quadratic_term_count=sum(block.kind == "numeric_quadratic" for block in ordered_blocks),
    )


def _partial_f_removal_p_value(current_fit: _OlsFit, reduced_fit: _OlsFit) -> float:
    df_removed = current_fit.rank - reduced_fit.rank
    if df_removed <= 0:
        raise LinearModelError("linear_model_selection_rank_invalid")
    adjusted_ss = max(0.0, reduced_fit.sse - current_fit.sse)
    f_statistic = (adjusted_ss / df_removed) / current_fit.mse
    return float(stats.f.sf(f_statistic, df_removed, current_fit.residual_df))


def _model_selection_step_payload(
    *,
    step: int,
    design_matrix: _DesignMatrix,
    fit: _OlsFit,
    full_model_mse: float,
    removed_term: str | None,
    removal_p_value: float | None,
) -> dict[str, object]:
    aicc, bic = _information_criteria(fit)
    mallows_cp = (fit.sse / full_model_mse) - (len(fit.residuals) - (2 * fit.parameter_count))
    return {
        "step": step,
        "active_terms": [str(term.get("term")) for term in design_matrix.model_terms],
        "removed_term": removed_term,
        "removal_p_value": removal_p_value,
        "s": fit.residual_standard_error,
        "r_squared": fit.r_squared,
        "adjusted_r_squared": fit.adjusted_r_squared,
        "press": fit.press,
        "predicted_r_squared": fit.predicted_r_squared,
        "mallows_cp": mallows_cp,
        "aicc": aicc,
        "bic": bic,
        "coefficients": [
            {
                "term": term.term,
                "estimate": float(fit.coefficients[index]),
            }
            for index, term in enumerate(design_matrix.coefficient_terms)
        ],
    }


def _information_criteria(fit: _OlsFit) -> tuple[float | None, float]:
    n_used = len(fit.residuals)
    parameter_count = fit.parameter_count
    base = n_used * (log(2.0 * pi) + 1.0 + log(fit.sse / n_used))
    aic = base + (2.0 * parameter_count)
    denominator = n_used - parameter_count - 1
    aicc = (
        aic + ((2.0 * parameter_count * (parameter_count + 1)) / denominator)
        if denominator > 0
        else None
    )
    bic = base + (parameter_count * log(n_used))
    return (aicc, bic)


def _equation_payload(
    *,
    response_column: LinearModelColumn,
    coefficient_rows: Sequence[dict[str, object]],
) -> dict[str, object]:
    intercept = float(cast(float, coefficient_rows[0]["estimate"]))
    terms: list[dict[str, object]] = []
    display_parts = [f"{response_column.display_name} = {_format_equation_number(intercept)}"]
    references: dict[str, str] = {}
    for coefficient in coefficient_rows[1:]:
        estimate = float(cast(float, coefficient["estimate"]))
        display_label = _equation_term_label(coefficient)
        sign = "+" if estimate >= 0.0 else "-"
        display_parts.append(f" {sign} {_format_equation_number(abs(estimate))} * {display_label}")
        term_payload = {
            "term": coefficient.get("term"),
            "kind": coefficient.get("term_kind"),
            "coefficient": estimate,
            "source_column_ids": coefficient.get("source_column_ids"),
            "level": coefficient.get("level"),
            "reference_level": coefficient.get("reference_level"),
            "coding": coefficient.get("coding"),
            "display_term": display_label,
        }
        terms.append(term_payload)
        source_ids = coefficient.get("source_column_ids")
        reference_level = coefficient.get("reference_level")
        if (
            isinstance(source_ids, list)
            and len(source_ids) == 1
            and isinstance(reference_level, str)
        ):
            references[str(source_ids[0])] = reference_level
    return {
        "response_label": response_column.display_name,
        "intercept": intercept,
        "terms": terms,
        "display_equation": "".join(display_parts),
        "coefficient_precision": "full_stored_double",
        "categorical_reference_levels": [
            {"column_id": column_id, "reference_level": level}
            for column_id, level in references.items()
        ],
    }


def _equation_term_label(coefficient: dict[str, object]) -> str:
    kind = coefficient.get("term_kind")
    term = str(coefficient.get("term"))
    if kind == "categorical_level":
        source_ids = coefficient.get("source_column_ids")
        source_label = str(source_ids[0]) if isinstance(source_ids, list) and source_ids else term
        return f"I({source_label}={coefficient.get('level')})"
    if kind == "numeric_interaction":
        return term.replace(":", " * ")
    return term


def _format_equation_number(value: float) -> str:
    return format(value, ".12g")


def _training_domain_payload(
    x_rows: Sequence[Sequence[float | str]],
    predictor_columns: Sequence[LinearModelColumn],
) -> dict[str, object]:
    predictors: list[dict[str, object]] = []
    for index, column in enumerate(predictor_columns):
        values = [row[index] for row in x_rows]
        if _is_numeric_column(column):
            numeric_values = [float(value) for value in values]
            predictors.append(
                {
                    "column_id": column.column_id,
                    "kind": "numeric",
                    "minimum": min(numeric_values),
                    "maximum": max(numeric_values),
                    "integer_only": column.data_type == "integer"
                    or column.measurement_level == "count",
                }
            )
        else:
            levels = sorted(
                {str(value) for value in values}, key=lambda value: (value.casefold(), value)
            )
            predictors.append(
                {
                    "column_id": column.column_id,
                    "kind": "categorical",
                    "levels": levels,
                }
            )
    return {"scope": "complete_case_fit_rows", "predictors": predictors}


def _anova_payload(
    *,
    y: FloatArray,
    fit: _OlsFit,
    design_matrix: _DesignMatrix,
    term_blocks: Sequence[_TermBlock],
    original_predictor_rows: Sequence[Sequence[float | str]],
) -> dict[str, object]:
    rows: list[dict[str, object]] = [
        {
            "source": "Regression",
            "row_kind": "regression",
            "df": fit.df_model,
            "adjusted_ss": fit.ssr,
            "adjusted_ms": fit.ssr / fit.df_model if fit.df_model > 0 else None,
            "f_statistic": fit.f_statistic,
            "p_value": fit.f_p_value,
        }
    ]
    for block in term_blocks:
        retained_indices = [
            index for index in range(fit.design.shape[1]) if index not in block.column_indices
        ]
        reduced_design = np.asarray(fit.design[:, retained_indices], dtype=float)
        reduced_rank = int(np.linalg.matrix_rank(reduced_design))
        reduced_coefficients = np.linalg.lstsq(reduced_design, y, rcond=None)[0]
        reduced_residuals = y - (reduced_design @ reduced_coefficients)
        reduced_sse = float(np.dot(reduced_residuals, reduced_residuals))
        term_df = fit.rank - reduced_rank
        adjusted_ss = max(0.0, reduced_sse - fit.sse)
        adjusted_ms = adjusted_ss / term_df
        f_statistic = adjusted_ms / fit.mse
        rows.append(
            {
                "source": block.term,
                "row_kind": "term",
                "term_kind": block.kind,
                "source_column_ids": list(block.source_column_ids),
                "df": term_df,
                "adjusted_ss": adjusted_ss,
                "adjusted_ms": adjusted_ms,
                "f_statistic": f_statistic,
                "p_value": float(stats.f.sf(f_statistic, term_df, fit.residual_df)),
            }
        )
    rows.append(
        {
            "source": "Error",
            "row_kind": "error",
            "df": fit.residual_df,
            "adjusted_ss": fit.sse,
            "adjusted_ms": fit.mse,
            "f_statistic": None,
            "p_value": None,
        }
    )
    lack_of_fit = _lack_of_fit_payload(
        y=y,
        predictor_rows=original_predictor_rows,
        residual_df=fit.residual_df,
        sse=fit.sse,
    )
    if lack_of_fit["available"]:
        rows.extend(cast(list[dict[str, object]], lack_of_fit["rows"]))
    rows.append(
        {
            "source": "Total",
            "row_kind": "total",
            "df": len(y) - 1,
            "adjusted_ss": fit.tss,
            "adjusted_ms": None,
            "f_statistic": None,
            "p_value": None,
        }
    )
    return {
        "method": "adjusted_partial_sums_of_squares",
        "rows": rows,
        "lack_of_fit": lack_of_fit,
        "hierarchy_note": (
            "Term tests are conditional on every other retained term, including higher-order terms."
        ),
    }


def _lack_of_fit_payload(
    *,
    y: FloatArray,
    predictor_rows: Sequence[Sequence[float | str]],
    residual_df: int,
    sse: float,
) -> dict[str, object]:
    replicate_groups: dict[tuple[float | str, ...], list[float]] = {}
    for predictor_row, response in zip(predictor_rows, y, strict=True):
        replicate_groups.setdefault(tuple(predictor_row), []).append(float(response))
    pure_error_df = sum(len(values) - 1 for values in replicate_groups.values())
    if pure_error_df <= 0:
        return {
            "available": False,
            "reason": "no_replicated_predictor_settings",
            "rows": [],
        }
    pure_error_ss = sum(
        sum((value - (sum(values) / len(values))) ** 2 for value in values)
        for values in replicate_groups.values()
    )
    lack_of_fit_df = residual_df - pure_error_df
    if lack_of_fit_df <= 0:
        return {
            "available": False,
            "reason": "no_lack_of_fit_degrees_of_freedom",
            "rows": [],
        }
    pure_error_ms = pure_error_ss / pure_error_df
    if pure_error_ms <= 0.0 or not isfinite(pure_error_ms):
        return {
            "available": False,
            "reason": "pure_error_variance_zero",
            "rows": [],
        }
    lack_of_fit_ss = max(0.0, sse - pure_error_ss)
    lack_of_fit_ms = lack_of_fit_ss / lack_of_fit_df
    f_statistic = lack_of_fit_ms / pure_error_ms
    return {
        "available": True,
        "reason": None,
        "replicate_setting_count": sum(len(values) > 1 for values in replicate_groups.values()),
        "rows": [
            {
                "source": "Lack-of-Fit",
                "row_kind": "lack_of_fit",
                "df": lack_of_fit_df,
                "adjusted_ss": lack_of_fit_ss,
                "adjusted_ms": lack_of_fit_ms,
                "f_statistic": f_statistic,
                "p_value": float(stats.f.sf(f_statistic, lack_of_fit_df, pure_error_df)),
            },
            {
                "source": "Pure Error",
                "row_kind": "pure_error",
                "df": pure_error_df,
                "adjusted_ss": pure_error_ss,
                "adjusted_ms": pure_error_ms,
                "f_statistic": None,
                "p_value": None,
            },
        ],
    }


def _residual_plots_payload(
    *,
    fitted: FloatArray,
    residuals: FloatArray,
    leverage: FloatArray,
    mse: float,
    row_indices: Sequence[int],
) -> dict[str, object]:
    standard_denominator = np.sqrt(mse * np.maximum(1.0 - leverage, 0.0))
    standardized = np.divide(
        residuals,
        standard_denominator,
        out=np.full_like(residuals, np.nan),
        where=standard_denominator > 0.0,
    )
    raw_values = np.asarray(residuals, dtype=float)
    standardized_values = np.asarray(standardized, dtype=float)
    return {
        "residual_types_available": ["raw", "standardized"],
        "histograms": {
            "raw": _histogram_payload(raw_values),
            "standardized": _histogram_payload(standardized_values),
        },
        "qq_plots": {
            "raw": _qq_plot_payload(raw_values, row_indices),
            "standardized": _qq_plot_payload(standardized_values, row_indices),
        },
        "residuals_vs_fits": {
            "raw": _residual_scatter_payload(fitted, raw_values, row_indices, include_order=False),
            "standardized": _residual_scatter_payload(
                fitted,
                standardized_values,
                row_indices,
                include_order=False,
            ),
        },
        "residuals_vs_order": {
            "raw": _residual_scatter_payload(fitted, raw_values, row_indices, include_order=True),
            "standardized": _residual_scatter_payload(
                fitted,
                standardized_values,
                row_indices,
                include_order=True,
            ),
        },
        "point_limit": DIAGNOSTIC_POINT_LIMIT,
        "points_truncated": len(residuals) > DIAGNOSTIC_POINT_LIMIT,
    }


def _histogram_payload(values: FloatArray) -> dict[str, object]:
    finite_values = values[np.isfinite(values)]
    if finite_values.size == 0:
        return {"n": 0, "bins": []}
    bin_count = min(30, max(5, int(np.ceil(np.sqrt(finite_values.size)))))
    counts, edges = np.histogram(finite_values, bins=bin_count)
    return {
        "n": int(finite_values.size),
        "bins": [
            {
                "lower": float(edges[index]),
                "upper": float(edges[index + 1]),
                "count": int(counts[index]),
            }
            for index in range(len(counts))
        ],
    }


def _qq_plot_payload(values: FloatArray, row_indices: Sequence[int]) -> dict[str, object]:
    finite = [
        (float(value), int(row_indices[index]))
        for index, value in enumerate(values)
        if isfinite(float(value))
    ]
    finite.sort(key=lambda item: (item[0], item[1]))
    n_values = len(finite)
    if n_values == 0:
        return {"n": 0, "points": [], "reference_line": None, "truncated": False}
    probabilities = (np.arange(1, n_values + 1, dtype=float) - 0.375) / (n_values + 0.25)
    theoretical = np.asarray(stats.norm.ppf(probabilities), dtype=float)
    observed = np.asarray([item[0] for item in finite], dtype=float)
    slope, intercept = np.polyfit(theoretical, observed, 1) if n_values > 1 else (0.0, observed[0])
    selected = _bounded_indices(n_values)
    return {
        "n": n_values,
        "points": [
            {
                "rank": int(index + 1),
                "row_index": finite[index][1],
                "theoretical_quantile": float(theoretical[index]),
                "residual": float(observed[index]),
            }
            for index in selected
        ],
        "reference_line": {"slope": float(slope), "intercept": float(intercept)},
        "truncated": n_values > DIAGNOSTIC_POINT_LIMIT,
    }


def _residual_scatter_payload(
    fitted: FloatArray,
    residuals: FloatArray,
    row_indices: Sequence[int],
    *,
    include_order: bool,
) -> dict[str, object]:
    finite_indices = [index for index, value in enumerate(residuals) if isfinite(float(value))]
    selected_positions = _bounded_indices(len(finite_indices))
    selected_indices = [finite_indices[position] for position in selected_positions]
    return {
        "n": len(finite_indices),
        "points": [
            {
                "row_index": int(row_indices[index]),
                "order": int(index + 1),
                "fitted": float(fitted[index]),
                "residual": float(residuals[index]),
            }
            for index in selected_indices
        ],
        "truncated": len(finite_indices) > DIAGNOSTIC_POINT_LIMIT,
        "x_kind": "order" if include_order else "fitted",
    }


def _bounded_indices(count: int) -> list[int]:
    if count <= DIAGNOSTIC_POINT_LIMIT:
        return list(range(count))
    return sorted(
        {int(round(value)) for value in np.linspace(0, count - 1, DIAGNOSTIC_POINT_LIMIT)}
    )


def _parse_rows(
    rows: Iterable[Sequence[str | None]],
    *,
    response_column: LinearModelColumn,
    predictor_columns: Sequence[LinearModelColumn],
    decimal: str,
    thousands: str | None,
) -> _ParsedRows:
    y_values: list[float] = []
    x_rows: list[list[float | str]] = []
    row_indices: list[int] = []
    n_total = 0
    n_excluded_missing = 0
    n_excluded_non_numeric = 0

    for row in rows:
        n_total += 1
        row_index = n_total - 1
        cells: list[_ParsedCell] = [
            _parse_cell(
                _row_value(row, response_column.column_index),
                decimal=decimal,
                thousands=thousands,
            )
        ]
        cells.extend(
            _parse_predictor_cell(
                _row_value(row, column.column_index),
                column=column,
                decimal=decimal,
                thousands=thousands,
            )
            for column in predictor_columns
        )
        if any(cell.missing for cell in cells):
            n_excluded_missing += 1
            continue
        if any(cell.non_numeric for cell in cells):
            n_excluded_non_numeric += 1
            continue
        response_value = cells[0].value
        assert isinstance(response_value, float)
        predictor_values: list[float | str] = []
        for cell in cells[1:]:
            assert cell.value is not None
            predictor_values.append(cell.value)
        y_values.append(response_value)
        x_rows.append(predictor_values)
        row_indices.append(row_index)

    return _ParsedRows(
        n_total=n_total,
        n_excluded_missing=n_excluded_missing,
        n_excluded_non_numeric=n_excluded_non_numeric,
        y_values=y_values,
        x_rows=x_rows,
        row_indices=row_indices,
    )


def _build_design_matrix(
    x_rows: Sequence[Sequence[float | str]],
    predictor_columns: Sequence[LinearModelColumn],
    *,
    interaction_terms: Sequence[tuple[str, str]],
    quadratic_terms: Sequence[str],
) -> _DesignMatrix:
    n_used = len(x_rows)
    predictor_arrays: list[FloatArray] = []
    coefficient_terms: list[_CoefficientTerm] = [
        _CoefficientTerm(term="Intercept", term_kind="intercept", column=None),
    ]
    model_terms: list[dict[str, object]] = []
    categorical_predictor_count = 0
    numeric_predictor_values: dict[str, FloatArray] = {}
    columns_by_id = {column.column_id: column for column in predictor_columns}

    for predictor_index, column in enumerate(predictor_columns):
        values = [row[predictor_index] for row in x_rows]
        if _is_numeric_column(column):
            numeric_values = [float(value) for value in values]
            if min(numeric_values) == max(numeric_values):
                raise LinearModelError("linear_model_predictor_constant")
            numeric_array = np.asarray(numeric_values, dtype=float)
            numeric_predictor_values[column.column_id] = numeric_array
            predictor_arrays.append(numeric_array)
            coefficient_terms.append(
                _CoefficientTerm(
                    term=column.display_name,
                    term_kind="numeric_main_effect",
                    column=column,
                    source_columns=(column,),
                ),
            )
            model_terms.append(
                {
                    "term": column.display_name,
                    "kind": "numeric_main_effect",
                    "column_id": column.column_id,
                    "source_column_ids": [column.column_id],
                },
            )
            continue

        if not _is_categorical_predictor_column(column):
            raise LinearModelError("linear_model_predictor_column_unsupported_type")

        categorical_values = [str(value) for value in values]
        levels = sorted(set(categorical_values), key=lambda value: (value.casefold(), value))
        if len(levels) < 2:
            raise LinearModelError("linear_model_factor_single_level")
        if len(levels) > MAX_CATEGORICAL_LEVELS:
            raise LinearModelError("linear_model_factor_too_many_levels")

        reference_level = levels[0]
        design_levels = levels[1:]
        categorical_predictor_count += 1
        model_terms.append(
            {
                "term": column.display_name,
                "kind": "categorical_main_effect",
                "column_id": column.column_id,
                "coding": "treatment",
                "reference_level": reference_level,
                "levels": levels,
            },
        )
        for level in design_levels:
            predictor_arrays.append(
                np.asarray(
                    [1.0 if value == level else 0.0 for value in categorical_values],
                    dtype=float,
                ),
            )
            coefficient_terms.append(
                _CoefficientTerm(
                    term=f"{column.display_name}[{level}]",
                    term_kind="categorical_level",
                    column=column,
                    source_columns=(column,),
                    level=level,
                    reference_level=reference_level,
                    coding="treatment",
                ),
            )

    column_order = {column.column_id: index for index, column in enumerate(predictor_columns)}
    interaction_specs = _normalize_interaction_terms(interaction_terms, column_order=column_order)
    quadratic_specs = _normalize_quadratic_terms(quadratic_terms)
    for column_id in quadratic_specs:
        quadratic_column = columns_by_id.get(column_id)
        quadratic_values = numeric_predictor_values.get(column_id)
        if quadratic_column is None:
            raise LinearModelError("linear_model_term_predictor_not_selected")
        if quadratic_values is None:
            raise LinearModelError("linear_model_term_requires_numeric_predictor")
        squared = np.asarray(quadratic_values * quadratic_values, dtype=float)
        if float(np.min(squared)) == float(np.max(squared)):
            raise LinearModelError("linear_model_quadratic_term_constant")
        predictor_arrays.append(squared)
        term_label = f"{quadratic_column.display_name}^2"
        coefficient_terms.append(
            _CoefficientTerm(
                term=term_label,
                term_kind="numeric_quadratic",
                column=quadratic_column,
                source_columns=(quadratic_column,),
            ),
        )
        model_terms.append(
            {
                "term": term_label,
                "kind": "numeric_quadratic",
                "column_id": quadratic_column.column_id,
                "source_column_ids": [quadratic_column.column_id],
            },
        )

    for left_column_id, right_column_id in interaction_specs:
        left_column = columns_by_id.get(left_column_id)
        right_column = columns_by_id.get(right_column_id)
        left_values = numeric_predictor_values.get(left_column_id)
        right_values = numeric_predictor_values.get(right_column_id)
        if left_column is None or right_column is None:
            raise LinearModelError("linear_model_term_predictor_not_selected")
        if left_values is None or right_values is None:
            raise LinearModelError("linear_model_term_requires_numeric_predictor")
        product = np.asarray(left_values * right_values, dtype=float)
        if float(np.min(product)) == float(np.max(product)):
            raise LinearModelError("linear_model_interaction_term_constant")
        predictor_arrays.append(product)
        term_label = f"{left_column.display_name}:{right_column.display_name}"
        coefficient_terms.append(
            _CoefficientTerm(
                term=term_label,
                term_kind="numeric_interaction",
                column=None,
                source_columns=(left_column, right_column),
            ),
        )
        model_terms.append(
            {
                "term": term_label,
                "kind": "numeric_interaction",
                "column_id": None,
                "source_column_ids": [left_column.column_id, right_column.column_id],
            },
        )

    if not predictor_arrays:
        raise LinearModelError("linear_model_predictors_required")
    predictors = np.column_stack(predictor_arrays)
    design = np.column_stack([np.ones(n_used), predictors])
    parameter_count = int(design.shape[1])
    return _DesignMatrix(
        design=np.asarray(design, dtype=float),
        predictors=np.asarray(predictors, dtype=float),
        coefficient_terms=coefficient_terms,
        model_terms=model_terms,
        df_model=parameter_count - 1,
        parameter_count=parameter_count,
        categorical_predictor_count=categorical_predictor_count,
        interaction_term_count=len(interaction_specs),
        quadratic_term_count=len(quadratic_specs),
    )


def _normalize_quadratic_terms(quadratic_terms: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for column_id in quadratic_terms:
        if not column_id:
            raise LinearModelError("invalid_linear_model_quadratic_terms")
        if column_id in seen:
            raise LinearModelError("duplicate_linear_model_quadratic_term")
        seen.add(column_id)
        normalized.append(column_id)
    return normalized


def _normalize_interaction_terms(
    interaction_terms: Sequence[tuple[str, str]],
    *,
    column_order: dict[str, int],
) -> list[tuple[str, str]]:
    normalized: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for left_column_id, right_column_id in interaction_terms:
        if not left_column_id or not right_column_id:
            raise LinearModelError("invalid_linear_model_interaction_terms")
        if left_column_id == right_column_id:
            raise LinearModelError("linear_model_interaction_same_predictor")
        seen_key = tuple(sorted((left_column_id, right_column_id)))
        if len(seen_key) != 2:
            raise LinearModelError("invalid_linear_model_interaction_terms")
        typed_seen_key = (seen_key[0], seen_key[1])
        if typed_seen_key in seen:
            raise LinearModelError("duplicate_linear_model_interaction_term")
        seen.add(typed_seen_key)
        if column_order.get(left_column_id, 10**9) <= column_order.get(
            right_column_id,
            10**9,
        ):
            normalized.append((left_column_id, right_column_id))
        else:
            normalized.append((right_column_id, left_column_id))
    return normalized


def _row_value(row: Sequence[str | None], column_index: int) -> str | None:
    return row[column_index] if column_index < len(row) else None


def _parse_predictor_cell(
    value: str | None,
    *,
    column: LinearModelColumn,
    decimal: str,
    thousands: str | None,
) -> _ParsedCell:
    if _is_numeric_column(column):
        return _parse_cell(value, decimal=decimal, thousands=thousands)
    return _parse_categorical_cell(value)


def _parse_categorical_cell(value: str | None) -> _ParsedCell:
    if value is None or value.strip() == "":
        return _ParsedCell(missing=True, non_numeric=False, value=None)
    return _ParsedCell(missing=False, non_numeric=False, value=value.strip())


def _parse_cell(
    value: str | None,
    *,
    decimal: str,
    thousands: str | None,
) -> _ParsedCell:
    if value is None or value.strip() == "":
        return _ParsedCell(missing=True, non_numeric=False, value=None)

    normalized = value.strip()
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")

    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return _ParsedCell(missing=False, non_numeric=True, value=None)
    if not parsed.is_finite():
        return _ParsedCell(missing=False, non_numeric=True, value=None)
    as_float = float(parsed)
    if not isfinite(as_float):
        return _ParsedCell(missing=False, non_numeric=True, value=None)
    return _ParsedCell(missing=False, non_numeric=False, value=as_float)


def _is_numeric_column(column: LinearModelColumn) -> bool:
    return (
        classify_linear_model_predictor(
            data_type=column.data_type,
            measurement_level=column.measurement_level,
            role=column.role,
        )
        == "numeric"
    )


def _is_categorical_predictor_column(column: LinearModelColumn) -> bool:
    return (
        classify_linear_model_predictor(
            data_type=column.data_type,
            measurement_level=column.measurement_level,
            role=column.role,
        )
        == "categorical"
    )


def _coefficient_payloads(
    coefficients: FloatArray,
    standard_errors: FloatArray,
    *,
    response_column: LinearModelColumn,
    terms: Sequence[_CoefficientTerm],
    residual_df: int,
    t_critical: float,
    confidence_level: float,
    vif_values: Sequence[float | None],
) -> list[dict[str, object]]:
    coefficient_values = [float(value) for value in coefficients]
    standard_error_values = [float(value) for value in standard_errors]

    rows: list[dict[str, object]] = []
    for index, term in enumerate(terms):
        estimate = coefficient_values[index]
        standard_error = standard_error_values[index]
        statistic = estimate / standard_error
        p_value = float(2.0 * stats.t.sf(abs(statistic), df=residual_df))
        vif_value = vif_values[index - 1] if index > 0 else None
        rows.append(
            {
                "term": term.term,
                "term_kind": term.term_kind,
                "column_id": term.column.column_id if term.column is not None else None,
                "source_column_ids": [column.column_id for column in term.source_columns],
                "response_column_id": response_column.column_id,
                "level": term.level,
                "reference_level": term.reference_level,
                "coding": term.coding,
                "estimate": estimate,
                "standard_error": standard_error,
                "statistic": statistic,
                "statistic_name": "t",
                "p_value": p_value,
                "confidence_interval": {
                    "method": "t",
                    "level": confidence_level,
                    "lower": estimate - (t_critical * standard_error),
                    "upper": estimate + (t_critical * standard_error),
                },
                "vif": vif_value,
            },
        )
    return rows


def _vif_values(predictors: FloatArray) -> list[float | None]:
    predictor_count = int(predictors.shape[1])
    if predictor_count == 1:
        return [1.0]

    values: list[float | None] = []
    for index in range(predictor_count):
        y = predictors[:, index]
        other_columns = [column for column in range(predictor_count) if column != index]
        design = np.column_stack([np.ones(len(y)), predictors[:, other_columns]])
        try:
            beta = np.linalg.lstsq(design, y, rcond=None)[0]
        except np.linalg.LinAlgError:
            values.append(None)
            continue
        fitted = design @ beta
        residuals = y - fitted
        sse = float(np.dot(residuals, residuals))
        centered = y - float(np.mean(y))
        tss = float(np.dot(centered, centered))
        if tss <= 0.0:
            values.append(None)
            continue
        r_squared = 1.0 - (sse / tss)
        if r_squared >= 1.0:
            values.append(None)
            continue
        values.append(1.0 / (1.0 - r_squared))
    return values


def _diagnostics_payload(
    *,
    fitted: FloatArray,
    residuals: FloatArray,
    design: FloatArray,
    xtx_inverse: FloatArray,
    mse: float,
    parameter_count: int,
    row_indices: Sequence[int],
) -> dict[str, object]:
    n_used = int(len(residuals))
    leverage_values = np.einsum("ij,jk,ik->i", design, xtx_inverse, design)
    leverage_values = np.clip(leverage_values, 0.0, 1.0)
    denominator = np.sqrt(mse * np.maximum(1.0 - leverage_values, 0.0))
    standardized_residuals: list[float | None] = []
    cooks_distances: list[float | None] = []
    for index, residual in enumerate(residuals):
        residual_denominator = float(denominator[index])
        leverage = float(leverage_values[index])
        if residual_denominator <= 0.0 or not isfinite(residual_denominator):
            standardized_residuals.append(None)
            cooks_distances.append(None)
            continue
        standardized = float(residual / residual_denominator)
        standardized_residuals.append(standardized)
        if leverage >= 1.0:
            cooks_distances.append(None)
            continue
        cooks_distances.append(
            (standardized**2 * leverage) / (parameter_count * max(1.0 - leverage, 1e-12)),
        )

    leverage_threshold = min(1.0, (2.0 * parameter_count) / n_used)
    cooks_distance_threshold = 4.0 / n_used
    high_leverage_indices = [
        row_indices[index]
        for index, leverage in enumerate(leverage_values)
        if float(leverage) > leverage_threshold
    ]
    large_residual_indices = [
        row_indices[index]
        for index, residual in enumerate(standardized_residuals)
        if residual is not None and abs(residual) > STANDARDIZED_RESIDUAL_WARNING_THRESHOLD
    ]
    high_cooks_distance_indices = [
        row_indices[index]
        for index, cooks_distance in enumerate(cooks_distances)
        if cooks_distance is not None and cooks_distance > cooks_distance_threshold
    ]

    finite_cooks_distances = [
        value for value in cooks_distances if value is not None and isfinite(value)
    ]
    finite_standardized_residuals = [
        value for value in standardized_residuals if value is not None and isfinite(value)
    ]
    point_count = min(n_used, DIAGNOSTIC_POINT_LIMIT)
    points = [
        {
            "row_index": row_indices[index],
            "fitted": float(fitted[index]),
            "residual": float(residuals[index]),
            "standardized_residual": standardized_residuals[index],
            "leverage": float(leverage_values[index]),
            "cooks_distance": cooks_distances[index],
        }
        for index in range(point_count)
    ]

    return {
        "residual_summary": {
            "mean": float(np.mean(residuals)),
            "min": float(np.min(residuals)),
            "q1": _percentile(residuals, 25.0),
            "median": _percentile(residuals, 50.0),
            "q3": _percentile(residuals, 75.0),
            "max": float(np.max(residuals)),
            "max_abs_standardized": (
                max(abs(value) for value in finite_standardized_residuals)
                if finite_standardized_residuals
                else None
            ),
            "large_standardized_threshold": STANDARDIZED_RESIDUAL_WARNING_THRESHOLD,
            "large_standardized_count": len(large_residual_indices),
            "large_standardized_row_indices": large_residual_indices,
        },
        "leverage": {
            "mean": float(np.mean(leverage_values)),
            "max": float(np.max(leverage_values)),
            "threshold": leverage_threshold,
            "high_count": len(high_leverage_indices),
            "high_row_indices": high_leverage_indices,
        },
        "influence": {
            "cooks_distance_max": (max(finite_cooks_distances) if finite_cooks_distances else None),
            "cooks_distance_threshold": cooks_distance_threshold,
            "high_cooks_distance_count": len(high_cooks_distance_indices),
            "high_cooks_distance_row_indices": high_cooks_distance_indices,
        },
        "diagnostic_points": {
            "point_limit": DIAGNOSTIC_POINT_LIMIT,
            "points_included": point_count,
            "truncated": n_used > DIAGNOSTIC_POINT_LIMIT,
            "points": points,
        },
    }


def _percentile(values: FloatArray, percentile: float) -> float:
    return float(np.percentile(values, percentile))


def _column_payload(column: LinearModelColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "column_index": column.column_index,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _result_warnings(
    *,
    n_excluded_missing: int,
    n_excluded_non_numeric: int,
    condition_number: float,
    max_vif: float | None,
    diagnostics: dict[str, object],
    categorical_predictor_count: int,
    interaction_term_count: int,
    quadratic_term_count: int,
    press_available: bool,
    model_selection_method: str,
    intercept_only: bool,
) -> list[str]:
    warnings = [
        "linear_model_not_causation",
        "linear_model_linearity_assumption",
        "linear_model_independence_assumption",
        "linear_model_homoscedasticity_assumption",
        "linear_model_residual_normality_assumption",
        "linear_model_outlier_influence_sensitive",
    ]
    if n_excluded_missing > 0:
        warnings.append("missing_values_excluded")
    if n_excluded_non_numeric > 0:
        warnings.append("non_numeric_values_excluded")
    if categorical_predictor_count > 0:
        warnings.append("linear_model_categorical_treatment_coding")
    if quadratic_term_count > 0:
        warnings.append("linear_model_quadratic_terms_selected")
    if interaction_term_count > 0:
        warnings.append("linear_model_interaction_terms_selected")
    if not press_available:
        warnings.append("linear_model_press_unavailable_high_leverage")
    if model_selection_method == "backward_elimination":
        warnings.append("linear_model_post_selection_inference_exploratory")
    if intercept_only:
        warnings.append("linear_model_intercept_only_selected")
    if condition_number >= CONDITION_NUMBER_WARNING_THRESHOLD:
        warnings.append("linear_model_high_condition_number")
    if max_vif is not None and max_vif >= VIF_WARNING_THRESHOLD:
        warnings.append("linear_model_high_vif")
    residual_summary = diagnostics.get("residual_summary")
    if isinstance(residual_summary, dict) and _positive_count(
        residual_summary.get("large_standardized_count"),
    ):
        warnings.append("linear_model_large_standardized_residual")
    leverage = diagnostics.get("leverage")
    if isinstance(leverage, dict) and _positive_count(leverage.get("high_count")):
        warnings.append("linear_model_high_leverage")
    influence = diagnostics.get("influence")
    if isinstance(influence, dict) and _positive_count(
        influence.get("high_cooks_distance_count"),
    ):
        warnings.append("linear_model_high_cooks_distance")
    return warnings


def _positive_count(value: object) -> bool:
    return isinstance(value, int) and value > 0
