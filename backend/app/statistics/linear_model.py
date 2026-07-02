from __future__ import annotations

import importlib.metadata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite, sqrt

import numpy as np
from numpy.typing import NDArray
from scipy import stats  # type: ignore[import-untyped]

MIN_RESIDUAL_DF = 1
CONDITION_NUMBER_WARNING_THRESHOLD = 30.0
VIF_WARNING_THRESHOLD = 5.0
STANDARDIZED_RESIDUAL_WARNING_THRESHOLD = 3.0
DIAGNOSTIC_POINT_LIMIT = 500
MAX_CATEGORICAL_LEVELS = 25
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
) -> dict[str, object]:
    if alpha <= 0.0 or alpha >= 1.0:
        raise LinearModelError("invalid_linear_model_alpha")
    if confidence_level <= 0.0 or confidence_level >= 1.0:
        raise LinearModelError("invalid_linear_model_confidence_level")
    if not predictor_columns:
        raise LinearModelError("linear_model_predictors_required")

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
    design_matrix = _build_design_matrix(
        x_rows,
        predictor_columns,
        interaction_terms=interaction_terms or (),
        quadratic_terms=quadratic_terms or (),
    )
    design = design_matrix.design
    predictors = design_matrix.predictors
    parameter_count = design_matrix.parameter_count
    df_model = design_matrix.df_model
    residual_df = n_used - parameter_count
    if residual_df < MIN_RESIDUAL_DF:
        raise LinearModelError("linear_model_residual_df_too_small")
    if min(y_values) == max(y_values):
        raise LinearModelError("linear_model_response_constant")

    y: FloatArray = np.asarray(y_values, dtype=float)
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

    y_mean = float(np.mean(y))
    centered_y = y - y_mean
    tss = float(np.dot(centered_y, centered_y))
    if tss <= 0.0 or not isfinite(tss):
        raise LinearModelError("linear_model_response_constant")

    mse = sse / residual_df
    covariance_matrix = xtx_inverse * mse
    standard_errors: FloatArray = np.sqrt(np.diag(covariance_matrix))
    if not np.all(np.isfinite(standard_errors)) or np.any(standard_errors <= 0.0):
        raise LinearModelError("linear_model_standard_error_not_finite")

    t_critical = float(stats.t.ppf(1.0 - ((1.0 - confidence_level) / 2.0), df=residual_df))
    coefficient_rows = _coefficient_payloads(
        coefficients,
        standard_errors,
        response_column=response_column,
        terms=design_matrix.coefficient_terms,
        residual_df=residual_df,
        t_critical=t_critical,
        confidence_level=confidence_level,
        vif_values=_vif_values(predictors),
    )

    r_squared = 1.0 - (sse / tss)
    adjusted_r_squared = 1.0 - ((1.0 - r_squared) * ((n_used - 1) / residual_df))
    ssr = tss - sse
    f_statistic = (ssr / df_model) / mse
    f_p_value = float(stats.f.sf(f_statistic, df_model, residual_df))
    condition_number = float(np.linalg.cond(design))
    vif_candidates: list[float] = []
    for coefficient in coefficient_rows:
        vif_value = coefficient.get("vif")
        if isinstance(vif_value, float):
            vif_candidates.append(vif_value)
    max_vif = max(vif_candidates, default=None)
    diagnostics = _diagnostics_payload(
        fitted=fitted,
        residuals=residuals,
        design=design,
        xtx_inverse=xtx_inverse,
        mse=mse,
        parameter_count=parameter_count,
        row_indices=parsed.row_indices,
    )

    return {
        "schema_version": 4,
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
        ),
        "response": _column_payload(response_column),
        "predictors": [_column_payload(column) for column in predictor_columns],
        "model_specification": {
            "intercept": True,
            "terms": design_matrix.model_terms,
        },
        "prediction_basis": {
            "basis_schema_version": 1,
            "coefficient_order": [term.term for term in design_matrix.coefficient_terms],
            "xtx_inverse": [[float(value) for value in row] for row in xtx_inverse.tolist()],
            "sigma_squared": mse,
            "df_residual": residual_df,
        },
        "sample": {
            "n_total": parsed.n_total,
            "n_used": n_used,
            "n_excluded_missing": parsed.n_excluded_missing,
            "n_excluded_non_numeric": parsed.n_excluded_non_numeric,
            "df_model": df_model,
            "df_residual": residual_df,
        },
        "fit": {
            "r_squared": r_squared,
            "adjusted_r_squared": adjusted_r_squared,
            "residual_standard_error": sqrt(mse),
            "sigma_squared": mse,
            "sse": sse,
            "ssr": ssr,
            "tss": tss,
            "f_statistic": f_statistic,
            "f_p_value": f_p_value,
        },
        "coefficients": coefficient_rows,
        "diagnostics": {
            "rank": rank,
            "parameter_count": parameter_count,
            "condition_number": condition_number,
            "max_vif": max_vif,
            **diagnostics,
        },
    }


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
        column.data_type in {"integer", "decimal"}
        and column.measurement_level not in {"nominal", "binary", "ordinal"}
        and column.role != "factor"
    )


def _is_categorical_predictor_column(column: LinearModelColumn) -> bool:
    return column.data_type != "datetime" and (
        column.data_type in {"text", "boolean"}
        or column.measurement_level in {"nominal", "binary", "ordinal"}
        or column.role == "factor"
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
