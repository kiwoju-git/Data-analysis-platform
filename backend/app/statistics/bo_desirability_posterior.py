"""Read-only bridge from explicitly keyed BO models to desirability moments.

No fit, acquisition search, history update, or artifact serialization occurs here.
Only actual-data base posteriors belong in this interface, not fantasy models.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import (
    DesirabilityGoal,
    DesirabilityMoments,
    finite_number,
    independent_desirability_moments,
    normalized_importance,
)
from app.statistics.bo_surrogate import BoSurrogate


@dataclass(frozen=True)
class DesirabilityResponsePosterior:
    response_id: str
    mean_raw: float
    latent_standard_deviation_raw: float
    predictive_standard_deviation_raw: float


@dataclass(frozen=True)
class SurrogateDesirability:
    moments: DesirabilityMoments
    responses: tuple[DesirabilityResponsePosterior, ...]


def raw_posterior_standard_deviation(variance_scaled: float, scale: float) -> float:
    variance, multiplier = finite_number(variance_scaled), finite_number(scale)
    if variance < 0 or multiplier <= 0:
        raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid")
    value = math.sqrt(variance) * multiplier
    if not math.isfinite(value) or (variance > 0 and value == 0):
        # Retain the existing worker/API numeric-error contract for q1. This is
        # raw-unit representability, not a failure of the Beta approximation.
        raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
    return value


def evaluate_surrogate_desirability(
    models: Mapping[str, BoSurrogate],
    goals: Sequence[DesirabilityGoal],
    normalized_coordinates: Any,
) -> SurrogateDesirability:
    """Evaluate one explicit candidate with raw-response, independent GP models.

    Minimize is a desirability curve, not a sign change of the fitted response.
    Measurement noise is reported separately and is not used in the integral.
    """
    import numpy as np

    normalized_importance(goals)
    if set(models) != {g.response_id for g in goals}:
        raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")
    try:
        if not isinstance(normalized_coordinates, np.ndarray):
            for scalar in np.asarray(normalized_coordinates, dtype=object).flat:
                finite_number(scalar)
        raw = np.asarray(normalized_coordinates)
        if raw.dtype.kind not in "iuf":
            raise ValueError
        x = raw.astype(float, copy=False)
        if (
            x.ndim != 1
            or not 1 <= len(x) <= 10
            or not np.all(np.isfinite(x))
            or np.any((x < 0) | (x > 1))
        ):
            raise ValueError
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid") from exc
    responses = []
    for goal in goals:
        model = models[goal.response_id]
        if model.direction_multiplier != 1 or model.x_train.shape[1] != len(x):
            raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid")
        scale = finite_number(model.normalization_scale)
        center = finite_number(model.normalization_mean)
        if scale <= 0:
            raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid")
        prediction = model.predict(x.reshape(1, -1))
        latent = finite_number(prediction.latent_variance_scaled[0])
        predictive = finite_number(prediction.predictive_variance_scaled[0])
        if latent < 0 or predictive < latent:
            raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid")
        responses.append(
            DesirabilityResponsePosterior(
                goal.response_id,
                finite_number(finite_number(prediction.mean_scaled[0]) * scale + center),
                raw_posterior_standard_deviation(latent, scale),
                raw_posterior_standard_deviation(predictive, scale),
            )
        )
    moments = independent_desirability_moments(
        {r.response_id: (r.mean_raw, r.latent_standard_deviation_raw) for r in responses}, goals
    )
    return SurrogateDesirability(moments, tuple(responses))
