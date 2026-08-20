from __future__ import annotations

import importlib.metadata
import warnings
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import TYPE_CHECKING, Literal, cast

import numpy as np
from numpy.typing import NDArray
from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from sklearn.cross_decomposition import PLSRegression  # type: ignore[import-untyped]

FloatArray = NDArray[np.float64]
COMPONENT_TIE_TOLERANCE = 1e-12
MAX_PLS_PREDICTORS = 100
MAX_PLS_COMPONENTS = 30
MAX_PLS_USABLE_ROWS = 20_000
MAX_PLS_LOO_ROWS = 500


class PlsRegressionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PlsColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class PlsOptions:
    scale: bool = True
    component_selection: Literal["automatic_cv", "fixed"] = "automatic_cv"
    n_components: int | None = None
    max_components: int = 10
    cv_method: Literal["k_fold", "leave_one_out"] = "k_fold"
    cv_folds: int = 5
    cv_shuffle: bool = True
    cv_seed: int = 20260820
    max_iter: int = 500
    tol: float = 1e-6
    plot_point_limit: int = 2000


@dataclass(frozen=True)
class _ParsedRows:
    x: FloatArray
    y: FloatArray
    row_indices: list[int]
    n_total: int
    n_excluded_missing: int
    n_excluded_non_numeric: int


