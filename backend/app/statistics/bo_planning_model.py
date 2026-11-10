"""Reusable BO fit and read-only evaluations for candidate tables and profilers."""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import ValidationError

from app.api.v1.schemas.bo_curve_calculation import DesirabilityCurveCalculationRequest
from app.api.v1.schemas.bo_desirability_batch_calculation import DesirabilityBatchCalculationRequest
from app.api.v1.schemas.bo_desirability_calculation import _Incumbent
from app.api.v1.schemas.bo_fit_quality import DesirabilityFitCalculationRequest
from app.statistics.bayesian_optimization import (
    BayesianOptimizationError,
    _SearchBudget,
)
from app.statistics.bo_candidate_points import candidate_factors, validated_candidate_rows
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_batch_acquisition import DesirabilityBatchAcquisition
from app.statistics.bo_desirability_core import (
    _fit_response_models,
    _incumbent_result,
    _observation_views,
    _shared_provenance,
    _validated_configuration,
)
from app.statistics.bo_desirability_posterior import evaluate_surrogate_desirability
from app.statistics.bo_fit_policy import FIT_POLICY, BoFitPolicy
from app.statistics.bo_surrogate_snapshot import dump_bo_surrogate, load_bo_surrogate

PlanningRequest = (
    DesirabilityBatchCalculationRequest
    | DesirabilityFitCalculationRequest
    | DesirabilityCurveCalculationRequest
)


@dataclass
class PlanningEvaluationBudget:
    deadline: float
    maximum: int
    used: int = 0

    def __post_init__(self) -> None:
        if type(self.maximum) is not int or not 1 <= self.maximum <= 65536:
            raise BayesianOptimizationError("bayesian_planning_input_invalid")

    def consume(self, count: int) -> None:
        _check_deadline(self.deadline)
        if count > self.maximum - self.used:
            raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
        self.used += count


def _incumbent_from_models(
    goals: Any, views: Any, models: Any, budget: PlanningEvaluationBudget
) -> dict[str, Any]:
    cache: dict[tuple[float, ...], Any] = {}

    def posterior(point: Any) -> Any:
        key = tuple(float(value) for value in point)
        budget.consume(0)
        if key not in cache:
            budget.consume(1)
            cache[key] = evaluate_surrogate_desirability(models, goals, point)
        return cache[key]

    return _incumbent_result(goals, views, posterior)


def parse_planning_request(payload: Any) -> PlanningRequest:
    models: dict[int, type[PlanningRequest]] = {
        5: DesirabilityBatchCalculationRequest,
        6: DesirabilityFitCalculationRequest,
        7: DesirabilityCurveCalculationRequest,
    }
    if not isinstance(payload, dict) or type(payload.get("schema_version")) is not int:
        raise BayesianOptimizationError("bayesian_planning_input_invalid")
    model = models.get(payload["schema_version"])
    if model is None:
        raise BayesianOptimizationError("bayesian_planning_input_invalid")
    try:
        return model.model_validate(payload)
    except ValidationError:
        raise BayesianOptimizationError("bayesian_planning_input_invalid") from None


def fit_planning_model(payload: dict[str, Any]) -> dict[str, Any]:
    """Fit only actual responses once; persist complete bounded state for later views."""
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    started = time.perf_counter()
    request = parse_planning_request(payload)
    raw = request.q1_request().worker_payload()
    goals, specifications, options, _ = _validated_configuration(
        raw, versioned_curves=request.schema_version == 7
    )
    factors = candidate_factors(raw["factors"])
    views = _observation_views(raw, goals, factors)
    budget = _SearchBudget(
        started, started + options["time_budget_ms"] / 1000, options["max_evaluations_total"]
    )
    fit_policy = getattr(request, "fit_policy", None)
    moment_budget = PlanningEvaluationBudget(
        budget.deadline, request.batch_options.max_moment_evaluations
    )
    if (
        len({tuple(row) for row in views[goals[0].response_id].raw_x.tolist()})
        > moment_budget.maximum
    ):
        raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
    with threadpool_limits(limits=1):
        models, records, warnings, evaluations = _fit_response_models(
            goals,
            specifications,
            options,
            views,
            budget,
            fit_policy=BoFitPolicy(fit_policy.deterministic_start_count)
            if fit_policy is not None
            else None,
        )
        incumbent = _incumbent_from_models(goals, views, models, moment_budget)
        states = {
            key: dump_bo_surrogate(model, training_targets_scaled=views[key].training_y_scaled)
            for key, model in models.items()
        }
        budget.consume(0)
    return {
        "schema_version": 1,
        "policy": "source_locked_bo_planning_model_v1",
        "calculation_request": request.worker_payload(),
        "response_states": states,
        "response_models": records,
        "incumbent": incumbent,
        "observation_view": _shared_provenance(views[goals[0].response_id]),
        "warnings": warnings,
        "fit_evaluations": evaluations,
        "fit_elapsed_ms": (time.perf_counter() - started) * 1000,
    }


