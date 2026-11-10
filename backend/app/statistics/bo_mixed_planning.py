"""Reusable source-locked mixed BO models; fits and later views are separate."""

from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass
from typing import Any

from app.api.v1.schemas.bo_mixed_planning import (
    EvaluatedMixedCandidateRow,
    MixedPlanningCalculationRequest,
    MixedPlanningSelectionCalculation,
)
from app.api.v1.schemas.bo_mixed_studies import mixed_constraint_definitions, mixed_factor_domains
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import composite_desirability, independent_desirability_moments
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_desirability_posterior import (
    DesirabilityResponsePosterior,
    SurrogateDesirability,
    raw_posterior_standard_deviation,
)
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_mixed_candidate_points import (
    canonical_mixed_point,
    mixed_point_distance,
    validated_mixed_candidate_rows,
)
from app.statistics.bo_mixed_snapshot import dump_bo_mixed_surrogate, load_bo_mixed_surrogate
from app.statistics.bo_mixed_surrogate import fit_bo_mixed_surrogate
from app.statistics.bo_planning_model import PlanningEvaluationBudget, _deadline, _same_incumbent
from app.statistics.bo_surrogate import BoSurrogatePolicy

POLICY = "source_locked_mixed_bo_planning_model_v1"


def _error(code: str = "bayesian_mixed_planning_snapshot_invalid") -> BayesianOptimizationError:
    return BayesianOptimizationError(code)


def parse_mixed_planning_request(payload: Any) -> MixedPlanningCalculationRequest:
    try:
        return MixedPlanningCalculationRequest.model_validate(payload)
    except (ValueError, TypeError, OverflowError):
        raise _error("bayesian_mixed_planning_input_invalid") from None


@dataclass(frozen=True)
class _TrainingView:
    raw_x: Any
    training_x: Any
    targets_scaled: Any
    within_ss_scaled: Any
    counts: tuple[int, ...]
    mean: float
    scale: float
    provenance: dict[str, Any]
    warnings: tuple[str, ...]


def _training_views(
    request: MixedPlanningCalculationRequest,
) -> tuple[dict[str, _TrainingView], dict[str, Any]]:
    import numpy as np

    domains = mixed_factor_domains(request.factors)
    keys = [domain.factor_id for domain in domains]
    raw_x = []
    actuals = []
    group_map: dict[tuple[Any, ...], list[int]] = {}
    for index, row in enumerate(request.observations):
        actual, encoded = canonical_mixed_point(domains, row.actual_coordinates)
        raw_x.append(encoded)
        actuals.append(actual)
        identity = (tuple(actual[key] for key in keys), row.condition_key)
        group_map.setdefault(identity, []).append(index)
    groups = list(group_map.values())
    unique_points = len({tuple(actual[key] for key in keys) for actual in actuals})
    if unique_points < max(2, len(domains) + 1):
        raise _error("bayesian_unique_conditions_insufficient")
    compressed = request.observation_policy.mode == "exact_replicates"
    training_groups = groups if compressed else [[index] for index in range(len(raw_x))]
    x = np.asarray(raw_x, dtype=float)
    shared = {
        "mode": request.observation_policy.mode,
        "raw_observation_count": len(raw_x),
        "unique_condition_count": len(groups),
        "unique_coordinate_count": unique_points,
        "effective_training_count": len(training_groups),
        "groups": [
            {
                "member_trial_ids": [str(request.observations[index].trial_id) for index in group],
                "member_indices": list(group),
                "n": len(group),
                "canonical_actual_coordinates": actuals[group[0]],
                "encoded_coordinates": dict(zip(keys, raw_x[group[0]], strict=True)),
                "condition_key": request.observations[group[0]].condition_key,
            }
            for group in groups
        ],
    }
    views = {}
    for definition in request.objective.responses:
        values = np.asarray(
            [row.response_values[definition.response_id] for row in request.observations],
            dtype=float,
        )
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            mean, scale = float(np.mean(values)), float(np.std(values, ddof=0))
        if not math.isfinite(mean) or not math.isfinite(scale):
            raise _error("bayesian_optimization_surrogate_fit_failed")
        warnings = []
        if scale <= max(1e-12, abs(mean) * 1e-12):
            scale = 1.0
            warnings.append("bayesian_optimization_constant_objective")
        with np.errstate(over="ignore", invalid="ignore", under="ignore"):
            standardized = (values - mean) / scale
            means = np.asarray([np.mean(standardized[group]) for group in training_groups])
            within = np.asarray(
                [
                    np.sum((standardized[group] - means[index]) ** 2)
                    for index, group in enumerate(training_groups)
                ]
            )
        if (
            not np.all(np.isfinite(standardized))
            or not np.all(np.isfinite(means))
            or not np.all(np.isfinite(within))
        ):
            raise _error("bayesian_optimization_surrogate_fit_failed")
        stats = []
        for group in groups:
            group_values = values[group]
            with np.errstate(over="ignore", invalid="ignore"):
                group_mean = float(np.mean(group_values))
                group_ss = float(np.sum((group_values - group_mean) ** 2))
            if not math.isfinite(group_mean) or not math.isfinite(group_ss):
                raise _error("bayesian_observation_group_invalid")
            stats.append(
                {
                    "member_trial_ids": [
                        str(request.observations[index].trial_id) for index in group
                    ],
                    "mean": group_mean,
                    "within_ss": group_ss,
                    "sample_variance": group_ss / (len(group) - 1) if len(group) > 1 else None,
                }
            )
        provenance = {
            **shared,
            "response_statistics": stats,
            "normalization": {"mean": mean, "scale": scale, "ddof": 0, "direction_multiplier": 1.0},
        }
        views[definition.response_id] = _TrainingView(
            x,
            x[[group[0] for group in training_groups]],
            means,
            within,
            tuple(len(group) for group in training_groups),
            mean,
            scale,
            provenance,
            tuple(warnings),
        )
    return views, shared


