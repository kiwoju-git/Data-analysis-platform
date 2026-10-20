"""RSM terms are exponent vectors, never parsed display labels."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from typing import Literal

import numpy as np

RsmTermPreset = Literal["linear", "linear_squares", "linear_interactions", "full_quadratic"]


@dataclass(frozen=True)
class RsmBasisTerm:
    term_id: str
    label: str
    kind: Literal["intercept", "main_effect", "interaction", "quadratic"]
    powers: tuple[int, ...]
    depends_on: tuple[str, ...]


def rsm_basis_terms(
    factor_names: Sequence[str], preset: RsmTermPreset = "full_quadratic"
) -> list[RsmBasisTerm]:
    if preset not in {"linear", "linear_squares", "linear_interactions", "full_quadratic"}:
        raise ValueError("doe_rsm_term_preset_invalid")
    count = len(factor_names)
    if not 2 <= count <= 5 or len(set(factor_names)) != count:
        raise ValueError("doe_rsm_analysis_factors_invalid")
    terms = [RsmBasisTerm("intercept", "Intercept", "intercept", (0,) * count, ())]
    for index, name in enumerate(factor_names):
        terms.append(
            RsmBasisTerm(
                f"factor_{index + 1}",
                name,
                "main_effect",
                tuple(int(position == index) for position in range(count)),
                (),
            )
        )
    # Keep the existing full-quadratic column order for numeric compatibility.
    if preset in {"linear_interactions", "full_quadratic"}:
        for first, second in combinations(range(count), 2):
            terms.append(
                RsmBasisTerm(
                    f"factor_{first + 1}:factor_{second + 1}",
                    f"{factor_names[first]} * {factor_names[second]}",
                    "interaction",
                    tuple(int(position in (first, second)) for position in range(count)),
                    (f"factor_{first + 1}", f"factor_{second + 1}"),
                )
            )
    if preset in {"linear_squares", "full_quadratic"}:
        for index, name in enumerate(factor_names):
            terms.append(
                RsmBasisTerm(
                    f"factor_{index + 1}^2",
                    f"{name}^2",
                    "quadratic",
                    tuple(2 if position == index else 0 for position in range(count)),
                    (f"factor_{index + 1}",),
                )
            )
    return terms


def evaluate_rsm_basis(coded: np.ndarray, powers: Sequence[Sequence[int]]) -> np.ndarray:
    values = np.asarray(coded, dtype=float)
    exponents = np.asarray(powers)
    if (
        values.ndim != 2
        or exponents.ndim != 2
        or values.shape[1] != exponents.shape[1]
        or not np.issubdtype(exponents.dtype, np.integer)
        or not bool(np.isfinite(values).all())
        or bool(np.any(exponents < 0))
        or bool(np.any(np.sum(exponents, axis=1) > 2))
    ):
        raise ValueError("doe_rsm_basis_invalid")
    with np.errstate(over="ignore", invalid="ignore"):
        matrix = np.prod(values[:, None, :] ** exponents[None, :, :], axis=2)
    if not bool(np.isfinite(matrix).all()):
        raise ValueError("doe_rsm_basis_not_finite")
    return matrix


def predict_rsm_basis(
    coded: Sequence[float],
    powers: Sequence[Sequence[int]],
    coefficients: Sequence[float] | np.ndarray,
) -> float:
    matrix = evaluate_rsm_basis(np.asarray([coded]), powers)
    beta = np.asarray(coefficients, dtype=float)
    if beta.shape != (matrix.shape[1],) or not bool(np.isfinite(beta).all()):
        raise ValueError("doe_rsm_basis_invalid")
    value = float(matrix[0] @ beta)
    if not isfinite(value):
        raise ValueError("doe_rsm_prediction_not_finite")
    return value