@dataclass(frozen=True)
class PlanningModel:
    request: PlanningRequest
    models: dict[str, Any]
    goals: list[Any]
    incumbent: dict[str, Any]
    excluded: list[list[float]]


def restore_planning_model(
    snapshot: dict[str, Any], *, budget: PlanningEvaluationBudget | None = None
) -> PlanningModel:
    """No optimizer, source-table read, or mutable-current-history lookup."""
    import numpy as np

    budget = budget or PlanningEvaluationBudget(_deadline(60_000), 65536)
    budget.consume(0)

    fields = {
        "schema_version",
        "policy",
        "calculation_request",
        "response_states",
        "response_models",
        "incumbent",
        "observation_view",
        "warnings",
        "fit_evaluations",
        "fit_elapsed_ms",
    }
    if (
        not isinstance(snapshot, dict)
        or set(snapshot) != fields
        or type(snapshot["schema_version"]) is not int
        or snapshot["schema_version"] != 1
        or snapshot["policy"] != "source_locked_bo_planning_model_v1"
    ):
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
    request = parse_planning_request(snapshot["calculation_request"])
    raw = request.q1_request().worker_payload()
    goals, specifications, _, _ = _validated_configuration(
        raw, versioned_curves=request.schema_version == 7
    )
    views = _observation_views(raw, goals, candidate_factors(raw["factors"]))
    states = snapshot["response_states"]
    records = snapshot["response_models"]
    if (
        not isinstance(states, dict)
        or set(states) != set(views)
        or not isinstance(records, list)
        or len(records) != len(views)
    ):
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
    models = {}
    fit_evaluations = 0
    for goal, record in zip(goals, records, strict=True):
        budget.consume(0)
        key = goal.response_id
        view = views[key]
        model = load_bo_surrogate(
            states[key], expected_training_targets_scaled=view.training_y_scaled
        )
        stored_metadata = {
            **model.metadata(),
            "package_versions": states[key]["fit"]["package_versions"],
            "factor_ids": list(view.factor_ids),
        }
        if (
            not np.array_equal(model.x_train, view.training_x)
            or tuple(model.group_counts) != tuple(int(n) for n in view.training_counts)
            or model.normalization_mean != view.normalization_mean
            or model.normalization_scale != view.normalization_scale
            or model.direction_multiplier != 1
            or model.kernel_spec != specifications[key][0]
            or model.policy != specifications[key][1]
            or model.jitter != request.search.jitter
            or model.optimizer["seed"] != request.search.random_seed
            or model.optimizer["restarts"] != request.search.hyperparameter_restart_count
            or model.optimizer["max_iterations"] != request.search.model_max_iterations
            or model.optimizer["max_evaluations"]
            != request.search.model_max_evaluations - fit_evaluations
            or record
            != {
                "response_id": key,
                "model": stored_metadata,
                "observation_view": view.provenance(),
            }
        ):
            raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
        fit_policy = getattr(request, "fit_policy", None)
        if fit_policy is None:
            if model.fit_diagnostics is not None:
                raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
        elif (
            model.fit_diagnostics is None
            or model.fit_diagnostics.get("policy") != FIT_POLICY
            or model.fit_diagnostics.get("deterministic_start_count")
            != fit_policy.deterministic_start_count
        ):
            raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
        fit_evaluations += model.optimizer["evaluations"]
        models[key] = model
    if (
        snapshot["fit_evaluations"] != fit_evaluations
        or fit_evaluations > request.search.model_max_evaluations
    ):
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
    if snapshot["observation_view"] != _shared_provenance(views[goals[0].response_id]):
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
    incumbent = snapshot["incumbent"]
    try:
        _Incumbent.model_validate(incumbent)
    except ValidationError:
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid") from None
    if (
        not isinstance(incumbent, dict)
        or type(incumbent.get("latent_incumbent_value")) not in {float, int}
        or not math.isfinite(incumbent["latent_incumbent_value"])
        or not 0 <= incumbent["latent_incumbent_value"] <= 1
    ):
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
    expected = _incumbent_from_models(goals, views, models, budget)
    if not _same_incumbent(incumbent, expected):
        raise BayesianOptimizationError("bayesian_planning_snapshot_invalid")
    # Completed coordinates must be excluded even if an internal caller omitted them.
    excluded = [list(row) for row in request.excluded_normalized]
    for row in views[goals[0].response_id].raw_x.tolist():
        if row not in excluded:
            excluded.append(row)
    return PlanningModel(request, models, goals, incumbent, excluded)


