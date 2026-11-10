"""Bounded q=1 multiresponse desirability calculation, without persistence.

Each GP fits one original response. Desirability is an acquisition payoff, never
a replacement measured response. Legacy single-response EI/ETI stays separate.
"""

from __future__ import annotations

import json
import time
from collections import OrderedDict
from dataclasses import asdict
from typing import Any

from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import (
    CURVE_POLICY,
    MOMENT_POLICY,
    DesirabilityGoal,
    composite_desirability,
    finite_number,
    normalized_importance,
)

RESULT_SCHEMA_VERSION = 4
MODEL_SCHEMA_VERSION = 5
POLICY_VERSION = "independent_latent_desirability_beta_ei_v1"
INCUMBENT_POLICY = "max_posterior_expected_desirability_at_observed_coordinates_v1"
_CACHE_LIMIT = 512


def calculate_desirability_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    from app.statistics.bayesian_optimization import (
        _constraint_evaluations,
        _SearchBudget,
        _validated_constraints,
        _validated_excluded_points,
        _validated_factors,
    )
    from app.statistics.bo_desirability_acquisition import beta_expected_improvement
    from app.statistics.bo_desirability_posterior import (
        SurrogateDesirability,
        evaluate_surrogate_desirability,
    )
    from app.statistics.bo_mixed_search import search_mixed_acquisition

    started = time.perf_counter()
    goals, specifications, options, xi = _validated_configuration(payload)
    factors = _validated_factors(payload["factors"])
    constraints = _validated_constraints(payload["constraints"], factors)
    excluded = _validated_excluded_points(payload["excluded_normalized"], factors)
    views = _observation_views(payload, goals, factors)
    first_view = views[goals[0].response_id]
    factor_ids = list(first_view.factor_ids)
    for point in first_view.raw_x.tolist():
        if point not in excluded:
            excluded.append(point)
    deadline = started + options["time_budget_ms"] / 1000
    budget = _SearchBudget(started, deadline, options["max_evaluations_total"])
    models, model_records, warnings, fit_evaluations = _fit_response_models(
        goals, specifications, options, views, budget
    )

    cache: OrderedDict[tuple[float, ...], SurrogateDesirability] = OrderedDict()
    integrand_evaluations = posterior_evaluations = 0

    def posterior(point: Any) -> SurrogateDesirability:
        nonlocal integrand_evaluations, posterior_evaluations
        budget.consume(0)
        key = tuple(float(value) for value in point)
        if key in cache:
            cache.move_to_end(key)
            return cache[key]
        result = evaluate_surrogate_desirability(models, goals, point)
        integrand_evaluations += result.moments.integration_evaluations
        posterior_evaluations += 1
        budget.consume(0)
        cache[key] = result
        if len(cache) > _CACHE_LIMIT:
            cache.popitem(last=False)
        return result

    with threadpool_limits(limits=1):
        incumbent = _incumbent_result(goals, views, posterior)
        latent_incumbent = incumbent["latent_incumbent_value"]

        def consume(count: int) -> None:
            nonlocal budget
            budget = budget.consume(count)

        def score(points: Any) -> Any:
            scores = []
            for point in points:
                moments = posterior(point).moments
                score_value = beta_expected_improvement(
                    moments.mean, moments.variance, latent_incumbent, xi=xi
                )
                scores.append(score_value.value)
                budget.consume(0)
            return np.asarray(scores, dtype=float)

        found = search_mixed_acquisition(
            factors=factors,
            constraints=constraints,
            score=score,
            seed=options["random_seed"],
            pool_size=options["candidate_count_per_step"],
            local_start_count=options["local_start_count_per_step"],
            local_maxiter=options["max_iterations_per_step"],
            excluded_normalized=excluded,
            duplicate_tolerance=options["duplicate_tolerance"],
            consume=consume,
        )
        consume(1)
        selected = posterior(found.normalized_coordinates)
        acquisition = beta_expected_improvement(
            selected.moments.mean, selected.moments.variance, latent_incumbent, xi=xi
        )
        if acquisition.value != found.acquisition:
            raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
    budget.consume(0)
    if acquisition.value == 0:
        warnings.append("bayesian_acquisition_numerically_zero")
    limitations = [
        "bayesian_desirability_independent_response_posteriors",
        "bayesian_desirability_beta_approximation_not_exact_ei",
        "bayesian_desirability_curve_not_jmp_equivalent",
        "bayesian_plugin_incumbent_not_exact_noisy_ei",
        "bayesian_homoscedastic_independent_measurement_noise",
        "bayesian_optimization_no_global_optimum_guarantee",
    ]
    warnings.extend(["bayesian_optimization_confirmation_required", *limitations])
    result = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "batch_size": 1,
        "policy": POLICY_VERSION,
        "objective": {
            "responses": [dict(response) for response in payload["objective"]["responses"]]
        },
        "shared_model": {
            "schema_version": MODEL_SCHEMA_VERSION,
            "policy_version": 1,
            "factor_ids": factor_ids,
            "response_ids": [goal.response_id for goal in goals],
            "response_models": model_records,
            "normalized_importance": [
                {"response_id": goal.response_id, "weight": weight}
                for goal, weight in zip(goals, normalized_importance(goals), strict=True)
            ],
            "curve_policy": CURVE_POLICY,
            "moment_policy": MOMENT_POLICY,
            "independence_assumption": True,
        },
        "incumbent": incumbent,
        "observation_view": _shared_provenance(first_view),
        "items": [
            {
                "rank": 1,
                "actual_coordinates": found.actual_coordinates,
                "normalized_coordinates": dict(
                    zip(factor_ids, found.normalized_coordinates, strict=True)
                ),
                "response_predictions": [asdict(response) for response in selected.responses],
                "desirability_moments": asdict(selected.moments),
                "acquisition": {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(acquisition),
                    "xi_desirability": xi,
                },
                "nearest_existing_distance": found.metadata["nearest_existing_distance"],
                "constraint_evaluations": _constraint_evaluations(
                    found.actual_coordinates, constraints
                ),
            }
        ],
        "search_budget": {
            "max_evaluations_total": options["max_evaluations_total"],
            "evaluations_consumed": budget.evaluations,
            "evaluation_unit": "candidate_with_all_response_desirability_moments",
            "posterior_evaluations": posterior_evaluations,
            "integrand_evaluations": integrand_evaluations,
            "response_fit_count": len(models),
            "model_max_evaluations_total": options["model_max_evaluations"],
            "model_evaluations_consumed": fit_evaluations,
            "final_factorizations": len(models),
            "time_budget_ms": options["time_budget_ms"],
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "searches": [found.metadata],
            "termination_reason": found.metadata["termination_reason"],
        },
        "warnings": list(dict.fromkeys(warnings)),
        "limitations": limitations,
    }
    try:
        json.dumps(result, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise BayesianOptimizationError("bayesian_desirability_numeric_invalid") from exc
    return result


def _incumbent_result(goals: Any, views: Any, posterior: Any) -> dict[str, Any]:
    first_view = views[goals[0].response_id]
    observed, training = [], []
    for index, trial_id in enumerate(first_view.trial_ids):
        values = {g.response_id: float(views[g.response_id].raw_y[index]) for g in goals}
        observed.append({"trial_id": trial_id, "value": composite_desirability(values, goals)})
        training.append(
            {
                "trial_id": trial_id,
                "moments": asdict(posterior(first_view.raw_x[index]).moments),
            }
        )
    # History order breaks ties. Different response maxima are never combined.
    observed_index = max(range(len(observed)), key=lambda i: observed[i]["value"])
    latent_index = max(range(len(training)), key=lambda i: training[i]["moments"]["mean"])
    return {
        "policy": INCUMBENT_POLICY,
        "best_observed_desirability": observed[observed_index]["value"],
        "best_observed_trial_id": observed[observed_index]["trial_id"],
        "latent_incumbent_value": training[latent_index]["moments"]["mean"],
        "latent_incumbent_trial_id": training[latent_index]["trial_id"],
        "latent_incumbent_normalized_coordinates": dict(
            zip(first_view.factor_ids, first_view.raw_x[latent_index].tolist(), strict=True)
        ),
        "observed_trial_desirabilities": observed,
        "training_posterior_desirabilities": training,
    }


def _validated_configuration(
    payload: dict[str, Any], *, versioned_curves: bool = False
) -> tuple[Any, Any, dict[str, Any], float]:
    from app.statistics.bayesian_batch import _validated_batch_options
    from app.statistics.bo_kernels import BoKernelSpec
    from app.statistics.bo_surrogate import BoSurrogatePolicy

    required = {
        "schema_version",
        "factors",
        "constraints",
        "observations",
        "excluded_normalized",
        "objective",
        "response_models",
        "observation_policy",
        "xi_desirability",
        "search",
    }
    if (
        not isinstance(payload, dict)
        or not required <= set(payload)
        or set(payload) - required - {"batch_size"}
        or type(payload["schema_version"]) is not int
        or payload["schema_version"] != (7 if versioned_curves else 4)
        or type(payload.get("batch_size", 1)) is not int
        or payload.get("batch_size", 1) != 1
    ):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    objective = payload["objective"]
    if (
        not isinstance(objective, dict)
        or set(objective) != {"responses"}
        or not isinstance(objective["responses"], list)
    ):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    goals = []
    for response in objective["responses"]:
        if versioned_curves:
            from app.api.v1.schemas.bo_curve_policy import VersionedCurveObjective

            parsed = VersionedCurveObjective.model_validate(objective)
            goals = [r.calculation_goal() for r in parsed.responses]
            break
        if (
            not isinstance(response, dict)
            or set(response)
            != {"response_id", "name", "unit", "goal", "lower", "target", "upper", "importance"}
            or not isinstance(response["name"], str)
            or not response["name"].strip()
            or (response["unit"] is not None and not isinstance(response["unit"], str))
        ):
            raise BayesianOptimizationError("bayesian_desirability_input_invalid")
        goals.append(
            DesirabilityGoal(**{k: v for k, v in response.items() if k not in {"name", "unit"}})
        )
    normalized_importance(goals)
    xi = finite_number(payload["xi_desirability"])
    if xi < 0:
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    search = payload["search"]
    if not isinstance(search, dict) or "batch_policy" in search:
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    options = _validated_batch_options(
        {
            "search": {**search, "batch_policy": POLICY_VERSION},
            "batch_size": 1,
            "acquisition": {
                "kind": "expected_improvement",
                "exploration_profile": "custom",
                "xi_standardized": 0.0,
            },
        },
        policy=POLICY_VERSION,
    )
    specifications = {}
    if not isinstance(payload["response_models"], list):
        raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")
    for item in payload["response_models"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"response_id", "kernel", "surrogate"}
            or not isinstance(item["response_id"], str)
            or item["response_id"] in specifications
            or not isinstance(item["kernel"], dict)
            or set(item["kernel"]) != {"kind"}
            or not isinstance(item["surrogate"], dict)
        ):
            raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")
        try:
            specifications[item["response_id"]] = (
                BoKernelSpec(**item["kernel"]),
                BoSurrogatePolicy(**item["surrogate"]),
            )
        except (TypeError, ValueError, OverflowError) as exc:
            raise BayesianOptimizationError("bayesian_desirability_model_contract_invalid") from exc
    if set(specifications) != {goal.response_id for goal in goals}:
        raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")
    return goals, specifications, options, xi


