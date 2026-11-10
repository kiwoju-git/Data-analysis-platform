"""Bounded worker output checks for typed mixed-condition views."""

import time
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any, cast

from pydantic import TypeAdapter

from app.api.v1.schemas.bayesian import BayesianLinearConstraintRequest
from app.api.v1.schemas.bo_mixed_planning import (
    EvaluatedMixedCandidateRow,
    MixedCandidateRow,
    MixedPlanningSelectionCalculation,
)
from app.api.v1.schemas.bo_mixed_studies import (
    MixedFactorRequest,
    mixed_constraint_definitions,
    mixed_factor_domains,
)
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_mixed_candidate_points import (
    generate_mixed_candidate_points,
    validated_mixed_candidate_rows,
)
from app.statistics.bo_mixed_planning import (
    evaluate_mixed_surrogate_desirability,
    restore_mixed_planning_model,
)
from app.statistics.bo_planning_model import PlanningEvaluationBudget, _same_incumbent


def _domains(payload: dict[str, Any]) -> tuple[Any, Any]:
    factors = TypeAdapter(list[MixedFactorRequest]).validate_python(payload["factors"])
    constraints = TypeAdapter(list[BayesianLinearConstraintRequest]).validate_python(
        payload["constraints"]
    )
    return mixed_factor_domains(factors), mixed_constraint_definitions(constraints)


def calculate_mixed_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    domains, constraints = _domains(payload)
    source = payload["source"]
    generated = None
    if source["kind"] == "seeded_uniform":
        generated = generate_mixed_candidate_points(
            domains, constraints, seed=source["seed"], count=source["count"]
        )
        points = generated["points"]
    elif source["kind"] == "explicit_rows":
        points = source["points"]
    else:
        raise BayesianOptimizationError("bayesian_candidate_input_invalid")
    rows = validated_mixed_candidate_rows(
        points,
        domains,
        constraints,
        excluded_encoded=payload["excluded"],
        duplicate_tolerance=payload["tolerance"],
        include_constraint_violations=payload["include_violations"],
        ordinal_rank_distance=payload["ordinal_rank_distance"],
    )
    return {
        "rows": rows,
        "generation": None if generated is None else generated["generation"],
    }


def validate_mixed_candidates(payload: dict[str, Any], result: Any, *, deadline: float) -> None:
    def check() -> None:
        if time.perf_counter() >= deadline:
            raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")

    try:
        if not isinstance(result, dict) or set(result) != {"rows", "generation"}:
            raise ValueError
        domains, constraints = _domains(payload)
        rows = [
            MixedCandidateRow.model_validate(row).model_dump(mode="json") for row in result["rows"]
        ]
        if payload["source"]["kind"] == "explicit_rows":
            if result["generation"] is not None:
                raise ValueError
            points = payload["source"]["points"]
        else:
            points = [row["input_coordinates"] for row in rows]
            if len(points) != payload["source"]["count"]:
                raise ValueError
            receipt = result["generation"]
            if (
                not isinstance(receipt, dict)
                or set(receipt)
                != {"policy", "seed", "requested_count", "attempt_count", "max_attempts"}
                or receipt["policy"] != "sha256_counter_mixed_uniform_candidates_v1"
                or receipt["seed"] != payload["source"]["seed"]
                or receipt["requested_count"] != len(points)
                or type(receipt["attempt_count"]) is not int
                or not len(points) <= receipt["attempt_count"] <= receipt["max_attempts"] == 200000
            ):
                raise ValueError
        expected = validated_mixed_candidate_rows(
            points,
            domains,
            constraints,
            excluded_encoded=payload["excluded"],
            duplicate_tolerance=payload["tolerance"],
            include_constraint_violations=payload["include_violations"],
            ordinal_rank_distance=payload["ordinal_rank_distance"],
            check_budget=check,
        )
        if rows != expected:
            raise ValueError
    except (ValueError, KeyError, TypeError, AttributeError):
        raise BayesianOptimizationError("bayesian_planning_result_invalid") from None


def _require(condition: bool) -> None:
    if not condition:
        raise BayesianOptimizationError("bayesian_planning_result_invalid")