def _same_incumbent(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(
                _same_incumbent(actual[key], value)
                for key, value in expected.items()
                if key not in {"integration_evaluations", "estimated_absolute_error"}
            )
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_same_incumbent(a, e) for a, e in zip(actual, expected, strict=True))
        )
    if type(expected) is float:
        return (
            type(actual) in {int, float}
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=2e-10, abs_tol=0)
        )
    return type(actual) is type(expected) and actual == expected


def evaluate_planning_points(
    snapshot: dict[str, Any],
    points: list[dict[str, float]],
    *,
    time_budget_ms: int = 60_000,
    max_moment_evaluations: int = 4096,
    eligibility_excluded_normalized: list[list[float]] | None = None,
    absolute_deadline: float | None = None,
    compute_acquisition: bool = True,
) -> list[dict[str, Any]]:
    """Evaluate bounded complete points; output never becomes measured responses."""
    if type(compute_acquisition) is not bool:
        raise BayesianOptimizationError("bayesian_planning_input_invalid")
    deadline = _deadline(time_budget_ms)
    if absolute_deadline is not None:
        if not math.isfinite(absolute_deadline):
            raise BayesianOptimizationError("bayesian_planning_input_invalid")
        deadline = min(deadline, absolute_deadline)
        _check_deadline(deadline)
    budget = PlanningEvaluationBudget(deadline, max_moment_evaluations)
    model = restore_planning_model(snapshot, budget=budget)
    request = model.request
    rows = validated_candidate_rows(
        points,
        [f.model_dump() for f in request.factors],
        [c.model_dump() for c in request.constraints],
        excluded_normalized=_eligibility_coordinates(model, eligibility_excluded_normalized),
        duplicate_tolerance=request.search.duplicate_tolerance,
        include_constraint_violations=True,
        check_budget=lambda: budget.consume(0),
    )
    if len(rows) > budget.maximum - budget.used:
        raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
    result = []
    for row in rows:
        budget.consume(1)
        point = [row["normalized_coordinates"][factor.factor_id] for factor in request.factors]
        base = evaluate_surrogate_desirability(model.models, model.goals, point)
        acquisition = (
            beta_expected_improvement(
                base.moments.mean,
                base.moments.variance,
                model.incumbent["latent_incumbent_value"],
                xi=request.xi_desirability,
            )
            if compute_acquisition
            else None
        )
        result.append(
            {
                **row,
                "response_predictions": [asdict(value) for value in base.responses],
                "desirability_moments": asdict(base.moments),
                "acquisition": {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(acquisition),
                    "xi_desirability": request.xi_desirability,
                }
                if acquisition is not None
                else None,
                "prediction_source": "completed_observations_base_posterior",
            }
        )
    _check_deadline(deadline)
    return result


