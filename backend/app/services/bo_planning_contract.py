"""No-refit checks before persisting manual selection and displaying model views."""

from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

import numpy as np

from app.api.v1.schemas import bo_planning as dto
from app.api.v1.schemas.bo_desirability_calculation import _ResponseModelResult
from app.api.v1.schemas.bo_fit_quality import _ResponseModel
from app.services.bo_desirability_batch_contract import _validate_planning_proof
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_beta_policy import stored_beta_expected_improvement
from app.statistics.bo_candidate_points import GENERATION_POLICY, validated_candidate_rows
from app.statistics.bo_desirability_batch_acquisition import _raw_variance, batch_response_seed
from app.statistics.bo_desirability_posterior import evaluate_surrogate_desirability
from app.statistics.bo_planning_model import (
    PlanningEvaluationBudget,
    PlanningModel,
    _deadline,
    _eligibility_coordinates,
    _same_incumbent,
    restore_planning_model,
)


def _require(condition: bool) -> None:
    if not condition:
        raise BayesianOptimizationError("bayesian_planning_result_invalid")


def validate_candidate_generation(payload: dict[str, Any], result: Any) -> list[dto.CandidateRow]:
    _require(isinstance(result, dict) and set(result) == {"rows", "generation"})
    rows = [dto.CandidateRow.model_validate(row) for row in result["rows"]]
    source = payload["source"]
    if source["kind"] == "explicit_rows":
        _require(result["generation"] is None)
        points = source["points"]
    else:
        generation = result["generation"]
        _require(
            isinstance(generation, dict)
            and set(generation)
            == {
                "policy",
                "seed",
                "requested_count",
                "attempt_count",
                "max_attempts",
            }
        )
        _require(generation["policy"] == GENERATION_POLICY and generation["seed"] == source["seed"])
        _require(generation["requested_count"] == source["count"] == len(rows))
        _require(
            type(generation["attempt_count"]) is int
            and (len(rows) <= generation["attempt_count"] <= generation["max_attempts"] == 200000)
        )
        points = [row.input_coordinates for row in rows]
    expected = validated_candidate_rows(
        points,
        payload["factors"],
        payload["constraints"],
        excluded_normalized=payload["excluded"],
        duplicate_tolerance=payload["tolerance"],
        include_constraint_violations=payload["include_violations"],
    )
    _require([row.model_dump(mode="json") for row in rows] == expected)
    return rows


def _base(
    model: PlanningModel,
    rows: list[Any],
    points: list[dict[str, float]],
    excluded: list[list[float]],
    budget: PlanningEvaluationBudget,
) -> None:
    request = model.request
    expected_rows = validated_candidate_rows(
        points,
        [factor.model_dump() for factor in request.factors],
        [constraint.model_dump() for constraint in request.constraints],
        excluded_normalized=_eligibility_coordinates(model, excluded),
        duplicate_tolerance=request.search.duplicate_tolerance,
        include_constraint_violations=True,
    )
    _require(len(expected_rows) == len(rows))
    for expected, row in zip(expected_rows, rows, strict=True):
        budget.consume(1)
        data = row.model_dump(mode="json")
        _require(all(data[key] == value for key, value in expected.items()))
        point = [row.normalized_coordinates[factor.factor_id] for factor in request.factors]
        base = evaluate_surrogate_desirability(model.models, model.goals, point)
        _require(_same_incumbent(data["response_predictions"], [asdict(v) for v in base.responses]))
        _require(_same_incumbent(data["desirability_moments"], asdict(base.moments)))
        acquisition = stored_beta_expected_improvement(
            base.moments.mean,
            base.moments.variance,
            model.incumbent["latent_incumbent_value"],
            xi=request.xi_desirability,
            numerical_policy=row.acquisition.numerical_policy,
        )
        _require(
            _same_incumbent(
                data["acquisition"],
                {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(acquisition),
                    "xi_desirability": request.xi_desirability,
                },
            )
        )


def validate_planning_evaluation(
    snapshot: dict[str, Any],
    points: list[dict[str, float]],
    excluded: list[list[float]],
    rows: Any,
    *,
    deadline: float | None = None,
) -> list[dto.EvaluatedCandidateRow]:
    typed = [dto.EvaluatedCandidateRow.model_validate(row) for row in rows]
    budget = PlanningEvaluationBudget(_deadline(60000) if deadline is None else deadline, 4096)
    model = restore_planning_model(snapshot, budget=budget)
    _base(model, typed, points, excluded, budget)
    budget.consume(0)
    return typed


