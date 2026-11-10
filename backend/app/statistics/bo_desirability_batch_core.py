"""Internal, all-or-nothing greedy batch search over fixed response GP posteriors."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict
from typing import Any

from pydantic import ValidationError

from app.api.v1.schemas.bo_curve_calculation import DesirabilityCurveCalculationRequest
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    DesirabilityBatchCalculationRequest,
)
from app.api.v1.schemas.bo_fit_quality import DesirabilityFitCalculationRequest
from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    _constraint_evaluations,
    _discrete_normalized_levels,
    _SearchBudget,
    _validated_constraints,
    _validated_excluded_points,
    _validated_factors,
)
from app.statistics.bo_desirability import CURVE_POLICY, MOMENT_POLICY, normalized_importance
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_batch_acquisition import (
    POLICY_VERSION,
    DesirabilityBatchAcquisition,
)
from app.statistics.bo_desirability_core import (
    MODEL_SCHEMA_VERSION,
    _fit_response_models,
    _incumbent_result,
    _observation_views,
    _shared_provenance,
    _validated_configuration,
)
from app.statistics.bo_desirability_posterior import evaluate_surrogate_desirability
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_mixed_search import ENUMERATION_LIMIT, search_mixed_acquisition
from app.statistics.bo_target_curve import MIXED_CURVE_POLICY, MIXED_MOMENT_POLICY


def batch_search_seed(root: int, step: int) -> int:
    if step == 0:
        return root
    material = f"{POLICY_VERSION}\0{root}\0mixed_search\0{step}"
    return int.from_bytes(hashlib.sha256(material.encode("ascii")).digest()[:4], "big")


def batch_preflight(
    request: DesirabilityBatchCalculationRequest
    | DesirabilityFitCalculationRequest
    | DesirabilityCurveCalculationRequest,
) -> dict[str, int]:
    """Reserve an upper bound for pool work, not a promise that local search fits.

    Small discrete spaces are enumerated in addition to the continuous pool;
    large spaces can add two neighbors per factor for 16 distinct assignments.
    Runtime accounting still charges every evaluation across every batch step.
    """
    factors = _validated_factors([f.model_dump() for f in request.factors])
    levels = [_discrete_normalized_levels(f) for f in factors]
    discrete = [v for v in levels if v is not None]
    assignments = math.prod(len(v) for v in discrete)
    pool = request.search.candidate_count_per_step
    if discrete and assignments <= ENUMERATION_LIMIT:
        upper = assignments + (pool if len(discrete) < len(factors) else 0)
    else:
        upper = pool + 32 * len(discrete)
    unique = len(
        {
            tuple(o.actual_coordinates[f.factor_id] for f in request.factors)
            for o in request.observations
        }
    )
    moments = unique + (upper + 2) * (
        1 + (request.batch_size - 1) * (1 + request.batch_options.sample_count)
    )
    if moments > request.batch_options.max_moment_evaluations:
        raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
    if (upper + 2) * request.batch_size > request.search.max_evaluations_total:
        raise BayesianOptimizationError("bayesian_optimization_budget_exhausted")
    return {"initial_pool_upper_bound_per_step": upper, "preflight_moment_allowance": moments}


def calculate_desirability_batch(payload: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    started = time.perf_counter()
    try:
        request = (
            DesirabilityCurveCalculationRequest.model_validate(payload)
            if payload.get("schema_version") == 7
            else DesirabilityFitCalculationRequest.model_validate(payload)
            if payload.get("schema_version") == 6
            else DesirabilityBatchCalculationRequest.model_validate(payload)
        )
    except ValidationError:
        raise BayesianOptimizationError("bayesian_desirability_batch_input_invalid") from None
    preflight = batch_preflight(request)
    raw = request.q1_request().worker_payload()
    goals, specifications, options, xi = _validated_configuration(
        raw, versioned_curves=request.schema_version == 7
    )
    factors = _validated_factors(raw["factors"])
    constraints = _validated_constraints(raw["constraints"], factors)
    excluded = _validated_excluded_points(raw["excluded_normalized"], factors)
    views = _observation_views(raw, goals, factors)
    first_view = views[goals[0].response_id]
    factor_ids = list(first_view.factor_ids)
    for point in first_view.raw_x.tolist():
        if point not in excluded:
            excluded.append(point)
    budget = _SearchBudget(
        started, started + options["time_budget_ms"] / 1000, options["max_evaluations_total"]
    )
    moment_count = integrands = 0
    maximum = request.batch_options.max_moment_evaluations

    def consume(count: int) -> None:
        nonlocal budget
        budget = budget.consume(count)

    def consume_moments(count: int) -> None:
        nonlocal moment_count
        consume(0)
        if count > maximum - moment_count:
            raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
        moment_count += count

    with threadpool_limits(limits=1):
        models, records, warnings, fit_evaluations = _fit_response_models(
            goals,
            specifications,
            options,
            views,
            budget,
            **(
                {"fit_policy": BoFitPolicy(request.fit_policy.deterministic_start_count)}
                if isinstance(
                    request,
                    DesirabilityFitCalculationRequest | DesirabilityCurveCalculationRequest,
                )
                and request.fit_policy is not None
                else {}
            ),
        )
        cache: dict[tuple[float, ...], Any] = {}

        def posterior(point: Any) -> Any:
            nonlocal integrands
            key = tuple(float(v) for v in point)
            if key not in cache:
                consume_moments(1)
                cache[key] = evaluate_surrogate_desirability(models, goals, point)
                integrands += cache[key].moments.integration_evaluations
                consume(0)
            return cache[key]

        incumbent = _incumbent_result(goals, views, posterior)
        incumbent_moments = moment_count
        items, searches = [], []
        selected_x: list[list[float]] = []
        for step in range(request.batch_size):
            if moment_count >= maximum:
                raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
            planner = DesirabilityBatchAcquisition(
                models,
                goals,
                incumbent["latent_incumbent_value"],
                np.asarray(selected_x).reshape((-1, len(factors))),
                xi=xi,
                root_seed=options["random_seed"],
                sample_count=request.batch_options.sample_count,
                max_moment_evaluations=maximum - moment_count,
                check_budget=lambda: consume(0),
                consume_moments=consume_moments,
            )
            seed = batch_search_seed(options["random_seed"], step)

            def score(points: Any, scorer: DesirabilityBatchAcquisition = planner) -> Any:
                return scorer.score(points).scores

            found = search_mixed_acquisition(
                factors=factors,
                constraints=constraints,
                score=score,
                seed=seed,
                pool_size=options["candidate_count_per_step"],
                local_start_count=options["local_start_count_per_step"],
                local_maxiter=options["max_iterations_per_step"],
                excluded_normalized=excluded,
                selected_normalized=selected_x,
                duplicate_tolerance=options["duplicate_tolerance"],
                min_batch_distance_normalized=request.batch_options.min_batch_distance_normalized,
                consume=consume,
            )
            consume(1)
            scored = planner.score([found.normalized_coordinates], include_details=True)
            if float(scored.scores[0]) != found.acquisition:
                raise BayesianOptimizationError("bayesian_desirability_numeric_invalid")
            base = scored.base_posteriors[0]
            acquisition = beta_expected_improvement(
                base.moments.mean,
                base.moments.variance,
                incumbent["latent_incumbent_value"],
                xi=xi,
            )
            items.append(
                {
                    "rank": step + 1,
                    "actual_coordinates": found.actual_coordinates,
                    "normalized_coordinates": dict(
                        zip(factor_ids, found.normalized_coordinates, strict=True)
                    ),
                    "response_predictions": [asdict(p) for p in base.responses],
                    "desirability_moments": asdict(base.moments),
                    "acquisition": {
                        "kind": "desirability_beta_expected_improvement",
                        **asdict(acquisition),
                        "xi_desirability": xi,
                    },
                    "nearest_existing_distance": found.metadata["nearest_existing_distance"],
                    "nearest_selected_distance": found.metadata["nearest_selected_distance"],
                    "constraint_evaluations": _constraint_evaluations(
                        found.actual_coordinates, constraints
                    ),
                    "planning": {
                        "score": float(scored.scores[0]),
                        "mc_standard_error": float(scored.mc_standard_error[0]),
                        "conditional_variance_raw": {
                            k: float(v[0]) for k, v in scored.conditional_variance_raw.items()
                        },
                        "search_seed": seed,
                        "sampler": planner.metadata(),
                        "proof": scored.details
                        or {"response_proofs": {}, "thresholds": [], "sample_moments": []},
                    },
                }
            )
            if found.acquisition == 0:
                warnings.append("bayesian_acquisition_numerically_zero")
            integrands += planner.integration_evaluations
            searches.append(found.metadata)
            selected_x.append(found.normalized_coordinates)
        consume(0)
    limitations = [
        "bayesian_desirability_independent_response_posteriors",
        "bayesian_desirability_beta_approximation_not_exact_ei",
        "bayesian_desirability_curve_not_jmp_equivalent",
        "bayesian_plugin_incumbent_not_exact_noisy_ei",
        "bayesian_homoscedastic_independent_measurement_noise",
        "bayesian_optimization_no_global_optimum_guarantee",
        "bayesian_desirability_mc_error_excludes_approximation_error",
        "bayesian_desirability_batch_not_jmp_augmentation",
    ]
    result = {
        "schema_version": request.schema_version,
        "batch_size": request.batch_size,
        "policy": POLICY_VERSION,
        "batch_options": request.batch_options.model_dump(mode="json"),
        "objective": request.objective.model_dump(mode="json"),
        "shared_model": {
            "schema_version": request.schema_version
            if request.schema_version in {6, 7}
            else MODEL_SCHEMA_VERSION,
            "policy_version": 1,
            "factor_ids": factor_ids,
            "response_ids": [g.response_id for g in goals],
            "response_models": records,
            "normalized_importance": [
                {"response_id": g.response_id, "weight": w}
                for g, w in zip(goals, normalized_importance(goals), strict=True)
            ],
            "curve_policy": MIXED_CURVE_POLICY if request.schema_version == 7 else CURVE_POLICY,
            "moment_policy": MIXED_MOMENT_POLICY if request.schema_version == 7 else MOMENT_POLICY,
            "independence_assumption": True,
        },
        "incumbent": incumbent,
        "observation_view": _shared_provenance(first_view),
        "items": items,
        "search_budget": {
            "max_evaluations_total": options["max_evaluations_total"],
            "evaluations_consumed": budget.evaluations,
            "evaluation_unit": "candidate_with_all_response_desirability_moments",
            "posterior_evaluations": incumbent_moments + budget.evaluations,
            "integrand_evaluations": integrands,
            "response_fit_count": len(models),
            "model_max_evaluations_total": options["model_max_evaluations"],
            "model_evaluations_consumed": fit_evaluations,
            "final_factorizations": len(models),
            "time_budget_ms": options["time_budget_ms"],
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "searches": searches,
            "termination_reason": "complete_ordered_batch",
            "max_moment_evaluations": maximum,
            "moment_evaluations": moment_count,
            "incumbent_moment_evaluations": incumbent_moments,
            "response_moment_evaluations": moment_count * len(models),
            **preflight,
        },
        "warnings": list(
            dict.fromkeys([*warnings, "bayesian_optimization_confirmation_required", *limitations])
        ),
        "limitations": limitations,
    }
    json.dumps(result, allow_nan=False)
    return result
