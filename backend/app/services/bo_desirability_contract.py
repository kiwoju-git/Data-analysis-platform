"""No-refit validation of desirability calculation and saved results."""

import math
from typing import Any

from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityCalculationRequest as DesirabilityCalculationRequest,
)
from app.api.v1.schemas.bo_desirability_calculation import (
    DesirabilityCalculationResult as DesirabilityCalculationResult,
)
from app.api.v1.schemas.bo_desirability_calculation import _CalculationRequestFields
from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    _validated_constraints,
    _validated_factors,
)
from app.statistics.bo_desirability import normalized_importance


def validate_calculation_result(
    request: DesirabilityCalculationRequest, result: DesirabilityCalculationResult
) -> None:
    _validate_source_and_candidate(request, result, result.items[0], q1_search=True)


def _validate_source_and_candidate(
    request: _CalculationRequestFields,
    result: Any,
    candidate: Any,
    *,
    q1_search: bool,
    fit_policy: Any = None,
) -> None:
    """Check identities, observed statistics and selected payoff without any refit.

    This is a calculation-boundary check, not a persistent artifact reader or a
    substitute for independent posterior/reference tests.
    """
    from app.statistics.bayesian_optimization import _constraint_evaluations
    from app.statistics.bo_desirability import (
        composite_desirability,
        independent_desirability_moments,
    )
    from app.statistics.bo_desirability_acquisition import beta_expected_improvement
    from app.statistics.bo_observation_groups import prepare_bo_observation_view

    def require(condition: bool) -> None:
        if not condition:
            raise BayesianOptimizationError("bayesian_desirability_result_invalid")

    def close(actual: float, expected: float) -> bool:
        return math.isclose(actual, expected, rel_tol=2e-11, abs_tol=0)

    goals = [r.calculation_goal() for r in request.objective.responses]
    factor_ids = [f.factor_id for f in request.factors]
    response_ids = [g.response_id for g in goals]
    trial_ids = [o.trial_id for o in request.observations]
    models = result.shared_model.response_models
    require(result.objective == request.objective)
    require(result.shared_model.factor_ids == factor_ids)
    require(result.shared_model.response_ids == response_ids)
    require([r.response_id for r in models] == response_ids)
    require([r.response_id for r in candidate.response_predictions] == response_ids)
    require([w.response_id for w in result.shared_model.normalized_importance] == response_ids)
    require(
        [w.weight for w in result.shared_model.normalized_importance]
        == list(normalized_importance(goals))
    )
    require(result.observation_view.mode == request.observation_policy.mode)
    require(result.observation_view.raw_observation_count == len(trial_ids))
    factors = _validated_factors([f.model_dump() for f in request.factors])
    model_requests = {r.response_id: r for r in request.response_models}
    fit_evaluations = 0
    canonical_observed: list[list[float]] = []
    shared_identity = result.observation_view.model_dump(mode="json")
    for response_model, prediction in zip(models, candidate.response_predictions, strict=True):
        model, response_id = response_model.model, response_model.response_id
        require(model.schema_version == (5 if fit_policy is not None else 4))
        expected_model = model_requests[response_id]
        projected = [
            {
                **o.model_dump(mode="json", exclude={"response_values"}),
                "objective_value": o.response_values[response_id],
            }
            for o in request.observations
        ]
        view = prepare_bo_observation_view(
            projected, factors, **request.observation_policy.model_dump()
        )
        if not canonical_observed:
            canonical_observed = view.raw_x.tolist()
        provenance = view.provenance()
        require(response_model.observation_view.model_dump(mode="json") == provenance)
        require(all(shared_identity[k] == provenance[k] for k in shared_identity if k != "groups"))
        require(
            shared_identity["groups"]
            == [
                {k: v for k, v in g.items() if k not in {"mean", "within_ss", "sample_variance"}}
                for g in provenance["groups"]
            ]
        )
        require(model.factor_ids == factor_ids)
        require(model.raw_observation_count == len(trial_ids))
        require(model.effective_training_count == view.effective_training_count)
        require(model.training_group_counts == view.training_counts.tolist())
        require(model.normalization.mean == view.normalization_mean)
        require(model.normalization.scale == view.normalization_scale)
        require(model.normalization.direction_multiplier == 1)
        require(model.signal_kernel.family == expected_model.kernel.kind)
        require(len(model.signal_kernel.length_scales) == len(factors))
        require(model.signal_kernel.initial_length_scales == [1.0] * len(factors))
        require(model.signal_kernel.amplitude_bounds == (1e-3, 1e3))
        require(model.signal_kernel.length_scale_bounds == (1e-2, 1e2))
        require(1e-3 * (1 - 1e-12) <= model.signal_kernel.amplitude <= 1e3 * (1 + 1e-12))
        require(
            all(
                1e-2 * (1 - 1e-12) <= v <= 1e2 * (1 + 1e-12)
                for v in model.signal_kernel.length_scales
            )
        )
        require(model.jitter == request.search.jitter)
        require(model.noise.mode == expected_model.surrogate.noise_mode)
        require(model.noise.fixed_sd_raw == expected_model.surrogate.fixed_noise_sd)
        if model.noise.mode == "estimate":
            bounds = (
                expected_model.surrogate.lower_noise_variance_scaled,
                expected_model.surrogate.upper_noise_variance_scaled,
            )
            require(model.noise.bounds_scaled == bounds)
            require(
                model.noise.initial_variance_scaled
                == expected_model.surrogate.initial_noise_variance_scaled
            )
            require(
                bounds[0] * (1 - 1e-12)
                <= model.noise.fitted_variance_scaled
                <= bounds[1] * (1 + 1e-12)
            )
        else:
            expected_variance = (
                (expected_model.surrogate.fixed_noise_sd / model.normalization.scale) ** 2
                if expected_model.surrogate.fixed_noise_sd is not None
                else 0.0
            )
            require(model.noise.bounds_scaled is None)
            require(close(model.noise.fitted_variance_scaled, expected_variance))
            require(close(model.noise.initial_variance_scaled, expected_variance))
        require(
            close(
                model.observation_noise_sd_raw,
                math.sqrt(model.noise.fitted_variance_scaled) * model.normalization.scale,
            )
        )
        require(
            close(
                prediction.predictive_standard_deviation_raw,
                math.hypot(
                    prediction.latent_standard_deviation_raw, model.observation_noise_sd_raw
                ),
            )
        )
        require(model.optimizer.seed == request.search.random_seed)
        require(model.optimizer.restarts == request.search.hyperparameter_restart_count)
        require(model.optimizer.max_iterations == request.search.model_max_iterations)
        require(
            model.optimizer.max_evaluations
            == request.search.model_max_evaluations - fit_evaluations
        )
        screening_count = 0
        if fit_policy is not None:
            from app.services.bo_fit_quality_contract import validate_fit_evidence

            screening_count = validate_fit_evidence(
                model, fit_policy, request.search, expected_model
            )
        require(
            model.optimizer.evaluations
            == screening_count + sum(s.evaluations for s in model.optimizer.starts)
        )
        fit_evaluations += model.optimizer.evaluations
    budget = result.search_budget
    require(budget.response_fit_count == budget.final_factorizations == len(models))
    require(budget.model_max_evaluations_total == request.search.model_max_evaluations)
    require(
        budget.model_evaluations_consumed == fit_evaluations <= request.search.model_max_evaluations
    )
    require(budget.max_evaluations_total == request.search.max_evaluations_total)
    require(budget.evaluations_consumed <= budget.max_evaluations_total)
    require(budget.time_budget_ms == request.search.time_budget_ms)
    if q1_search:
        require(budget.evaluations_consumed == budget.searches[0].evaluations + 1)
        require(budget.termination_reason == budget.searches[0].termination_reason)
    incumbent = result.incumbent
    require([v.trial_id for v in incumbent.observed_trial_desirabilities] == trial_ids)
    require([v.trial_id for v in incumbent.training_posterior_desirabilities] == trial_ids)
    observed = [composite_desirability(o.response_values, goals) for o in request.observations]
    require([v.value for v in incumbent.observed_trial_desirabilities] == observed)
    best_index = max(range(len(observed)), key=observed.__getitem__)
    require(incumbent.best_observed_trial_id == trial_ids[best_index])
    require(incumbent.best_observed_desirability == observed[best_index])
    latent = [v.moments.mean for v in incumbent.training_posterior_desirabilities]
    latent_index = max(range(len(latent)), key=latent.__getitem__)
    require(incumbent.latent_incumbent_trial_id == trial_ids[latent_index])
    require(incumbent.latent_incumbent_value == latent[latent_index])
    require(set(incumbent.latent_incumbent_normalized_coordinates) == set(factor_ids))
    for factor in request.factors:
        actual = request.observations[latent_index].actual_coordinates[factor.factor_id]
        require(
            math.isclose(
                incumbent.latent_incumbent_normalized_coordinates[factor.factor_id],
                (actual - factor.low) / (factor.high - factor.low),
                rel_tol=0,
                abs_tol=2e-12,
            )
        )
    require(
        set(candidate.actual_coordinates)
        == set(candidate.normalized_coordinates)
        == set(factor_ids)
    )
    for factor in request.factors:
        actual = candidate.actual_coordinates[factor.factor_id]
        normalized = candidate.normalized_coordinates[factor.factor_id]
        require(factor.low <= actual <= factor.high and 0 <= normalized <= 1)
        require(
            math.isclose(
                normalized,
                (actual - factor.low) / (factor.high - factor.low),
                rel_tol=0,
                abs_tol=2e-12,
            )
        )
        if factor.domain_kind == "discrete_numeric":
            require(factor.step is not None)
            assert factor.step is not None
            level = (actual - factor.low) / factor.step
            require(math.isclose(level, round(level), rel_tol=0, abs_tol=1e-8))
    point = [candidate.normalized_coordinates[k] for k in factor_ids]
    nearest = min(
        math.dist(point, old) for old in [*request.excluded_normalized, *canonical_observed]
    )
    require(nearest > request.search.duplicate_tolerance)
    require(close(candidate.nearest_existing_distance, nearest))
    constraints = _validated_constraints([c.model_dump() for c in request.constraints], factors)
    evaluated = _constraint_evaluations(candidate.actual_coordinates, constraints)
    require([c.model_dump(mode="json") for c in candidate.constraint_evaluations] == evaluated)
    require(all(c["satisfied"] for c in evaluated))
    expected_moments = independent_desirability_moments(
        {
            p.response_id: (p.mean_raw, p.latent_standard_deviation_raw)
            for p in candidate.response_predictions
        },
        goals,
    )
    require(close(candidate.desirability_moments.mean, expected_moments.mean))
    require(close(candidate.desirability_moments.second_moment, expected_moments.second_moment))
    require(close(candidate.desirability_moments.variance, expected_moments.variance))
    require(candidate.acquisition.xi_desirability == request.xi_desirability)
    expected_ei = beta_expected_improvement(
        expected_moments.mean,
        expected_moments.variance,
        incumbent.latent_incumbent_value,
        xi=request.xi_desirability,
    )
    require(candidate.acquisition.value == expected_ei.value)
    require(candidate.acquisition.threshold == expected_ei.threshold)
    require(candidate.acquisition.distribution == expected_ei.distribution)
    require(
        candidate.acquisition.alpha == expected_ei.alpha
        and candidate.acquisition.beta == expected_ei.beta
    )