def calculate_pls_regression(
    rows: Iterable[Sequence[str | None]],
    response_column: PlsColumn,
    predictor_columns: Sequence[PlsColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    options: PlsOptions | None = None,
) -> dict[str, object]:
    active = options or PlsOptions()
    _validate_columns(response_column, predictor_columns)
    parsed = _parse_rows(
        rows,
        response_column,
        predictor_columns,
        decimal=decimal,
        thousands=thousands,
    )
    _validate_sample(parsed, predictor_columns, active)
    splits = _cross_validation_splits(parsed.x.shape[0], active)
    minimum_training_rows = min(len(training) for training, _validation in splits)
    maximum_components = min(
        MAX_PLS_COMPONENTS,
        parsed.x.shape[1],
        minimum_training_rows,
    )
    if active.max_components < 1 or active.max_components > maximum_components:
        raise PlsRegressionError("pls_component_count_invalid")
    if active.component_selection == "fixed":
        if active.n_components is None or not 1 <= active.n_components <= active.max_components:
            raise PlsRegressionError("pls_component_count_invalid")
    elif active.component_selection != "automatic_cv":
        raise PlsRegressionError("pls_component_count_invalid")

    tss_y = float(np.sum(np.square(parsed.y - np.mean(parsed.y))))
    candidate_models: dict[int, PLSRegression] = {}
    selection_rows: list[dict[str, object]] = []
    cv_predictions_by_component: dict[int, FloatArray] = {}
    convergence_by_component: dict[int, bool] = {}
    with threadpool_limits(limits=1):
        for component_count in range(1, active.max_components + 1):
            model, converged = _fit_model(parsed.x, parsed.y, component_count, active)
            fitted = _predict(model, parsed.x)
            training_sse = float(np.sum(np.square(parsed.y - fitted)))
            training_r_squared = 1.0 - (training_sse / tss_y)
            cv_fitted = _cross_validated_predictions(
                parsed.x,
                parsed.y,
                component_count,
                splits,
                active,
            )
            press = float(np.sum(np.square(parsed.y - cv_fitted)))
            predicted_r_squared = 1.0 - (press / tss_y)
            cv_rmse = float(np.sqrt(press / parsed.y.size))
            x_variance = _cumulative_x_variance(model, parsed.x, active.scale)
            candidate_models[component_count] = model
            cv_predictions_by_component[component_count] = cv_fitted
            convergence_by_component[component_count] = converged
            selection_rows.append(
                {
                    "components": component_count,
                    "x_variance": x_variance,
                    "training_sse": training_sse,
                    "training_r_squared": training_r_squared,
                    "press": press,
                    "predicted_r_squared": predicted_r_squared,
                    "cv_rmse": cv_rmse,
                    "iterations": [int(value) for value in model.n_iter_],
                    "converged": converged,
                },
            )

    selected_components = (
        _select_components(selection_rows)
        if active.component_selection == "automatic_cv"
        else int(active.n_components or 0)
    )
    selected_model = candidate_models[selected_components]
    selected_cv_fitted = cv_predictions_by_component[selected_components]
    fitted = _predict(selected_model, parsed.x)
    residuals = parsed.y - fitted
    cv_residuals = parsed.y - selected_cv_fitted
    raw_coefficients = np.asarray(selected_model.coef_, dtype=np.float64).reshape(-1)
    sklearn_intercept = float(np.asarray(selected_model.intercept_).reshape(-1)[0])
    x_mean = np.mean(parsed.x, axis=0)
    x_standard_deviation = np.std(parsed.x, axis=0, ddof=1)
    y_mean = float(np.mean(parsed.y))
    y_standard_deviation = float(np.std(parsed.y, ddof=1))
    effective_intercept = sklearn_intercept - float(np.dot(x_mean, raw_coefficients))
    standardized_coefficients = raw_coefficients * x_standard_deviation / y_standard_deviation
    selected_row = selection_rows[selected_components - 1]
    warnings_list = _warning_codes(
        selection_rows=selection_rows,
        selected_row=selected_row,
        selected_components=selected_components,
        maximum_evaluated=active.max_components,
        converged=convergence_by_component[selected_components],
        excluded=parsed.n_excluded_missing + parsed.n_excluded_non_numeric,
    )
    plot_indices = _evenly_spaced_indices(parsed.y.size, active.plot_point_limit)

    return {
        "schema_version": 1,
        "summary_type": "partial_least_squares_regression",
        "method": {
            "name": "PLS1 regression",
            "engine": "sklearn.cross_decomposition.PLSRegression",
            "engine_version": importlib.metadata.version("scikit-learn"),
            "component_selection": active.component_selection,
            "cv_method": active.cv_method,
            "cv_folds": len(splits),
            "cv_shuffle": active.cv_shuffle if active.cv_method == "k_fold" else False,
            "cv_seed": active.cv_seed if active.cv_method == "k_fold" else None,
            "scale": active.scale,
            "max_iter": active.max_iter,
            "tol": active.tol,
            "missing_policy": "complete_case",
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
        "component_selection": {
            "selected_components": selected_components,
            "evaluated_components": active.max_components,
            "maximum_allowed_components": maximum_components,
            "tie_tolerance": COMPONENT_TIE_TOLERANCE,
            "rows": selection_rows,
        },
        "model_summary": {
            "selected_components": selected_components,
            "training_r_squared": selected_row["training_r_squared"],
            "predicted_r_squared": selected_row["predicted_r_squared"],
            "press": selected_row["press"],
            "cv_rmse": selected_row["cv_rmse"],
            "cumulative_x_variance": selected_row["x_variance"],
        },
        "coefficients": [
            {
                "column_id": column.column_id,
                "display_name": column.display_name,
                "coefficient": float(raw_coefficients[index]),
                "standardized_coefficient": float(standardized_coefficients[index]),
                "direction": (
                    "positive"
                    if raw_coefficients[index] > 0
                    else "negative"
                    if raw_coefficients[index] < 0
                    else "zero"
                ),
            }
            for index, column in enumerate(predictor_columns)
        ],
        "prediction_basis": {
            "predictor_order": [column.column_id for column in predictor_columns],
            "coefficients": [float(value) for value in raw_coefficients],
            "effective_intercept": effective_intercept,
            "sklearn_intercept": sklearn_intercept,
            "x_mean": [float(value) for value in x_mean],
            "x_standard_deviation": [float(value) for value in x_standard_deviation],
            "y_mean": y_mean,
            "y_standard_deviation": y_standard_deviation,
            "scale": active.scale,
        },
        "latent_components": {
            "x_weights": _matrix(selected_model.x_weights_),
            "y_weights": _matrix(selected_model.y_weights_),
            "x_loadings": _matrix(selected_model.x_loadings_),
            "y_loadings": _matrix(selected_model.y_loadings_),
            "x_rotations": _matrix(selected_model.x_rotations_),
            "score_row_indices": [parsed.row_indices[index] for index in plot_indices],
            "x_scores": _matrix(np.asarray(selected_model.x_scores_)[plot_indices]),
            "y_scores": _matrix(np.asarray(selected_model.y_scores_)[plot_indices]),
        },
        "diagnostics": {
            "point_limit": active.plot_point_limit,
            "point_count_total": int(parsed.y.size),
            "truncated": len(plot_indices) < parsed.y.size,
            "points": [
                {
                    "row_index": parsed.row_indices[index],
                    "observed": float(parsed.y[index]),
                    "fitted": float(fitted[index]),
                    "cross_validated_fitted": float(selected_cv_fitted[index]),
                    "residual": float(residuals[index]),
                    "cross_validated_residual": float(cv_residuals[index]),
                }
                for index in plot_indices
            ],
        },
        "training_ranges": [
            {
                "column_id": column.column_id,
                "minimum": float(np.min(parsed.x[:, index])),
                "maximum": float(np.max(parsed.x[:, index])),
            }
            for index, column in enumerate(predictor_columns)
        ],
        "warnings": warnings_list,
    }


def predict_from_pls_basis(
    values: Sequence[float],
    *,
    coefficients: Sequence[float],
    effective_intercept: float,
) -> float:
    if len(values) != len(coefficients) or len(values) == 0:
        raise PlsRegressionError("pls_model_manifest_invalid")
    prediction = float(effective_intercept) + sum(
        float(value) * float(coefficient)
        for value, coefficient in zip(values, coefficients, strict=True)
    )
    if not isfinite(prediction):
        raise PlsRegressionError("pls_prediction_failed")
    return prediction


def _fit_model(
    x: FloatArray,
    y: FloatArray,
    components: int,
    options: PlsOptions,
) -> tuple[PLSRegression, bool]:
    from sklearn.cross_decomposition import PLSRegression  # type: ignore[import-untyped]
    from sklearn.exceptions import ConvergenceWarning  # type: ignore[import-untyped]

    model = PLSRegression(
        n_components=components,
        scale=options.scale,
        max_iter=options.max_iter,
        tol=options.tol,
        copy=True,
    )
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ConvergenceWarning)
            model.fit(x, y.reshape(-1, 1))
    except (FloatingPointError, ValueError) as exc:
        raise PlsRegressionError("pls_model_fit_failed") from exc
    converged = not any(issubclass(item.category, ConvergenceWarning) for item in caught)
    return model, converged


def _predict(model: PLSRegression, x: FloatArray) -> FloatArray:
    values = np.asarray(model.predict(x), dtype=np.float64).reshape(-1)
    if values.size != x.shape[0] or not np.all(np.isfinite(values)):
        raise PlsRegressionError("pls_model_fit_failed")
    return values


def _cross_validated_predictions(
    x: FloatArray,
    y: FloatArray,
    components: int,
    splits: Sequence[tuple[NDArray[np.int64], NDArray[np.int64]]],
    options: PlsOptions,
) -> FloatArray:
    predicted = np.full(y.shape, np.nan, dtype=np.float64)
    try:
        for training, validation in splits:
            model, _converged = _fit_model(x[training], y[training], components, options)
            predicted[validation] = _predict(model, x[validation])
    except PlsRegressionError as exc:
        raise PlsRegressionError("pls_cross_validation_failed") from exc
    if not np.all(np.isfinite(predicted)):
        raise PlsRegressionError("pls_cross_validation_failed")
    return predicted


def _cross_validation_splits(
    n_samples: int,
    options: PlsOptions,
) -> list[tuple[NDArray[np.int64], NDArray[np.int64]]]:
    from sklearn.model_selection import KFold, LeaveOneOut  # type: ignore[import-untyped]

    if options.cv_method == "leave_one_out":
        if n_samples > MAX_PLS_LOO_ROWS:
            raise PlsRegressionError("pls_leave_one_out_limit")
        splitter = LeaveOneOut()
    elif options.cv_method == "k_fold":
        if options.cv_folds < 2 or options.cv_folds > 10 or options.cv_folds >= n_samples:
            raise PlsRegressionError("pls_cv_fold_count_invalid")
        splitter = KFold(
            n_splits=options.cv_folds,
            shuffle=options.cv_shuffle,
            random_state=options.cv_seed if options.cv_shuffle else None,
        )
    else:
        raise PlsRegressionError("pls_cv_group_invalid")
    return [(training, validation) for training, validation in splitter.split(np.arange(n_samples))]


def _select_components(rows: Sequence[dict[str, object]]) -> int:
    if not rows:
        raise PlsRegressionError("pls_component_count_invalid")
    best = 1
    best_value = float(cast(float, rows[0]["predicted_r_squared"]))
    for index, row in enumerate(rows[1:], start=2):
        value = float(cast(float, row["predicted_r_squared"]))
        if value > best_value + COMPONENT_TIE_TOLERANCE:
            best = index
            best_value = value
    return best


def _cumulative_x_variance(model: PLSRegression, x: FloatArray, scale: bool) -> float:
    centered = x - np.mean(x, axis=0)
    if scale:
        centered = centered / np.std(x, axis=0, ddof=1)
    reconstructed = np.asarray(model.x_scores_) @ np.asarray(model.x_loadings_).T
    sst = float(np.sum(np.square(centered)))
    if sst <= 0.0:
        raise PlsRegressionError("pls_constant_predictor")
    value = 1.0 - (float(np.sum(np.square(centered - reconstructed))) / sst)
    if not isfinite(value):
        raise PlsRegressionError("pls_model_fit_failed")
    if -COMPONENT_TIE_TOLERANCE < value < 0.0:
        return 0.0
    if 1.0 < value < 1.0 + COMPONENT_TIE_TOLERANCE:
        return 1.0
    return value


def _parse_rows(
    rows: Iterable[Sequence[str | None]],
    response: PlsColumn,
    predictors: Sequence[PlsColumn],
    *,
    decimal: str,
    thousands: str | None,
) -> _ParsedRows:
    x_rows: list[list[float]] = []
    y_values: list[float] = []
    indices: list[int] = []
    n_total = 0
    n_missing = 0
    n_non_numeric = 0
    for row_index, row in enumerate(rows):
        n_total += 1
        parsed_values = [
            _parse_number(_row_value(row, column.column_index), decimal, thousands)
            for column in (response, *predictors)
        ]
        if any(invalid for _value, invalid in parsed_values):
            n_non_numeric += 1
            continue
        if any(value is None for value, _invalid in parsed_values):
            n_missing += 1
            continue
        numeric = [float(value) for value, _invalid in parsed_values if value is not None]
        y_values.append(numeric[0])
        x_rows.append(numeric[1:])
        indices.append(row_index)
    return _ParsedRows(
        x=np.asarray(x_rows, dtype=np.float64),
        y=np.asarray(y_values, dtype=np.float64),
        row_indices=indices,
        n_total=n_total,
        n_excluded_missing=n_missing,
        n_excluded_non_numeric=n_non_numeric,
    )


def _parse_number(
    raw: str | None,
    decimal: str,
    thousands: str | None,
) -> tuple[float | None, bool]:
    if raw is None or raw.strip() == "":
        return None, False
    normalized = raw.strip()
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    try:
        value = Decimal(normalized)
    except InvalidOperation:
        return None, True
    if not value.is_finite() or not isfinite(float(value)):
        return None, True
    return float(value), False


def _validate_columns(response: PlsColumn, predictors: Sequence[PlsColumn]) -> None:
    if response.data_type not in {"integer", "decimal"} or response.role == "id":
        raise PlsRegressionError("pls_response_type_unsupported")
    if not 2 <= len(predictors) <= MAX_PLS_PREDICTORS:
        raise PlsRegressionError("pls_predictors_too_few")
    ids = [column.column_id for column in predictors]
    if len(set(ids)) != len(ids) or response.column_id in ids:
        raise PlsRegressionError("pls_component_count_invalid")
    if any(
        column.data_type not in {"integer", "decimal"} or column.role == "id"
        for column in predictors
    ):
        raise PlsRegressionError("pls_predictor_type_unsupported")


def _validate_sample(
    parsed: _ParsedRows,
    predictors: Sequence[PlsColumn],
    options: PlsOptions,
) -> None:
    n_used = parsed.y.size
    if n_used < 4:
        raise PlsRegressionError("pls_usable_rows_too_few")
    if n_used > MAX_PLS_USABLE_ROWS:
        raise PlsRegressionError("pls_usable_rows_limit")
    if not np.all(np.isfinite(parsed.x)) or not np.all(np.isfinite(parsed.y)):
        raise PlsRegressionError("pls_model_fit_failed")
    if float(np.ptp(parsed.y)) == 0.0:
        raise PlsRegressionError("pls_constant_response")
    if any(float(np.ptp(parsed.x[:, index])) == 0.0 for index in range(len(predictors))):
        raise PlsRegressionError("pls_constant_predictor")
    if options.max_iter < 1 or options.max_iter > 10_000:
        raise PlsRegressionError("pls_component_count_invalid")
    if not 0.0 < options.tol <= 0.1:
        raise PlsRegressionError("pls_component_count_invalid")
    if not 100 <= options.plot_point_limit <= 5000:
        raise PlsRegressionError("pls_component_count_invalid")


def _warning_codes(
    *,
    selection_rows: Sequence[dict[str, object]],
    selected_row: dict[str, object],
    selected_components: int,
    maximum_evaluated: int,
    converged: bool,
    excluded: int,
) -> list[str]:
    codes = ["pls_predictive_not_causal", "pls_no_classical_coefficient_p_values"]
    predicted = float(cast(float, selected_row["predicted_r_squared"]))
    training = float(cast(float, selected_row["training_r_squared"]))
    if predicted < 0.0:
        codes.append("pls_negative_predicted_r_squared")
    if selected_components == maximum_evaluated and maximum_evaluated > 1:
        codes.append("pls_selected_maximum_component")
    if training - predicted > 0.2:
        codes.append("pls_training_r_squared_much_higher_than_cv")
    if not converged or any(not bool(row["converged"]) for row in selection_rows):
        codes.append("pls_model_not_converged")
    if excluded:
        codes.append("missing_values_excluded")
    return codes


def _evenly_spaced_indices(count: int, limit: int) -> list[int]:
    if count <= limit:
        return list(range(count))
    return sorted({int(value) for value in np.linspace(0, count - 1, limit)})


def _column_payload(column: PlsColumn) -> dict[str, object]:
    return {
        "column_id": column.column_id,
        "display_name": column.display_name,
        "data_type": column.data_type,
        "measurement_level": column.measurement_level,
        "role": column.role,
        "unit": column.unit,
    }


def _matrix(value: object) -> list[list[float]]:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise PlsRegressionError("pls_model_fit_failed")
    return [[float(item) for item in row] for row in array]


def _row_value(row: Sequence[str | None], index: int) -> str | None:
    return row[index] if index < len(row) else None