def evaluate_mixed_surrogate_desirability(
    models: Any, goals: Any, point: Any
) -> SurrogateDesirability:
    import numpy as np

    x = np.asarray(point, dtype=float).reshape(1, -1)
    responses = []
    for goal in goals:
        model = models[goal.response_id]
        if model.direction_multiplier != 1:
            raise _error()
        prediction = model.predict(x)
        latent = float(prediction.latent_variance_scaled[0])
        predictive = float(prediction.predictive_variance_scaled[0])
        mean = (
            float(prediction.mean_scaled[0]) * model.normalization_scale + model.normalization_mean
        )
        if not math.isfinite(mean) or latent < 0 or predictive < latent:
            raise _error()
        responses.append(
            DesirabilityResponsePosterior(
                goal.response_id,
                mean,
                raw_posterior_standard_deviation(latent, model.normalization_scale),
                raw_posterior_standard_deviation(predictive, model.normalization_scale),
            )
        )
    moments = independent_desirability_moments(
        {
            item.response_id: (item.mean_raw, item.latent_standard_deviation_raw)
            for item in responses
        },
        goals,
    )
    return SurrogateDesirability(moments, tuple(responses))


def _incumbent(
    request: MixedPlanningCalculationRequest,
    models: dict[str, Any],
    views: dict[str, _TrainingView],
    budget: PlanningEvaluationBudget,
) -> dict[str, Any]:
    goals = [response.calculation_goal() for response in request.objective.responses]
    keys = [factor.factor_id for factor in request.factors]
    raw_x = views[goals[0].response_id].raw_x
    cache = {}
    actual_results: list[dict[str, Any]] = []
    posterior_results: list[dict[str, Any]] = []
    for row, point in zip(request.observations, raw_x, strict=True):
        budget.consume(0)
        identity = tuple(float(value) for value in point)
        if identity not in cache:
            budget.consume(1)
            cache[identity] = evaluate_mixed_surrogate_desirability(models, goals, point)
        actual_results.append(
            {
                "trial_id": str(row.trial_id),
                "value": composite_desirability(row.response_values, goals),
            }
        )
        posterior_results.append(
            {"trial_id": str(row.trial_id), "moments": asdict(cache[identity].moments)}
        )
    best_actual = max(range(len(actual_results)), key=lambda index: actual_results[index]["value"])
    best_latent = max(
        range(len(posterior_results)), key=lambda index: posterior_results[index]["moments"]["mean"]
    )
    return {
        "policy": "max_posterior_expected_desirability_at_observed_coordinates_v1",
        "best_observed_desirability": actual_results[best_actual]["value"],
        "best_observed_trial_id": actual_results[best_actual]["trial_id"],
        "latent_incumbent_value": posterior_results[best_latent]["moments"]["mean"],
        "latent_incumbent_trial_id": posterior_results[best_latent]["trial_id"],
        "latent_incumbent_encoded_coordinates": dict(
            zip(keys, raw_x[best_latent].tolist(), strict=True)
        ),
        "coordinate_encoding": "numeric_normalized_category_index_v1",
        "observed_trial_desirabilities": actual_results,
        "training_posterior_desirabilities": posterior_results,
    }


