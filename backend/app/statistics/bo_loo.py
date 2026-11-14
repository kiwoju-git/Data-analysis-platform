"""Read-only, fixed-full-fit-parameter LOO; not fold-local refitting or Auto routing."""

from __future__ import annotations

import math
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError

POLICY = "fixed_full_fit_parameters_row_loo_v1"
ERROR = "bayesian_loo_diagnostic_invalid"


def conditional_row_loo(model: Any, raw_x: Any, raw_y: Any, trial_ids: list[str]) -> dict[str, Any]:
    """GPML eq. 5.12 on raw trials, even when the saved fit compressed repeats."""
    import numpy as np
    from scipy.linalg import cho_solve, cholesky, solve_triangular  # type: ignore[import-untyped]

    x, y = np.asarray(raw_x, dtype=float), np.asarray(raw_y, dtype=float)
    n = len(trial_ids)
    if (
        not 2 <= n <= 200
        or len(set(trial_ids)) != n
        or any(not isinstance(key, str) or not key for key in trial_ids)
        or x.ndim != 2
        or x.shape != (n, model.x_train.shape[1])
        or y.shape != (n,)
        or not np.all(np.isfinite(x))
        or not np.all(np.isfinite(y))
        or model.raw_observation_count != n
        or model.direction_multiplier != 1
    ):
        raise BayesianOptimizationError(ERROR)
    signal, noise = model._signal_and_noise()
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            target = (y - model.normalization_mean) / model.normalization_scale
            covariance = signal(x) + np.eye(n) * (noise + model.jitter)
            lower = cholesky(covariance, lower=True, check_finite=True)
            alpha = cho_solve((lower, True), target, check_finite=True)
            inverse_lower = solve_triangular(lower, np.eye(n), lower=True, check_finite=True)
            precision_diagonal = np.sum(inverse_lower**2, axis=0)
            if np.any(precision_diagonal <= 0) or not np.all(np.isfinite(precision_diagonal)):
                raise BayesianOptimizationError(ERROR)
            error_scaled = alpha / precision_diagonal
            predicted = model.normalization_mean + model.normalization_scale * (
                target - error_scaled
            )
            residual = error_scaled * model.normalization_scale
            error_norm = math.hypot(*error_scaled)
            rmse = error_norm * (model.normalization_scale / math.sqrt(n))
            centered = target - np.mean(target)
            centered_norm = math.hypot(*centered)
            r_squared = None if centered_norm == 0 else 1 - (error_norm / centered_norm) ** 2
        if (
            not np.all(np.isfinite(predicted))
            or not np.all(np.isfinite(residual))
            or not math.isfinite(rmse)
            or (error_norm > 0 and rmse == 0)
            or (r_squared is not None and not math.isfinite(r_squared))
        ):
            raise BayesianOptimizationError(ERROR)
    except (ValueError, np.linalg.LinAlgError, FloatingPointError, OverflowError):
        raise BayesianOptimizationError(ERROR) from None
    return {
        "raw_observation_count": n,
        "effective_training_count": len(model.x_train),
        "n_scored": n,
        "rmse": rmse,
        "r_squared": r_squared,
        "r_squared_reason": "constant_observations" if r_squared is None else None,
        "points": [
            {
                "trial_id": key,
                "observation_index": i + 1,
                "observed": float(y[i]),
                "predicted": float(predicted[i]),
                "residual": float(residual[i]),
            }
            for i, key in enumerate(trial_ids)
        ],
    }


def planning_loo(snapshot: dict[str, Any], *, mixed: bool = False) -> dict[str, Any]:
    """Only validated saved model state and its exact historical observations are read."""
    restored: Any
    views: Any
    if snapshot.get("policy") == "source_locked_mixture_bo_planning_model_v1":
        from app.statistics.bo_mixture_planning import restore_mixture_planning_model

        restored = restore_mixture_planning_model(snapshot)
        encoded = [
            restored.design.canonical(row["actual_coordinates"])[1] for row in restored.observations
        ]
        raw_x = {response.response_id: encoded for response in restored.objective.responses}
        mixed = snapshot["inner_model_kind"] == "mixed"
    elif mixed:
        from app.statistics.bo_mixed_planning import _training_views, restore_mixed_planning_model

        restored = restore_mixed_planning_model(snapshot)
        views, _ = _training_views(restored.request)
        raw_x = {key: view.raw_x for key, view in views.items()}
    else:
        from app.statistics.bo_candidate_points import candidate_factors
        from app.statistics.bo_desirability_core import _observation_views
        from app.statistics.bo_planning_model import restore_planning_model

        restored = restore_planning_model(snapshot)
        raw = restored.request.q1_request().worker_payload()
        views = _observation_views(raw, restored.goals, candidate_factors(raw["factors"]))
        raw_x = {key: view.raw_x for key, view in views.items()}
    rows = snapshot["calculation_request"]["observations"]
    definitions = snapshot["calculation_request"]["objective"]["responses"]
    return {
        "schema_version": 1,
        "policy": POLICY,
        "evaluation_unit": "individual_observed_trial",
        "normalization_policy": "frozen_full_fit_mean_scale",
        "r_squared_policy": "one_minus_press_over_raw_centered_tss",
        "model_refit": False,
        "auto_routing_applied": False,
        "warnings": [
            "full_fit_parameters_include_held_out_observation",
            "not_external_validation",
            "repeats_are_not_new_condition_validation",
        ]
        + (["category_vocabulary_and_parameters_frozen"] if mixed else []),
        "responses": [
            {
                "response_id": definition["response_id"],
                **conditional_row_loo(
                    restored.models[definition["response_id"]],
                    raw_x[definition["response_id"]],
                    [row["response_values"][definition["response_id"]] for row in rows],
                    [row["trial_id"] for row in rows],
                ),
            }
            for definition in definitions
        ],
    }
