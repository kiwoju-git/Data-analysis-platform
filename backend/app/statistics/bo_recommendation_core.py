"""New BO policy orchestration; legacy wrappers keep their original calculations."""

from __future__ import annotations

import math
import time
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError

RESULT_SCHEMA_VERSION = 2
ITEM_SCHEMA_VERSION = 2
CONFIG_SCHEMA_VERSION = 2
METHOD_VERSION = "0.7.0"
POLICY_VERSION = "greedy_mc_joint_latent_improvement_v2"


def calculate_noise_aware_batch(payload: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    from app.statistics.bayesian_batch import _validated_batch_options, _validated_objective
    from app.statistics.bayesian_optimization import (
        _constraint_evaluations,
        _SearchBudget,
        _validated_constraints,
        _validated_excluded_points,
        _validated_factors,
    )
    from app.statistics.bo_acquisition import build_acquisition_context
    from app.statistics.bo_batch_acquisition import BoBatchAcquisition
    from app.statistics.bo_mixed_search import search_mixed_acquisition
    from app.statistics.bo_observation_groups import (
        BoObservationGroupsError,
        prepare_bo_observation_view,
    )
    from app.statistics.bo_surrogate import BoSurrogatePolicy, fit_bo_surrogate

    started = time.perf_counter()
    factors = _validated_factors(payload.get("factors"))
    constraints = _validated_constraints(payload.get("constraints"), factors)
    excluded = _validated_excluded_points(payload.get("excluded_normalized"), factors)
    options = _validated_batch_options(payload, policy=POLICY_VERSION)
    objective = _validated_objective(payload.get("objective"))
    expected_kind = (
        "expected_target_improvement"
        if objective["goal_type"] == "match_target"
        else "expected_improvement"
    )
    if options["acquisition_kind"] != expected_kind:
        raise BayesianOptimizationError("bayesian_optimization_acquisition_goal_mismatch")
    observation_policy = payload.get("observation_policy", {})
    if not isinstance(observation_policy, dict) or set(observation_policy) - {
        "mode",
        "nearby_tolerances",
        "nearby_units",
    }:
        raise BayesianOptimizationError("bayesian_observation_mode_invalid")
    try:
        observations = payload.get("observations")
        if not isinstance(observations, list):
            raise BoObservationGroupsError("bayesian_observations_invalid")
        view = prepare_bo_observation_view(observations, factors, **observation_policy)
    except BoObservationGroupsError as exc:
        raise BayesianOptimizationError(exc.code) from exc
    try:
        policy = BoSurrogatePolicy(**payload.get("surrogate", {}))
    except (TypeError, ValueError) as exc:
        raise BayesianOptimizationError("bayesian_surrogate_noise_invalid") from exc
    batch_options = payload.get("batch_options", {})
    if not isinstance(batch_options, dict) or set(batch_options) - {
        "posterior_sample_count",
        "min_batch_distance_normalized",
    }:
        raise BayesianOptimizationError("bayesian_batch_acquisition_input_invalid")
    sample_count = batch_options.get("posterior_sample_count", 64)
    distance = batch_options.get("min_batch_distance_normalized", 0.0)
    if (
        isinstance(sample_count, bool)
        or not isinstance(sample_count, int)
        or not 16 <= sample_count <= 256
        or isinstance(distance, bool)
        or not isinstance(distance, int | float)
        or not math.isfinite(distance)
        or distance < 0
    ):
        raise BayesianOptimizationError("bayesian_batch_acquisition_input_invalid")
    deadline = started + options["time_budget_ms"] / 1000
    budget = _SearchBudget(started, deadline, options["max_evaluations_total"])
    model = fit_bo_surrogate(
        view.raw_x,
        view.raw_y,
        policy,
        options,
        deadline=deadline,
        goal_type=objective["goal_type"],
        group_member_indices=tuple(group.member_indices for group in view.groups)
        if view.mode == "exact_replicates"
        else None,
    )
    context, incumbent = build_acquisition_context(
        model,
        view.raw_x,
        view.raw_y,
        list(view.trial_ids),
        goal_type=objective["goal_type"],
        xi_standardized=options["xi_standardized"],
        target_value=objective["target_value"],
    )
    warnings = list(model.warning_codes)
    warnings.extend(
        [
            "bayesian_optimization_confirmation_required",
            "bayesian_optimization_no_global_optimum_guarantee",
            "bayesian_plugin_incumbent_not_exact_noisy_ei",
        ]
    )
    selected: list[list[float]] = []
    items, searches = [], []
    raw_evaluations = sample_evaluations = 0
    factor_ids = [factor["factor_id"] for factor in factors]
    for step in range(options["batch_size"]):
        acquisition = BoBatchAcquisition(
            model,
            context,
            np.asarray(selected).reshape((-1, len(factors))),
            sample_count=sample_count,
            root_seed=options["random_seed"],
            step=step,
        )

        def consume(count: int, step_index: int = step) -> None:
            nonlocal budget, raw_evaluations, sample_evaluations
            # One work unit is at most 64 conditional analytic evaluations.
            weight = max(1, math.ceil(sample_count / 64)) if step_index else 1
            budget = budget.consume(count * weight)
            raw_evaluations += count
            sample_evaluations += count * (sample_count if step_index else 1)

        def score(points: Any, step_acquisition: BoBatchAcquisition = acquisition) -> Any:
            return step_acquisition.score(points).scores_scaled

        with threadpool_limits(limits=1):
            found = search_mixed_acquisition(
                factors=factors,
                constraints=constraints,
                score=score,
                seed=(options["random_seed"] + 104729 * step) % (2**32),
                pool_size=options["candidate_count_per_step"],
                local_start_count=options["local_start_count_per_step"],
                local_maxiter=options["max_iterations_per_step"],
                excluded_normalized=excluded,
                selected_normalized=selected,
                duplicate_tolerance=options["duplicate_tolerance"],
                min_batch_distance_normalized=distance,
                consume=consume,
            )
            consume(1)
            point = np.asarray([found.normalized_coordinates])
            values = acquisition.score(point)
        raw_mean = model.direction_multiplier * (
            float(values.mean_scaled[0]) * model.normalization_scale + model.normalization_mean
        )
        latent_sd = math.sqrt(float(values.latent_variance_scaled[0])) * model.normalization_scale
        predictive_sd = (
            math.sqrt(float(values.predictive_variance_scaled[0])) * model.normalization_scale
        )
        acquisition_scaled = float(values.scores_scaled[0])
        acquisition_raw = acquisition_scaled * model.normalization_scale
        if not all(
            math.isfinite(value) for value in (raw_mean, latent_sd, predictive_sd, acquisition_raw)
        ):
            raise BayesianOptimizationError("bayesian_optimization_surrogate_fit_failed")
        if found.metadata.get("all_scores_zero") or acquisition_scaled == 0:
            warnings.append("bayesian_acquisition_numerically_zero")
        planning = {
            **acquisition.metadata(),
            "conditional_latent_sd_scaled": math.sqrt(float(values.conditional_variance_scaled[0])),
            "conditional_variance_adjustment_max_scaled": (
                values.conditional_variance_adjustment_max_scaled
            ),
        }
        items.append(
            {
                "rank": step + 1,
                "actual_coordinates": found.actual_coordinates,
                "normalized_coordinates": dict(
                    zip(factor_ids, found.normalized_coordinates, strict=True)
                ),
                "predicted_objective_mean": raw_mean,
                "latent_standard_deviation": latent_sd,
                "predictive_standard_deviation": predictive_sd,
                "acquisition_kind": expected_kind,
                "acquisition_value_standardized": acquisition_scaled,
                "acquisition_value_raw": acquisition_raw,
                "planning": planning,
                "nearest_existing_distance": _nearest(found.normalized_coordinates, excluded),
                "nearest_selected_distance": _nearest(found.normalized_coordinates, selected),
                "constraint_evaluations": _constraint_evaluations(
                    found.actual_coordinates, constraints
                ),
            }
        )
        selected.append(found.normalized_coordinates)
        searches.append(found.metadata)
    if time.perf_counter() >= deadline:
        raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
    shared_model = {
        **model.metadata(),
        "objective_goal_type": objective["goal_type"],
        "target_scaled": context.target_scaled,
    }
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "batch_policy": POLICY_VERSION,
        "batch_size": options["batch_size"],
        "shared_model": shared_model,
        "incumbent": incumbent,
        "observation_view": view.provenance(),
        "items": items,
        "search_budget": {
            "max_evaluations_total": options["max_evaluations_total"],
            "evaluations_consumed": budget.evaluations,
            "evaluation_unit": "candidate_or_64_conditional_acquisition_samples",
            "raw_candidate_evaluations": raw_evaluations,
            "conditional_acquisition_sample_evaluations": sample_evaluations,
            "time_budget_ms": options["time_budget_ms"],
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "min_batch_distance_normalized": distance,
            "searches": searches,
            "termination_reason": "search_completed",
        },
        "warnings": list(dict.fromkeys(warnings)),
        "limitations": [
            "bayesian_plugin_incumbent_not_exact_noisy_ei",
            "bayesian_homoscedastic_independent_measurement_noise",
            "bayesian_batch_rank_not_success_probability",
            "bayesian_optimization_no_global_optimum_guarantee",
        ],
    }


def _nearest(point: list[float], others: list[Any]) -> float | None:
    import numpy as np

    if len(others) == 0:
        return None
    return float(np.linalg.norm(np.asarray(others) - np.asarray(point), axis=1).min())