def fit_mixed_planning_model(payload: dict[str, Any]) -> dict[str, Any]:
    """Fit each raw response once, sharing the original deadline and fit budget."""
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    started = time.perf_counter()
    request = parse_mixed_planning_request(payload)
    budget = PlanningEvaluationBudget(
        started + request.search.time_budget_ms / 1000, request.max_moment_evaluations
    )
    domains = mixed_factor_domains(request.factors)
    views, shared = _training_views(request)
    if len({tuple(row) for row in next(iter(views.values())).raw_x.tolist()}) > budget.maximum:
        raise _error("bayesian_desirability_batch_budget_exhausted")
    models, records, states = {}, [], {}
    warnings = []
    evaluations = 0
    specifications = {item.response_id: item for item in request.response_models}
    with threadpool_limits(limits=1):
        for goal in request.objective.responses:
            budget.consume(0)
            remaining = request.search.model_max_evaluations - evaluations
            if remaining < 2:
                raise _error("bayesian_optimization_budget_exhausted")
            key, specification = goal.response_id, specifications[goal.response_id]
            view = views[key]
            model = fit_bo_mixed_surrogate(
                view.training_x,
                view.targets_scaled,
                domains,
                BoSurrogatePolicy(**specification.surrogate.model_dump()),
                {**request.search.model_dump(), "model_max_evaluations": remaining},
                deadline=budget.deadline,
                normalization_mean=view.mean,
                normalization_scale=view.scale,
                direction_multiplier=1.0,
                group_counts=view.counts,
                within_ss_scaled=view.within_ss_scaled,
                raw_observation_count=len(request.observations),
                kernel_spec=BoKernelSpec(specification.kernel.kind),
                fit_policy=BoFitPolicy(request.fit_policy.deterministic_start_count),
            )
            evaluations += model.optimizer["evaluations"]
            if evaluations > request.search.model_max_evaluations:
                raise _error("bayesian_optimization_budget_exhausted")
            models[key] = model
            records.append(
                {"response_id": key, "model": model.metadata(), "observation_view": view.provenance}
            )
            states[key] = dump_bo_mixed_surrogate(model)
            warnings.extend([*view.warnings, *model.warning_codes])
            budget.consume(0)
        incumbent = _incumbent(request, models, views, budget)
    return {
        "schema_version": 2,
        "policy": POLICY,
        "calculation_request": request.worker_payload(),
        "response_states": states,
        "response_models": records,
        "incumbent": incumbent,
        "observation_view": shared,
        "warnings": list(dict.fromkeys(warnings)),
        "fit_evaluations": evaluations,
        "fit_elapsed_ms": (time.perf_counter() - started) * 1000,
    }


@dataclass(frozen=True)
class MixedPlanningModel:
    request: MixedPlanningCalculationRequest
    models: dict[str, Any]
    goals: list[Any]
    incumbent: dict[str, Any]
    excluded_encoded: list[list[float]]