def _fit_response_models(
    goals: Any,
    specifications: Any,
    options: dict[str, Any],
    views: Any,
    budget: Any,
    *,
    fit_policy: Any = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], int]:
    from app.statistics.bo_surrogate import fit_bo_surrogate

    models: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    warnings: list[str] = []
    evaluations = 0
    for goal in goals:
        budget.consume(0)
        remaining = options["model_max_evaluations"] - evaluations
        if remaining < 2:
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
        view = views[goal.response_id]
        kernel, noise = specifications[goal.response_id]
        model = fit_bo_surrogate(
            view.raw_x,
            view.raw_y,
            noise,
            {**options, "model_max_evaluations": remaining},
            deadline=budget.deadline,
            goal_type="maximize",
            group_member_indices=tuple(group.member_indices for group in view.groups)
            if view.mode == "exact_replicates"
            else None,
            kernel_spec=kernel,
            **({"fit_policy": fit_policy} if fit_policy is not None else {}),
        )
        evaluations += model.optimizer["evaluations"]
        if evaluations > options["model_max_evaluations"]:
            raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
        models[goal.response_id] = model
        records.append(
            {
                "response_id": goal.response_id,
                "model": {**model.metadata(), "factor_ids": list(view.factor_ids)},
                "observation_view": view.provenance(),
            }
        )
        warnings.extend(model.warning_codes)
        budget.consume(0)
    return models, records, warnings, evaluations


