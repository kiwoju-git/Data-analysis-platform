"""Bounded, no-refit validation of the internal ordered-batch calculation.

Conditional quadrature moments are worker output, not an independent posterior
proof. Validate their feasible moments and score reduction here; independent
numerical tests validate the quadrature and GP conditioning separately.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any

import numpy as np

from app.api.v1.schemas.bo_curve_calculation import (
    DesirabilityCurveCalculationRequest,
    DesirabilityCurveCalculationResult,
)
from app.api.v1.schemas.bo_desirability_batch_calculation import (
    DesirabilityBatchCalculationRequest,
    DesirabilityBatchCalculationResult,
    DesirabilityBatchCandidate,
)
from app.api.v1.schemas.bo_desirability_calculation import _ResponseModelResult
from app.api.v1.schemas.bo_fit_quality import (
    DesirabilityFitCalculationRequest,
    DesirabilityFitCalculationResult,
    _ResponseModel,
)
from app.api.v1.schemas.bo_planning import PlanningSelectionItem
from app.services.bo_desirability_contract import _validate_source_and_candidate
from app.statistics.bayesian_optimization import BayesianOptimizationError, _validated_factors
from app.statistics.bo_desirability import composite_desirability
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_batch_acquisition import (
    _condition,
    _raw_variance,
    _rescale_variance,
    batch_response_seed,
)
from app.statistics.bo_desirability_batch_core import batch_preflight, batch_search_seed
from app.statistics.bo_desirability_core import _observation_views


def _require(condition: bool) -> None:
    if not condition:
        raise BayesianOptimizationError("bayesian_desirability_result_invalid")


def _close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=2e-11, abs_tol=0)


def validate_batch_calculation_result(
    request: DesirabilityBatchCalculationRequest
    | DesirabilityFitCalculationRequest
    | DesirabilityCurveCalculationRequest,
    result: DesirabilityBatchCalculationResult
    | DesirabilityFitCalculationResult
    | DesirabilityCurveCalculationResult,
) -> None:
    _require(request.schema_version == result.schema_version)
    _require(result.batch_size == request.batch_size == len(result.items))
    _require(result.batch_options == request.batch_options)
    q1 = request.q1_request()
    goals = [r.calculation_goal() for r in request.objective.responses]
    keys = [g.response_id for g in goals]
    factor_ids = [f.factor_id for f in request.factors]
    budget = result.search_budget
    _require(len(budget.searches) == request.batch_size)
    _require(budget.termination_reason == "complete_ordered_batch")
    _require(budget.max_moment_evaluations == request.batch_options.max_moment_evaluations)
    preflight = batch_preflight(request)
    _require(all(getattr(budget, key) == value for key, value in preflight.items()))
    # Match numerical caching, not exact observation grouping. Different actual
    # identities can map to the same representable normalized float input.
    views = _observation_views(
        q1.worker_payload(), goals, _validated_factors([f.model_dump() for f in request.factors])
    )
    coordinates = [tuple(point) for point in views[keys[0]].raw_x.tolist()]
    unique = len(set(coordinates))
    _require(budget.incumbent_moment_evaluations == unique)
    consumed, candidates, integrands = unique, 0, 0
    selected: list[list[float]] = []
    for step, (item, search) in enumerate(zip(result.items, budget.searches, strict=True)):
        _validate_source_and_candidate(
            q1,
            result,
            item,
            q1_search=False,
            fit_policy=request.fit_policy
            if isinstance(
                request, DesirabilityFitCalculationRequest | DesirabilityCurveCalculationRequest
            )
            else None,
        )
        _require(item.rank == step + 1)
        point = [item.normalized_coordinates[k] for k in factor_ids]
        nearest = min((math.dist(point, old) for old in selected), default=None)
        if nearest is None:
            _require(item.nearest_selected_distance is None)
        else:
            _require(item.nearest_selected_distance is not None)
            assert item.nearest_selected_distance is not None
            _require(_close(item.nearest_selected_distance, nearest))
            _require(nearest > request.search.duplicate_tolerance)
            _require(nearest >= request.batch_options.min_batch_distance_normalized)
        _require(search.nearest_selected_distance == item.nearest_selected_distance)
        _require(search.nearest_existing_distance == item.nearest_existing_distance)
        planning, sampler = item.planning, item.planning.sampler
        _require(planning.search_seed == batch_search_seed(request.search.random_seed, step))
        _require(sampler.root_seed == request.search.random_seed and sampler.batch_step == step)
        _require(sampler.requested_sample_count == request.batch_options.sample_count)
        _require(sampler.effective_sample_count == (sampler.requested_sample_count if step else 0))
        _require(sampler.conditioned_on_selected_ranks == list(range(1, step + 1)))
        _require(
            sampler.baseline_threshold
            == result.incumbent.latent_incumbent_value + request.xi_desirability
        )
        _require(
            sampler.response_sample_seeds
            == {
                key: str(batch_response_seed(request.search.random_seed, step, key)) for key in keys
            }
        )
        _require(sampler.max_moment_evaluations == budget.max_moment_evaluations - consumed)
        _require(sampler.candidate_evaluations == search.evaluations + 1)
        _require(sampler.exact_selected_evaluations <= sampler.candidate_evaluations)
        _require(
            sampler.moment_evaluations
            == sampler.candidate_evaluations
            + (sampler.candidate_evaluations - sampler.exact_selected_evaluations)
            * sampler.effective_sample_count
        )
        _require(sampler.response_moment_evaluations == sampler.moment_evaluations * len(keys))
        consumed += sampler.moment_evaluations
        candidates += sampler.candidate_evaluations
        integrands += sampler.integration_evaluations
        _require(consumed <= budget.max_moment_evaluations)
        _require(set(planning.conditional_variance_raw) == set(keys))
        _require(all(v >= 0 for v in planning.conditional_variance_raw.values()))
        if step:
            _validate_planning_proof(result.items, result.shared_model.response_models, step, goals)
        else:
            _require(sampler.exact_selected_evaluations == 0)
            _require(not sampler.selected_covariance)
            _require(
                planning.proof.model_dump()
                == {
                    "response_proofs": {},
                    "thresholds": [],
                    "sample_moments": [],
                }
            )
            _require(planning.score == item.acquisition.value and planning.mc_standard_error == 0)
            for p in item.response_predictions:
                _require(
                    planning.conditional_variance_raw[p.response_id]
                    == _raw_variance(p.latent_standard_deviation_raw)
                )
        selected.append(point)
    _require(budget.evaluations_consumed == candidates)
    _require(budget.moment_evaluations == consumed)
    _require(budget.posterior_evaluations == unique + candidates)
    _require(budget.response_moment_evaluations == consumed * len(keys))
    # Repeated coordinates share the incumbent calculation, not repeated costs.
    seen: set[tuple[float, ...]] = set()
    for coordinate, stored in zip(
        coordinates, result.incumbent.training_posterior_desirabilities, strict=True
    ):
        if coordinate not in seen:
            integrands += stored.moments.integration_evaluations
            seen.add(coordinate)
    _require(budget.integrand_evaluations == integrands)


def _validate_planning_proof(
    items: Sequence[DesirabilityBatchCandidate | PlanningSelectionItem],
    response_models: Sequence[_ResponseModelResult | _ResponseModel],
    step: int,
    goals: Any,
) -> None:
    item = items[step]
    planning, proof, sampler = item.planning, item.planning.proof, item.planning.sampler
    keys = [g.response_id for g in goals]
    _require(set(proof.response_proofs) == set(sampler.selected_covariance) == set(keys))
    count = sampler.effective_sample_count
    _require(len(proof.thresholds) == len(proof.sample_moments) == count)
    selected_samples: dict[str, Any] = {}
    _require(len(response_models) == len(item.response_predictions))
    for model_index, prediction in enumerate(item.response_predictions):
        model_record = response_models[model_index]
        key, model = model_record.response_id, model_record.model
        saved = proof.response_proofs[key]
        mean = np.asarray(saved.selected_mean_scaled)
        cov = np.asarray(saved.selected_covariance_scaled)
        cross = np.asarray(saved.cross_covariance_scaled)
        _require(mean.shape == cross.shape == (step,) and cov.shape == (step, step))
        center, scale = model.normalization.mean, model.normalization.scale
        centered, state = _condition(
            cov, model.signal_kernel.amplitude, step, int(sampler.response_sample_seeds[key]), count
        )
        summary = sampler.selected_covariance[key]
        _require(summary.rank == state.rank)
        _require(summary.roundoff_scale == state.covariance_scale)
        _require(
            summary.negative_eigenvalue_adjustment_scaled
            == state.negative_eigenvalue_adjustment_scaled
        )
        _require(
            summary.negative_eigenvalue_adjustment_raw
            == _rescale_variance(state.negative_eigenvalue_adjustment_scaled, scale)
        )
        # Predictions at a prefix may be evaluated in different BLAS batches.
        # Allow only scale-aware floating-point roundoff, never statistical noise.
        tolerance = 128 * np.finfo(float).eps * state.covariance_scale * step
        for index, old in enumerate(items[:step]):
            previous = next(p for p in old.response_predictions if p.response_id == key)
            _require(
                math.isclose(
                    mean[index] * scale + center,
                    previous.mean_raw,
                    rel_tol=2e-11,
                    abs_tol=128 * np.finfo(float).eps * max(abs(center), scale),
                )
            )
            previous_var = (previous.latent_standard_deviation_raw / scale) ** 2
            _require(
                math.isclose(cov[index, index], previous_var, rel_tol=2e-11, abs_tol=tolerance)
            )
            for earlier in range(index):
                old_cross = old.planning.proof.response_proofs[key].cross_covariance_scaled[earlier]
                _require(
                    math.isclose(cov[index, earlier], old_cross, rel_tol=2e-11, abs_tol=tolerance)
                )
        _require(
            math.isclose(
                saved.candidate_mean_scaled * scale + center,
                prediction.mean_raw,
                rel_tol=2e-11,
                abs_tol=128 * np.finfo(float).eps * max(abs(center), scale),
            )
        )
        _require(
            math.isclose(
                saved.candidate_variance_scaled,
                (prediction.latent_standard_deviation_raw / scale) ** 2,
                rel_tol=2e-11,
                abs_tol=tolerance,
            )
        )
        _require(bool(np.all(np.abs(cross - cross @ state.projector) <= tolerance)))
        whitened = cross @ state.whitener
        reduction = float(whitened @ whitened)
        variance = saved.candidate_variance_scaled - reduction
        tolerance_v = (
            64
            * np.finfo(float).eps
            * max(saved.candidate_variance_scaled, reduction, state.covariance_scale)
            * step
        )
        _require(bool(math.isfinite(variance) and variance >= -tolerance_v))
        adjustment = max(0.0, -variance)
        _require(
            bool(adjustment <= summary.conditional_variance_adjustment_max_scaled <= tolerance_v)
        )
        expected_raw = _rescale_variance(max(0.0, variance), scale)
        _require(_close(planning.conditional_variance_raw[key], expected_raw))
        selected_samples[key] = (mean + centered) * scale + center
        _require(bool(np.all(np.isfinite(selected_samples[key]))))
    thresholds = [
        max(
            sampler.baseline_threshold,
            max(
                composite_desirability({k: selected_samples[k][m, j] for k in keys}, goals)
                for j in range(step)
            ),
        )
        for m in range(count)
    ]
    _require(proof.thresholds == thresholds)
    scores = [
        beta_expected_improvement(
            m.mean, m.variance, min(threshold, 1.0), xi=max(threshold - 1.0, 0.0)
        ).value
        for m, threshold in zip(proof.sample_moments, thresholds, strict=True)
    ]
    _require(planning.score == float(np.mean(scores)))
    _require(planning.mc_standard_error == float(np.std(scores, ddof=1) / math.sqrt(count)))