def restore_mixed_planning_model(
    snapshot: dict[str, Any], *, budget: PlanningEvaluationBudget | None = None
) -> MixedPlanningModel:
    """Bind safe numeric state to source rows, then check observed-location incumbent."""
    import numpy as np

    budget = budget or PlanningEvaluationBudget(_deadline(60000), 65536)
    budget.consume(0)
    expected_fields = {
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
        type(snapshot) is not dict
        or set(snapshot) != expected_fields
        or type(snapshot["schema_version"]) is not int
        or snapshot["schema_version"] != 2
        or snapshot["policy"] != POLICY
    ):
        raise _error()
    try:
        request = parse_mixed_planning_request(snapshot["calculation_request"])
        if request.worker_payload() != snapshot["calculation_request"]:
            raise _error()
        views, shared = _training_views(request)
        domains = mixed_factor_domains(request.factors)
        specifications = {item.response_id: item for item in request.response_models}
        states, records = snapshot["response_states"], snapshot["response_models"]
        if (
            type(states) is not dict
            or set(states) != set(views)
            or type(records) is not list
            or len(records) != len(views)
        ):
            raise _error()
        models = {}
        warnings = []
        evaluations = 0
        for goal, record in zip(request.objective.responses, records, strict=True):
            budget.consume(0)
            key, specification = goal.response_id, specifications[goal.response_id]
            view = views[key]
            model = load_bo_mixed_surrogate(
                states[key],
                expected_factor_domains=domains,
                expected_training_targets_scaled=view.targets_scaled,
                expected_within_ss_scaled=view.within_ss_scaled,
            )
            metadata = {
                **model.metadata(),
                "package_versions": states[key]["fit"]["package_versions"],
            }
            if (
                not np.array_equal(model.x_train, view.training_x)
                or model.group_counts != view.counts
                or model.normalization_mean != view.mean
                or model.normalization_scale != view.scale
                or model.direction_multiplier != 1
                or model.raw_observation_count != len(request.observations)
                or model.kernel_spec != BoKernelSpec(specification.kernel.kind)
                or model.policy != BoSurrogatePolicy(**specification.surrogate.model_dump())
                or model.jitter != request.search.jitter
                or model.optimizer["seed"] != request.search.random_seed
                or model.optimizer["restarts"] != request.search.hyperparameter_restart_count
                or model.optimizer["max_iterations"] != request.search.model_max_iterations
                or model.optimizer["max_evaluations"]
                != request.search.model_max_evaluations - evaluations
                or model.fit_diagnostics is None
                or model.fit_diagnostics["deterministic_start_count"]
                != request.fit_policy.deterministic_start_count
                or record
                != {"response_id": key, "model": metadata, "observation_view": view.provenance}
            ):
                raise _error()
            evaluations += model.optimizer["evaluations"]
            models[key] = model
            warnings.extend([*view.warnings, *model.warning_codes])
        if (
            snapshot["observation_view"] != shared
            or snapshot["warnings"] != list(dict.fromkeys(warnings))
            or type(snapshot["fit_evaluations"]) is not int
            or snapshot["fit_evaluations"] != evaluations
            or evaluations > request.search.model_max_evaluations
            or type(snapshot["fit_elapsed_ms"]) not in {float, int}
            or not math.isfinite(snapshot["fit_elapsed_ms"])
            or snapshot["fit_elapsed_ms"] < 0
        ):
            raise _error()
        incumbent = _incumbent(request, models, views, budget)
        if (
            not _same_incumbent(snapshot["incumbent"], incumbent)
            or snapshot["incumbent"]["latent_incumbent_encoded_coordinates"]
            != incumbent["latent_incumbent_encoded_coordinates"]
        ):
            raise _error()
        excluded = [list(row) for row in request.excluded_encoded]
        for point in next(iter(views.values())).raw_x.tolist():
            if point not in excluded:
                excluded.append(point)
        budget.consume(0)
        return MixedPlanningModel(
            request,
            models,
            [goal.calculation_goal() for goal in request.objective.responses],
            snapshot["incumbent"],
            excluded,
        )
    except BayesianOptimizationError as exc:
        if exc.code in {
            "bayesian_optimization_time_budget_exhausted",
            "bayesian_desirability_batch_budget_exhausted",
        }:
            raise
        raise _error() from None
    except (ValueError, KeyError, TypeError, AttributeError, OverflowError):
        raise _error() from None