def _observation_views(payload: dict[str, Any], goals: Any, factors: Any) -> dict[str, Any]:
    from app.statistics.bo_observation_groups import (
        BoObservationGroupsError,
        prepare_bo_observation_view,
    )

    rows, policy = payload["observations"], payload["observation_policy"]
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 200
        or not isinstance(policy, dict)
        or set(policy) - {"mode", "nearby_tolerances", "nearby_units"}
    ):
        raise BayesianOptimizationError("bayesian_desirability_input_invalid")
    response_ids = {goal.response_id for goal in goals}
    for row in rows:
        required = {"trial_id", "actual_coordinates", "normalized_coordinates", "response_values"}
        if (
            not isinstance(row, dict)
            or not required <= set(row)
            or set(row) - required - {"condition_key"}
            or not isinstance(row["response_values"], dict)
            or set(row["response_values"]) != response_ids
        ):
            raise BayesianOptimizationError("bayesian_desirability_response_mapping_invalid")
        for value in row["response_values"].values():
            finite_number(value)
    views: dict[str, Any] = {}
    for goal in goals:
        # This scalar projection exists only for the response-specific GP view.
        # It never replaces the immutable complete observed response vector.
        projected = [
            {
                **{key: value for key, value in row.items() if key != "response_values"},
                "objective_value": finite_number(row["response_values"][goal.response_id]),
            }
            for row in rows
        ]
        try:
            view = prepare_bo_observation_view(projected, factors, **policy)
        except BoObservationGroupsError as exc:
            raise BayesianOptimizationError(exc.code) from exc
        if views and _shared_provenance(view) != _shared_provenance(next(iter(views.values()))):
            raise BayesianOptimizationError("bayesian_observation_identity_invalid")
        views[goal.response_id] = view
    return views


def _shared_provenance(view: Any) -> dict[str, Any]:
    provenance = view.provenance()
    fields = (
        "mode",
        "raw_observation_count",
        "unique_condition_count",
        "unique_coordinate_count",
        "effective_training_count",
    )
    result = {key: provenance[key] for key in fields}
    result["groups"] = [
        {
            key: value
            for key, value in group.items()
            if key not in {"mean", "within_ss", "sample_variance"}
        }
        for group in provenance["groups"]
    ]
    return result