def _base_rows(
    payload: dict[str, Any], model: Any, budget: PlanningEvaluationBudget
) -> list[dict[str, Any]]:
    excluded = list(model.excluded_encoded)
    for point in payload.get("eligibility_excluded_encoded", []):
        if point not in excluded:
            excluded.append(point)
    return validated_mixed_candidate_rows(
        payload["points"],
        mixed_factor_domains(model.request.factors),
        mixed_constraint_definitions(model.request.constraints),
        excluded_encoded=excluded,
        duplicate_tolerance=model.request.search.duplicate_tolerance,
        include_constraint_violations=True,
        ordinal_rank_distance=payload.get("ordinal_rank_distance", False),
        check_budget=lambda: budget.consume(0),
    )


def _validate_base(
    model: Any,
    rows: list[Any],
    originals: list[dict[str, Any]],
    budget: PlanningEvaluationBudget,
    *,
    compute_acquisition: bool,
) -> None:
    _require(len(rows) == len(originals))
    for row, original in zip(rows, originals, strict=True):
        budget.consume(1)
        data = row.model_dump(mode="json")
        _require(all(data[key] == value for key, value in original.items()))
        point = [row.encoded_coordinates[f.factor_id] for f in model.request.factors]
        base = evaluate_mixed_surrogate_desirability(model.models, model.goals, point)
        _require(
            _same_incumbent(data["response_predictions"], [asdict(item) for item in base.responses])
        )
        _require(_same_incumbent(data["desirability_moments"], asdict(base.moments)))
        if not compute_acquisition:
            _require(row.acquisition is None)
            continue
        expected = {
            "kind": "desirability_beta_expected_improvement",
            **asdict(
                beta_expected_improvement(
                    base.moments.mean,
                    base.moments.variance,
                    model.incumbent["latent_incumbent_value"],
                    xi=model.request.xi_desirability,
                )
            ),
            "xi_desirability": model.request.xi_desirability,
        }
        _require(_same_incumbent(data["acquisition"], expected))


def validate_mixed_evaluation(payload: dict[str, Any], result: Any, *, deadline: float) -> None:
    try:
        _require(type(result) is list and 1 <= len(result) <= 10000)
        budget = PlanningEvaluationBudget(deadline, payload.get("max_moment_evaluations", 4096))
        model = restore_mixed_planning_model(payload["snapshot"], budget=budget)
        originals = _base_rows(payload, model, budget)
        typed = [EvaluatedMixedCandidateRow.model_validate(row) for row in result]
        compute = payload.get("compute_acquisition", True)
        _require(type(compute) is bool)
        _validate_base(model, typed, originals, budget, compute_acquisition=compute)
        budget.consume(0)
    except BayesianOptimizationError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError):
        raise BayesianOptimizationError("bayesian_planning_result_invalid") from None