def evaluate_mixed_planning_points(
    snapshot: dict[str, Any],
    points: list[dict[str, Any]],
    *,
    time_budget_ms: int = 60000,
    max_moment_evaluations: int = 65536,
    eligibility_excluded_encoded: list[list[float]] | None = None,
    compute_acquisition: bool = True,
    ordinal_rank_distance: bool = False,
    absolute_deadline: float | None = None,
) -> list[dict[str, Any]]:
    """Read-only complete-point conditional views, with base latent uncertainty."""
    deadline = _deadline(time_budget_ms)
    if absolute_deadline is not None:
        if type(absolute_deadline) not in {int, float} or not math.isfinite(absolute_deadline):
            raise _error("bayesian_planning_input_invalid")
        deadline = min(deadline, absolute_deadline)
    if type(compute_acquisition) is not bool:
        raise _error("bayesian_planning_input_invalid")
    budget = PlanningEvaluationBudget(deadline, max_moment_evaluations)
    model = restore_mixed_planning_model(snapshot, budget=budget)
    domains = mixed_factor_domains(model.request.factors)
    excluded = [list(point) for point in model.excluded_encoded]
    if eligibility_excluded_encoded is not None:
        if (
            type(eligibility_excluded_encoded) is not list
            or len(eligibility_excluded_encoded) > 200
        ):
            raise _error("bayesian_planning_input_invalid")
        for point in eligibility_excluded_encoded:
            if point not in excluded:
                excluded.append(point)
    rows = validated_mixed_candidate_rows(
        points,
        domains,
        mixed_constraint_definitions(model.request.constraints),
        excluded_encoded=excluded,
        duplicate_tolerance=model.request.search.duplicate_tolerance,
        include_constraint_violations=True,
        ordinal_rank_distance=ordinal_rank_distance,
        check_budget=lambda: budget.consume(0),
    )
    if len(rows) > budget.maximum - budget.used:
        raise _error("bayesian_desirability_batch_budget_exhausted")
    result = []
    for row in rows:
        budget.consume(1)
        point = [row["encoded_coordinates"][domain.factor_id] for domain in domains]
        prediction = evaluate_mixed_surrogate_desirability(model.models, model.goals, point)
        acquisition = None
        if compute_acquisition:
            acquisition = {
                "kind": "desirability_beta_expected_improvement",
                **asdict(
                    beta_expected_improvement(
                        prediction.moments.mean,
                        prediction.moments.variance,
                        model.incumbent["latent_incumbent_value"],
                        xi=model.request.xi_desirability,
                    )
                ),
                "xi_desirability": model.request.xi_desirability,
            }
        result.append(
            EvaluatedMixedCandidateRow.model_validate(
                {
                    **row,
                    "response_predictions": [asdict(item) for item in prediction.responses],
                    "desirability_moments": asdict(prediction.moments),
                    "acquisition": acquisition,
                    "prediction_source": "completed_observations_base_posterior",
                }
            ).model_dump(mode="json")
        )
        budget.consume(0)
    return result