def validate_planning_selection(
    snapshot: dict[str, Any],
    points: list[dict[str, float]],
    excluded: list[list[float]],
    result: Any,
    *,
    deadline: float | None = None,
) -> dto.PlanningSelectionCalculation:
    typed = dto.PlanningSelectionCalculation.model_validate(result)
    budget = PlanningEvaluationBudget(_deadline(60000) if deadline is None else deadline, 4096)
    model = restore_planning_model(snapshot, budget=budget)
    incumbent_evaluations = budget.used
    _base(model, typed.items, points, excluded, budget)
    request = model.request
    model_records = [
        (
            _ResponseModel if item["model"]["schema_version"] == 5 else _ResponseModelResult
        ).model_validate(item)
        for item in snapshot["response_models"]
    ]
    factor_ids = [factor.factor_id for factor in request.factors]
    keys = [goal.response_id for goal in model.goals]
    selected: list[list[float]] = []
    consumed = incumbent_evaluations
    _require(typed.max_moment_evaluations == request.batch_options.max_moment_evaluations)
    for step, item in enumerate(typed.items):
        budget.consume(0)
        point = [item.normalized_coordinates[key] for key in factor_ids]
        nearest = min((math.dist(point, old) for old in selected), default=None)
        _require(item.nearest_selected_distance == nearest)
        _require(
            nearest is None
            or (
                nearest > request.search.duplicate_tolerance
                and nearest >= request.batch_options.min_batch_distance_normalized
            )
        )
        sampler = item.planning.sampler
        _require(
            sampler.numerical_policy
            == item.acquisition.numerical_policy
            == typed.items[0].acquisition.numerical_policy
        )
        _require(sampler.batch_step == step and sampler.root_seed == request.search.random_seed)
        _require(sampler.requested_sample_count == request.batch_options.sample_count)
        _require(
            sampler.effective_sample_count == (request.batch_options.sample_count if step else 0)
        )
        _require(sampler.conditioned_on_selected_ranks == list(range(1, step + 1)))
        _require(
            sampler.response_sample_seeds
            == {
                key: str(batch_response_seed(request.search.random_seed, step, key)) for key in keys
            }
        )
        _require(
            sampler.baseline_threshold
            == model.incumbent["latent_incumbent_value"] + request.xi_desirability
        )
        _require(sampler.max_moment_evaluations == typed.max_moment_evaluations - consumed)
        _require(sampler.candidate_evaluations == 1 and sampler.exact_selected_evaluations == 0)
        _require(sampler.moment_evaluations == 1 + sampler.effective_sample_count)
        _require(sampler.response_moment_evaluations == sampler.moment_evaluations * len(keys))
        consumed += sampler.moment_evaluations
        if step:
            for key in keys:
                surrogate = model.models[key]
                posterior = surrogate.predict(np.asarray(selected), joint=True)
                candidate = surrogate.predict(np.asarray([point]))
                cross = surrogate.latent_cross_covariance(np.asarray([point]), np.asarray(selected))
                proof = item.planning.proof.response_proofs[key]
                scale = surrogate.covariance_roundoff_scale
                absolute = 128 * np.finfo(float).eps * scale * step
                _require(
                    bool(
                        np.allclose(
                            proof.selected_mean_scaled,
                            posterior.mean_scaled,
                            rtol=2e-11,
                            atol=absolute,
                        )
                    )
                )
                _require(
                    bool(
                        np.allclose(
                            proof.selected_covariance_scaled,
                            posterior.latent_covariance_scaled,
                            rtol=2e-11,
                            atol=absolute,
                        )
                    )
                )
                _require(
                    bool(
                        np.allclose(
                            proof.cross_covariance_scaled,
                            cross[0],
                            rtol=2e-11,
                            atol=absolute,
                        )
                    )
                )
                _require(
                    math.isclose(
                        proof.candidate_mean_scaled,
                        float(candidate.mean_scaled[0]),
                        rel_tol=2e-11,
                        abs_tol=absolute,
                    )
                )
                _require(
                    math.isclose(
                        proof.candidate_variance_scaled,
                        float(candidate.latent_variance_scaled[0]),
                        rel_tol=2e-11,
                        abs_tol=absolute,
                    )
                )
            _validate_planning_proof(typed.items, model_records, step, model.goals)
        else:
            _require(
                item.planning.score == item.acquisition.value
                and item.planning.mc_standard_error == 0
            )
            _require(not sampler.selected_covariance)
            _require(
                item.planning.proof.model_dump()
                == {
                    "response_proofs": {},
                    "thresholds": [],
                    "sample_moments": [],
                }
            )
            _require(
                item.planning.conditional_variance_raw
                == {
                    p.response_id: _raw_variance(p.latent_standard_deviation_raw)
                    for p in item.response_predictions
                }
            )
        selected.append(point)
    _require(typed.moment_evaluations == consumed <= typed.max_moment_evaluations)
    budget.consume(0)
    return typed
