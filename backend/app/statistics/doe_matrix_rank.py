"""One explicit rank policy for new regular-fraction fits; legacy fits are unchanged."""

from __future__ import annotations

import numpy as np


def column_scaled_matrix(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    norms = np.linalg.norm(matrix, axis=0)
    scales = np.where(norms > 0, norms, 1.0)
    return matrix / scales, scales


def doe_matrix_rank(matrix: np.ndarray, tolerance: float | None = None) -> int:
    if tolerance is None:
        return int(np.linalg.matrix_rank(matrix))
    scaled, _ = column_scaled_matrix(matrix)
    return int(np.sum(np.linalg.svd(scaled, compute_uv=False) > tolerance))


def doe_least_squares(
    matrix: np.ndarray,
    response: np.ndarray,
    tolerance: float | None = None,
) -> tuple[np.ndarray, int]:
    if tolerance is None:
        coefficients, _, rank, _ = np.linalg.lstsq(matrix, response, rcond=None)
        return coefficients, int(rank)
    scaled, scales = column_scaled_matrix(matrix)
    u, singular, vh = np.linalg.svd(scaled, full_matrices=False)
    retained = singular > tolerance
    coefficients = vh[retained].T @ ((u[:, retained].T @ response) / singular[retained])
    return coefficients / scales, int(np.sum(retained))