def score_ordered_selection(
    snapshot: dict[str, Any],
    points: list[dict[str, float]],
    *,
    time_budget_ms: int = 60_000,
    eligibility_excluded_normalized: list[list[float]] | None = None,
) -> dict[str, Any]:
    """Recompute each selected prefix; manual rows are not claimed as search optima."""
    import numpy as np

    deadline = _deadline(time_budget_ms)
    if not isinstance(points, list) or not 1 <= len(points) <= 8:
        raise BayesianOptimizationError("bayesian_planning_selection_invalid")
    # Source validation also consumes the explicit overall moment budget.
    parsed = parse_planning_request(snapshot.get("calculation_request"))
    validation_budget = PlanningEvaluationBudget(
        deadline, parsed.batch_options.max_moment_evaluations
    )
    model = restore_planning_model(snapshot, budget=validation_budget)
    request = model.request
    rows = validated_candidate_rows(
        points,
        [f.model_dump() for f in request.factors],
        [c.model_dump() for c in request.constraints],
        excluded_normalized=_eligibility_coordinates(model, eligibility_excluded_normalized),
        duplicate_tolerance=request.search.duplicate_tolerance,
    )
    if any(not row["eligible"] for row in rows):
        raise BayesianOptimizationError("bayesian_planning_selection_ineligible")
    maximum = request.batch_options.max_moment_evaluations
    consumed = validation_budget.used
    selected: list[list[float]] = []
    items = []

    def consume(count: int) -> None:
        nonlocal consumed
        _check_deadline(deadline)
        if count > maximum - consumed:
            raise BayesianOptimizationError("bayesian_desirability_batch_budget_exhausted")
        consumed += count

    for index, row in enumerate(rows):
        point = [row["normalized_coordinates"][f.factor_id] for f in request.factors]
        nearest = min((math.dist(point, old) for old in selected), default=None)
        if nearest is not None and (
            nearest <= request.search.duplicate_tolerance
            or nearest < request.batch_options.min_batch_distance_normalized
        ):
            raise BayesianOptimizationError("bayesian_planning_selection_distance")
        planner = DesirabilityBatchAcquisition(
            model.models,
            model.goals,
            model.incumbent["latent_incumbent_value"],
            np.asarray(selected).reshape((-1, len(request.factors))),
            xi=request.xi_desirability,
            root_seed=request.search.random_seed,
            sample_count=request.batch_options.sample_count,
            max_moment_evaluations=maximum - consumed,
            check_budget=lambda: _check_deadline(deadline),
            consume_moments=consume,
        )
        scored = planner.score([point], include_details=True)
        base = scored.base_posteriors[0]
        acquisition = beta_expected_improvement(
            base.moments.mean,
            base.moments.variance,
            model.incumbent["latent_incumbent_value"],
            xi=request.xi_desirability,
        )
        items.append(
            {
                **row,
                "rank": index + 1,
                "nearest_selected_distance": nearest,
                "response_predictions": [asdict(value) for value in base.responses],
                "desirability_moments": asdict(base.moments),
                "acquisition": {
                    "kind": "desirability_beta_expected_improvement",
                    **asdict(acquisition),
                    "xi_desirability": request.xi_desirability,
                },
                "planning": {
                    "score": float(scored.scores[0]),
                    "mc_standard_error": float(scored.mc_standard_error[0]),
                    "sampler": planner.metadata(),
                    "conditional_variance_raw": {
                        key: float(value[0])
                        for key, value in scored.conditional_variance_raw.items()
                    },
                    "proof": scored.details
                    or {
                        "response_proofs": {},
                        "thresholds": [],
                        "sample_moments": [],
                    },
                },
            }
        )
        selected.append(point)
    _check_deadline(deadline)
    return {
        "schema_version": 1,
        "selection_policy": "manual_ordered_fixed_model_v1",
        "model_refit": False,
        "items": items,
        "moment_evaluations": consumed,
        "max_moment_evaluations": maximum,
    }


def _eligibility_coordinates(
    model: PlanningModel,
    current: list[list[float]] | None,
) -> list[list[float]]:
    if current is None:
        return model.excluded
    if not isinstance(current, list) or len(current) > 200:
        raise BayesianOptimizationError("bayesian_candidate_input_invalid")
    rows = list(current)
    for row in model.excluded:
        if row not in rows:
            rows.append(row)
    return rows


def _deadline(milliseconds: int) -> float:
    if type(milliseconds) is not int or not 1000 <= milliseconds <= 60_000:
        raise BayesianOptimizationError("bayesian_planning_input_invalid")
    return time.perf_counter() + milliseconds / 1000


def _check_deadline(deadline: float) -> None:
    if time.perf_counter() >= deadline:
        raise BayesianOptimizationError("bayesian_optimization_time_budget_exhausted")