def validate_mixed_selection(
    operation: str, payload: dict[str, Any], result: Any, *, deadline: float
) -> None:
    """Recheck bounded selected posteriors and receipts inside the owning worker."""
    import numpy as np

    from app.api.v1.schemas.bo_mixed_workflow import MixedAugmentationCalculation
    from app.services.bo_augmentation_contract import validate_mixed_augmentation_binding
    from app.services.bo_desirability_batch_contract import _validate_planning_proof
    from app.statistics.bo_augmentation import CONFIRM
    from app.statistics.bo_desirability_batch_acquisition import _raw_variance, batch_response_seed
    from app.statistics.bo_mixed_candidate_points import mixed_point_distance

    try:
        budget = PlanningEvaluationBudget(deadline, payload["max_moment_evaluations"])
        model = None
        if payload.get("snapshot") is not None:
            model = restore_mixed_planning_model(payload["snapshot"], budget=budget)
        incumbent_evaluations = budget.used
        if operation == "mixed_augmentation":
            typed_aug = MixedAugmentationCalculation.model_validate(result)
            domains, constraints = _domains(payload)
            originals = validated_mixed_candidate_rows(
                payload["points"],
                domains,
                constraints,
                excluded_encoded=payload["existing_coordinates"],
                duplicate_tolerance=payload["duplicate_tolerance"],
                include_constraint_violations=True,
                ordinal_rank_distance=payload["ordinal_rank_distance"],
                check_budget=lambda: budget.consume(0),
            )
            by_id = {row["row_id"]: row for row in originals}
            if model is not None:
                _validate_base(
                    model,
                    list(typed_aug.selected_rows),
                    [by_id[row.row_id] for row in typed_aug.selected_rows],
                    budget,
                    compute_acquisition=payload["policy"] != CONFIRM,
                )
                _require(incumbent_evaluations + len(originals) <= budget.maximum)
            validate_mixed_augmentation_binding(
                result,
                request=payload,
                snapshot=payload.get("snapshot"),
                rows=originals,
                existing_coordinates=payload["existing_coordinates"],
                domains=domains,
            )
            budget.consume(0)
            return
        _require(operation == "mixed_selection" and model is not None)
        typed = MixedPlanningSelectionCalculation.model_validate(result)
        assert model is not None
        originals = _base_rows(payload, model, budget)
        _validate_base(model, list(typed.items), originals, budget, compute_acquisition=True)
        request = model.request
        domains = mixed_factor_domains(request.factors)
        keys = [goal.response_id for goal in model.goals]
        selected: list[list[float]] = []
        consumed = incumbent_evaluations
        _require(typed.max_moment_evaluations == payload["max_moment_evaluations"])
        _require(typed.ordinal_rank_distance == payload.get("ordinal_rank_distance", False))
        response_models: list[Any] = [
            SimpleNamespace(
                response_id=key,
                model=SimpleNamespace(
                    normalization=SimpleNamespace(
                        mean=model.models[key].normalization_mean,
                        scale=model.models[key].normalization_scale,
                    ),
                    signal_kernel=SimpleNamespace(
                        amplitude=model.models[key].covariance_roundoff_scale
                    ),
                ),
            )
            for key in keys
        ]
        for step, item in enumerate(typed.items):
            budget.consume(0)
            point = [item.encoded_coordinates[domain.factor_id] for domain in domains]
            nearest = min(
                (
                    mixed_point_distance(
                        point, old, domains, ordinal_rank_distance=typed.ordinal_rank_distance
                    )
                    for old in selected
                ),
                default=None,
            )
            _require(item.nearest_selected_distance == nearest)
            _require(
                nearest is None
                or nearest > request.search.duplicate_tolerance
                and nearest >= payload["min_batch_distance"]
            )
            sampler = item.planning.sampler
            _require(sampler.batch_step == step and sampler.root_seed == request.search.random_seed)
            _require(sampler.requested_sample_count == payload["sample_count"])
            _require(sampler.effective_sample_count == (payload["sample_count"] if step else 0))
            _require(sampler.conditioned_on_selected_ranks == list(range(1, step + 1)))
            _require(
                sampler.response_sample_seeds
                == {
                    key: str(batch_response_seed(request.search.random_seed, step, key))
                    for key in keys
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
                    cross = surrogate.latent_cross_covariance(
                        np.asarray([point]), np.asarray(selected)
                    )
                    proof = item.planning.proof.response_proofs[key]
                    absolute = (
                        128 * np.finfo(float).eps * surrogate.covariance_roundoff_scale * step
                    )
                    for supplied, expected in (
                        (proof.selected_mean_scaled, posterior.mean_scaled),
                        (proof.selected_covariance_scaled, posterior.latent_covariance_scaled),
                        (proof.cross_covariance_scaled, cross[0]),
                        (proof.candidate_mean_scaled, float(candidate.mean_scaled[0])),
                        (
                            proof.candidate_variance_scaled,
                            float(candidate.latent_variance_scaled[0]),
                        ),
                    ):
                        _require(np.asarray(supplied).shape == np.asarray(expected).shape)
                        _require(bool(np.allclose(supplied, expected, rtol=2e-11, atol=absolute)))
                _validate_planning_proof(cast(Any, typed.items), response_models, step, model.goals)
            else:
                _require(
                    item.planning.score == item.acquisition.value
                    and item.planning.mc_standard_error == 0
                )
                _require(not sampler.selected_covariance)
                _require(
                    item.planning.proof.model_dump()
                    == {"response_proofs": {}, "thresholds": [], "sample_moments": []}
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
    except BayesianOptimizationError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        raise BayesianOptimizationError("bayesian_planning_result_invalid") from None
