from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from math import isfinite
from typing import Literal

import numpy as np
from scipy.stats import chi2

MatrixType = Literal["correlation", "covariance"]
ComponentSelection = Literal["all", "fixed", "cumulative_threshold"]


class PrincipalComponentsError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PrincipalComponentsColumn:
    column_id: str
    column_index: int
    display_name: str
    data_type: str
    measurement_level: str
    role: str
    unit: str | None


@dataclass(frozen=True)
class PrincipalComponentsOptions:
    matrix_type: MatrixType = "correlation"
    component_selection: ComponentSelection = "all"
    component_count: int | None = None
    cumulative_threshold: float = 0.9
    outlier_alpha: float = 0.05
    plot_point_limit: int = 5000


def calculate_principal_components(
    rows: Iterable[Sequence[str | None]],
    columns: list[PrincipalComponentsColumn],
    *,
    decimal: str = ".",
    thousands: str | None = None,
    options: PrincipalComponentsOptions | None = None,
) -> dict[str, object]:
    resolved = options or PrincipalComponentsOptions()
    if not 2 <= len(columns) <= 50:
        raise PrincipalComponentsError("pca_variable_count_invalid")

    n_total = 0
    n_excluded_missing = 0
    n_excluded_non_numeric = 0
    complete_rows: list[list[float]] = []
    source_row_numbers: list[int] = []
    for source_row_number, row in enumerate(rows, start=1):
        n_total += 1
        parsed_row: list[float] = []
        missing = False
        non_numeric = False
        for column in columns:
            raw = row[column.column_index] if column.column_index < len(row) else None
            if raw is None or raw.strip() == "":
                missing = True
                break
            number = _parse_number(raw, decimal=decimal, thousands=thousands)
            if number is None:
                non_numeric = True
                break
            parsed_row.append(number)
        if missing:
            n_excluded_missing += 1
        elif non_numeric:
            n_excluded_non_numeric += 1
        else:
            complete_rows.append(parsed_row)
            source_row_numbers.append(source_row_number)

    if len(complete_rows) < 3:
        raise PrincipalComponentsError("pca_usable_rows_too_few")
    if len(complete_rows) > 20_000:
        raise PrincipalComponentsError("pca_usable_rows_limit")

    matrix = np.asarray(complete_rows, dtype=np.float64)
    means = np.mean(matrix, axis=0)
    sample_standard_deviations = np.std(matrix, axis=0, ddof=1)
    if np.any(~np.isfinite(sample_standard_deviations)) or np.any(sample_standard_deviations <= 0):
        raise PrincipalComponentsError("pca_constant_variable")

    centered = matrix - means
    if resolved.matrix_type == "correlation":
        transformed = centered / sample_standard_deviations
        standardized = True
    elif resolved.matrix_type == "covariance":
        transformed = centered
        standardized = False
    else:
        raise PrincipalComponentsError("pca_matrix_type_invalid")

    sample_matrix = transformed.T @ transformed / (matrix.shape[0] - 1)
    eigenvalues, eigenvectors = np.linalg.eigh(sample_matrix)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    tolerance = max(1.0, float(np.max(np.abs(eigenvalues)))) * 1e-12
    if np.any(eigenvalues < -tolerance):
        raise PrincipalComponentsError("pca_eigendecomposition_failed")
    eigenvalues = np.where(eigenvalues < 0, 0.0, eigenvalues)

    maximum_components = min(matrix.shape[1], matrix.shape[0] - 1)
    eigenvalues = eigenvalues[:maximum_components]
    eigenvectors = eigenvectors[:, :maximum_components]
    eigenvectors = _normalize_component_signs(eigenvectors)
    scores = transformed @ eigenvectors
    loadings = eigenvectors * np.sqrt(eigenvalues)

    total_eigenvalue = float(np.sum(eigenvalues))
    if total_eigenvalue <= 0 or not isfinite(total_eigenvalue):
        raise PrincipalComponentsError("pca_eigendecomposition_failed")
    proportions = eigenvalues / total_eigenvalue
    cumulative = np.cumsum(proportions)
    selected_components = _selected_component_count(
        resolved,
        maximum_components=maximum_components,
        cumulative=cumulative,
    )

    selected_eigenvalues = eigenvalues[:selected_components]
    positive = selected_eigenvalues > tolerance
    if not np.any(positive):
        raise PrincipalComponentsError("pca_eigendecomposition_failed")
    distances_squared = np.sum(
        np.square(scores[:, :selected_components][:, positive]) / selected_eigenvalues[positive],
        axis=1,
    )
    reference = float(chi2.ppf(1.0 - resolved.outlier_alpha, int(np.sum(positive))))
    outlier_flags = distances_squared > reference

    score_rows = [
        {
            "source_row_number": source_row_numbers[index],
            "scores": [float(value) for value in scores[index, :]],
            "mahalanobis_distance_squared": float(distances_squared[index]),
            "outlier": bool(outlier_flags[index]),
        }
        for index in range(matrix.shape[0])
    ]
    preview_indices = _preview_indices(outlier_flags, resolved.plot_point_limit)

    warnings: list[str] = []
    if n_excluded_missing or n_excluded_non_numeric:
        warnings.append("pca_complete_case_rows_excluded")
    if len(preview_indices) < len(score_rows):
        warnings.append("pca_chart_points_limited")
    if matrix.shape[1] >= matrix.shape[0]:
        warnings.append("pca_variables_not_less_than_rows")

    return {
        "schema_version": 1,
        "summary_type": "principal_components_analysis",
        "method": "sample_correlation_eigendecomposition"
        if resolved.matrix_type == "correlation"
        else "sample_covariance_eigendecomposition",
        "missing_policy": "complete_case",
        "sample": {
            "n_total": n_total,
            "n_used": len(score_rows),
            "n_excluded": n_total - len(score_rows),
            "n_excluded_missing": n_excluded_missing,
            "n_excluded_non_numeric": n_excluded_non_numeric,
            "variable_count": len(columns),
        },
        "variables": [
            {
                "column_id": column.column_id,
                "display_name": column.display_name,
                "unit": column.unit,
                "mean": float(means[index]),
                "sample_standard_deviation": float(sample_standard_deviations[index]),
            }
            for index, column in enumerate(columns)
        ],
        "preprocessing": {
            "matrix_type": resolved.matrix_type,
            "centered": True,
            "standardized": standardized,
            "degrees_of_freedom": 1,
        },
        "matrix": [[float(value) for value in row] for row in sample_matrix],
        "component_selection": {
            "mode": resolved.component_selection,
            "requested_component_count": resolved.component_count,
            "cumulative_threshold": resolved.cumulative_threshold,
            "maximum_components": maximum_components,
            "selected_components": selected_components,
            "selected_cumulative_proportion": float(cumulative[selected_components - 1]),
        },
        "eigenanalysis": [
            {
                "component": index + 1,
                "eigenvalue": float(eigenvalues[index]),
                "proportion": float(proportions[index]),
                "cumulative_proportion": float(cumulative[index]),
                "selected": index < selected_components,
            }
            for index in range(maximum_components)
        ],
        "eigenvectors": [
            {
                "column_id": column.column_id,
                "display_name": column.display_name,
                "values": [float(value) for value in eigenvectors[index, :]],
            }
            for index, column in enumerate(columns)
        ],
        "loadings": [
            {
                "column_id": column.column_id,
                "display_name": column.display_name,
                "values": [float(value) for value in loadings[index, :]],
            }
            for index, column in enumerate(columns)
        ],
        "scores": score_rows,
        "plot": {
            "point_limit": resolved.plot_point_limit,
            "point_count": len(preview_indices),
            "sampled": len(preview_indices) < len(score_rows),
            "sampling_policy": "outliers_then_evenly_spaced",
            "points": [score_rows[index] for index in preview_indices],
        },
        "outliers": {
            "alpha": resolved.outlier_alpha,
            "method": "chi_square_squared_mahalanobis_selected_components",
            "degrees_of_freedom": int(np.sum(positive)),
            "reference_value": reference,
            "count": int(np.sum(outlier_flags)),
        },
        "warnings": warnings,
        "provenance": {
            "algorithm": "numpy.linalg.eigh",
            "sign_policy": "largest_absolute_eigenvector_entry_positive_first_on_tie",
            "score_equation": "transformed_X @ eigenvectors",
        },
    }