def score_mixed_ordered_selection(
    snapshot: dict[str, Any],
    points: list[dict[str, Any]],
    *,
    time_budget_ms: int = 60000,
    eligibility_excluded_encoded: list[list[float]] | None = None,
    sample_count: int = 64,
    min_batch_distance: float = 0.0,
    max_moment_evaluations: int = 8192,
    ordinal_rank_distance: bool = False,
    absolute_deadline: float | None = None,
) -> dict[str, Any]:
    """Score a fixed order with joint latent draws; never fit or search for alternatives."""
    import numpy as np

    from app.statistics.bo_desirability_batch_acquisition import DesirabilityBatchAcquisition

    deadline = _deadline(time_budget_ms)
    if absolute_deadline is not None:
        if type(absolute_deadline) not in {int, float} or not math.isfinite(absolute_deadline):
            raise _error("bayesian_planning_input_invalid")
        deadline = min(deadline, absolute_deadline)
    if (
        type(points) is not list
        or not 1 <= len(points) <= 8
        or type(sample_count) is not int
        or not 16 <= sample_count <= 256
        or type(min_batch_distance) not in {int, float}
        or not math.isfinite(min_batch_distance)
        or min_batch_distance < 0
        or type(ordinal_rank_distance) is not bool
    ):
        raise _error("bayesian_planning_selection_invalid")
    budget = PlanningEvaluationBudget(deadline, max_moment_evaluations)
    model = restore_mixed_planning_model(snapshot, budget=budget)
    request = model.request
    domains = mixed_factor_domains(request.factors)
    excluded = [list(point) for point in model.excluded_encoded]
    if eligibility_excluded_encoded is not None:
        if (
            type(eligibility_excluded_encoded) is not list
            or len(eligibility_excluded_encoded) > 200
        ):
            raise _error("bayesian_planning_input_invalid")
        for point in eligibility_excluded_encoded:
            if point not in excluded:
                excluded.append(point)
    rows = validated_mixed_candidate_rows(
        points,
        domains,
        mixed_constraint_definitions(request.constraints),
        excluded_encoded=excluded,
        duplicate_tolerance=request.search.duplicate_tolerance,
        ordinal_rank_distance=ordinal_rank_distance,
        check_budget=lambda: budget.consume(0),
    )
    if any(not row["eligible"] for row in rows):
        raise _error("bayesian_planning_selection_ineligible")
    required = len(rows) + (len(rows) - 1) * sample_count
    if required > budget.maximum - budget.used:
        raise _error("bayesian_desirability_batch_budget_exhausted")
    selected: list[list[float]] = []
    items = []
    for index, row in enumerate(rows):
        budget.consume(0)
        point = [row["encoded_coordinates"][domain.factor_id] for domain in domains]
        nearest = min(
            (
                mixed_point_distance(
                    point, old, domains, ordinal_rank_distance=ordinal_rank_distance
                )
                for old in selected
            ),
            default=None,
        )
        if nearest is not None and (
            nearest <= request.search.duplicate_tolerance or nearest < min_batch_distance
        ):
            raise _error("bayesian_planning_selection_distance")
        planner = DesirabilityBatchAcquisition(
            model.models,
            model.goals,
            model.incumbent["latent_incumbent_value"],
            np.asarray(selected).reshape((-1, len(domains))),
            xi=request.xi_desirability,
            root_seed=request.search.random_seed,
            sample_count=sample_count,
            max_moment_evaluations=budget.maximum - budget.used,
            check_budget=lambda: budget.consume(0),
            consume_moments=budget.consume,
            factor_domains=domains,
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
                "prediction_source": "completed_observations_base_posterior",
                "planning": {
                    "score": float(scored.scores[0]),
                    "mc_standard_error": float(scored.mc_standard_error[0]),
                    "sampler": planner.metadata(),
                    "conditional_variance_raw": {
                        key: float(value[0])
                        for key, value in scored.conditional_variance_raw.items()
                    },
                    "proof": scored.details
                    or {"response_proofs": {}, "thresholds": [], "sample_moments": []},
                },
            }
        )
        selected.append(point)
    budget.consume(0)
    return MixedPlanningSelectionCalculation.model_validate(
        {
            "schema_version": 2,
            "selection_policy": "manual_ordered_mixed_model_v1",
            "model_refit": False,
            "distance_policy": rows[0]["distance_policy"],
            "ordinal_rank_distance": ordinal_rank_distance,
            "items": items,
            "moment_evaluations": budget.used,
            "max_moment_evaluations": budget.maximum,
        }
    ).model_dump(mode="json")