def _parse_number(value: str, *, decimal: str, thousands: str | None) -> float | None:
    normalized = value.strip()
    if thousands is not None:
        normalized = normalized.replace(thousands, "")
    if decimal != ".":
        normalized = normalized.replace(decimal, ".")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation:
        return None
    if not parsed.is_finite():
        return None
    return float(parsed)


def _normalize_component_signs(eigenvectors: np.ndarray) -> np.ndarray:
    normalized = eigenvectors.copy()
    for component in range(normalized.shape[1]):
        pivot = int(np.argmax(np.abs(normalized[:, component])))
        if normalized[pivot, component] < 0:
            normalized[:, component] *= -1
    return normalized


def _selected_component_count(
    options: PrincipalComponentsOptions,
    *,
    maximum_components: int,
    cumulative: np.ndarray,
) -> int:
    if options.component_selection == "all":
        return maximum_components
    if options.component_selection == "fixed":
        if (
            options.component_count is None
            or not 1 <= options.component_count <= maximum_components
        ):
            raise PrincipalComponentsError("pca_component_count_invalid")
        return options.component_count
    if options.component_selection == "cumulative_threshold":
        if not 0 < options.cumulative_threshold <= 1:
            raise PrincipalComponentsError("pca_cumulative_threshold_invalid")
        return min(
            maximum_components,
            int(np.searchsorted(cumulative, options.cumulative_threshold, side="left")) + 1,
        )
    raise PrincipalComponentsError("pca_component_selection_invalid")


def _preview_indices(flags: np.ndarray, limit: int) -> list[int]:
    count = len(flags)
    if not 100 <= limit <= 5000:
        raise PrincipalComponentsError("pca_plot_point_limit_invalid")
    if count <= limit:
        return list(range(count))
    outliers = [int(index) for index in np.flatnonzero(flags)]
    keep = outliers[:limit]
    remaining = limit - len(keep)
    if remaining <= 0:
        return sorted(keep)
    candidates = np.flatnonzero(~flags)
    positions = np.linspace(0, len(candidates) - 1, remaining, dtype=int)
    keep.extend(int(candidates[position]) for position in positions)
    return sorted(set(keep))
