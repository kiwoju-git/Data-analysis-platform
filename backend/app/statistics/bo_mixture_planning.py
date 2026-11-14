"""Safe mixture GP snapshots with explicit numeric/mixed inner-model dispatch."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from typing import Any

from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_mixed_workflow import MixedFitOptions
from app.statistics.bayesian_optimization import BayesianOptimizationError
from app.statistics.bo_desirability import composite_desirability
from app.statistics.bo_desirability_acquisition import beta_expected_improvement
from app.statistics.bo_factor_domains import (
    BoCategoricalFactorDomain,
    BoPseudocomponentFactorDomain,
)
from app.statistics.bo_fit_policy import BoFitPolicy
from app.statistics.bo_kernels import BoKernelSpec
from app.statistics.bo_mixed_initial_design import mixed_constraints_satisfied
from app.statistics.bo_mixed_planning import evaluate_mixed_surrogate_desirability
from app.statistics.bo_mixed_snapshot import dump_bo_mixed_surrogate, load_bo_mixed_surrogate
from app.statistics.bo_mixed_surrogate import fit_bo_mixed_surrogate
from app.statistics.bo_mixture_design import METRIC, BoMixtureDesign
from app.statistics.bo_mixture_design import POLICY as ENCODING
from app.statistics.bo_surrogate import BoSurrogate, BoSurrogatePolicy, fit_bo_surrogate
from app.statistics.bo_surrogate_snapshot import dump_bo_surrogate, load_bo_surrogate
from app.statistics.doe_factor_domain import DoeFactorDomain

POLICY = "source_locked_mixture_bo_planning_model_v1"


def _error(code: str = "bayesian_mixture_planning_snapshot_invalid") -> BayesianOptimizationError:
    return BayesianOptimizationError(code)


def _parsed(
    payload: dict[str, Any],
) -> tuple[BoMixtureDesign, Any, MixedFitOptions, list[dict[str, Any]]]:
    from pydantic import TypeAdapter

    if type(payload) is not dict or set(payload) != {
        "design_domain",
        "objective",
        "fit",
        "observations",
    }:
        raise _error("bayesian_mixture_planning_input_invalid")
    design = BoMixtureDesign.from_payload(payload["design_domain"])
    objective: AnyDesirabilityObjective = TypeAdapter(AnyDesirabilityObjective).validate_python(
        payload["objective"]
    )
    fit = MixedFitOptions.model_validate(payload["fit"])
    rows = payload["observations"]
    if type(rows) is not list or not max(2, len(design.keys)) <= len(rows) <= 200:
        raise _error("bayesian_optimization_history_incomplete")
    ids, unique = set(), set()
    response_ids = {r.response_id for r in objective.responses}
    if {r.response_id for r in fit.response_models} != response_ids or len(
        fit.response_models
    ) != len(response_ids):
        raise _error("bayesian_desirability_response_mapping_invalid")
    for row in rows:
        if type(row) is not dict or set(row) != {
            "trial_id",
            "actual_coordinates",
            "response_values",
        }:
            raise _error("bayesian_mixture_planning_input_invalid")
        actual, _ = design.canonical(row["actual_coordinates"])
        if (
            row["trial_id"] in ids
            or type(row["trial_id"]) is not str
            or set(row["response_values"]) != response_ids
        ):
            raise _error("bayesian_observation_identity_invalid")
        if any(
            type(v) not in {int, float} or not math.isfinite(v)
            for v in row["response_values"].values()
        ):
            raise _error("bayesian_observation_identity_invalid")
        if not mixed_constraints_satisfied(actual, design.constraints):
            raise _error("bayesian_candidate_constraint_violation")
        ids.add(row["trial_id"])
        unique.add(tuple(actual[k] for k in design.keys))
    if len(unique) < max(2, len(design.keys)):
        raise _error("bayesian_unique_conditions_insufficient")
    if len(unique) > fit.max_moment_evaluations:
        raise _error("bayesian_desirability_batch_budget_exhausted")
    return design, objective, fit, rows


def _kernel_domains(design: BoMixtureDesign) -> tuple[Any, ...]:
    # The inputs already are stored pseudocomponents. [0,1] here describes their
    # executable kernel coordinates, not independent actual-component scaling.
    digest = hashlib.sha256(
        json.dumps(
            design.mixture.payload(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return (
        tuple(
            BoPseudocomponentFactorDomain(
                c.factor_id,
                DoeFactorDomain(0.0, 1.0),
                (c.high - c.low) / design.mixture.denominator,
                digest,
            )
            for c in design.mixture.components
        )
        + design.process_factors
    )


def _training(
    design: BoMixtureDesign, fit: MixedFitOptions, rows: list[dict[str, Any]], response_id: str
) -> tuple[Any, Any, tuple[tuple[int, ...], ...], Any, Any, float, float]:
    import numpy as np

    x = np.asarray([design.canonical(row["actual_coordinates"])[1] for row in rows])
    y = np.asarray([row["response_values"][response_id] for row in rows], dtype=float)
    mean, scale = float(np.mean(y)), float(np.std(y))
    if not math.isfinite(mean) or not math.isfinite(scale):
        raise _error("bayesian_optimization_surrogate_fit_failed")
    if scale <= max(1e-12, abs(mean) * 1e-12):
        scale = 1.0
    groups: dict[tuple[Any, ...], list[int]] = {}
    for index, row in enumerate(rows):
        identity = (
            tuple(row["actual_coordinates"][k] for k in design.keys)
            if fit.observation_policy.mode == "exact_replicates"
            else (index,)
        )
        groups.setdefault(identity, []).append(index)
    members = tuple(tuple(g) for g in groups.values())
    standardized = (y - mean) / scale
    targets = np.asarray([np.mean(standardized[list(g)]) for g in members])
    within = np.asarray(
        [np.sum((standardized[list(g)] - targets[i]) ** 2) for i, g in enumerate(members)]
    )
    return x, y, members, targets, within, mean, scale


def fit_mixture_planning_model(payload: dict[str, Any]) -> dict[str, Any]:
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    design, objective, fit, rows = _parsed(payload)
    started = time.perf_counter()
    deadline = started + fit.search.time_budget_ms / 1000
    mixed = any(isinstance(f, BoCategoricalFactorDomain) for f in design.process_factors)
    states: dict[str, Any] = {}
    metadata: list[dict[str, Any]] = []
    warnings: list[str] = []
    evaluations = 0
    specifications = {r.response_id: r for r in fit.response_models}
    with threadpool_limits(limits=1):
        for goal in objective.responses:
            key, specification = goal.response_id, specifications[goal.response_id]
            x, y, members, targets, within, mean, scale = _training(design, fit, rows, key)
            search = {
                **fit.search.model_dump(),
                "model_max_evaluations": fit.search.model_max_evaluations - evaluations,
            }
            if search["model_max_evaluations"] < 2:
                raise _error("bayesian_optimization_budget_exhausted")
            kernel_spec = BoKernelSpec(specification.kernel.kind)
            fit_policy = BoFitPolicy(fit.fit_policy.deterministic_start_count)
            policy = BoSurrogatePolicy(**specification.surrogate.model_dump())
            model: BoSurrogate
            if mixed:
                model = fit_bo_mixed_surrogate(
                    x[[g[0] for g in members]],
                    targets,
                    _kernel_domains(design),
                    policy,
                    search,
                    normalization_mean=mean,
                    normalization_scale=scale,
                    direction_multiplier=1.0,
                    group_counts=tuple(len(g) for g in members),
                    within_ss_scaled=within,
                    raw_observation_count=len(rows),
                    deadline=deadline,
                    kernel_spec=kernel_spec,
                    fit_policy=fit_policy,
                )
                state = dump_bo_mixed_surrogate(model)
            else:
                model = fit_bo_surrogate(
                    x,
                    y,
                    policy,
                    search,
                    group_member_indices=members
                    if fit.observation_policy.mode == "exact_replicates"
                    else None,
                    deadline=deadline,
                    kernel_spec=kernel_spec,
                    fit_policy=fit_policy,
                )
                state = dump_bo_surrogate(
                    model,
                    training_targets_scaled=targets,
                    affine_factor_domains=_kernel_domains(design),
                )
            evaluations += model.optimizer["evaluations"]
            states[key] = state
            metadata.append({"response_id": key, "model": model.metadata()})
            warnings.extend(model.warning_codes)
    snapshot = {
        "schema_version": 3,
        "policy": POLICY,
        "design_domain": design.payload(),
        "calculation_request": payload,
        "inner_model_kind": "mixed" if mixed else "numeric",
        "response_states": states,
        "response_models": metadata,
        "warnings": list(dict.fromkeys(warnings)),
        "fit_evaluations": evaluations,
        "fit_elapsed_ms": (time.perf_counter() - started) * 1000,
    }
    restored = restore_mixture_planning_model(snapshot, _allow_unfinished=True)
    snapshot["incumbent"] = _incumbent(restored)
    return snapshot


@dataclass(frozen=True)
class MixturePlanningModel:
    design: BoMixtureDesign
    objective: Any
    fit: MixedFitOptions
    observations: list[dict[str, Any]]
    models: dict[str, Any]


def _incumbent(model: MixturePlanningModel) -> dict[str, Any]:
    goals = [r.calculation_goal() for r in model.objective.responses]
    values = []
    cache = {}
    for row in model.observations:
        point = model.design.canonical(row["actual_coordinates"])[1]
        if point not in cache:
            cache[point] = evaluate_mixed_surrogate_desirability(
                model.models, goals, point
            ).moments.mean
        value = cache[point]
        values.append(value)
    best = max(range(len(values)), key=values.__getitem__)
    observed = [composite_desirability(r["response_values"], goals) for r in model.observations]
    return {
        "policy": "max_posterior_expected_desirability_at_observed_coordinates_v1",
        "latent_incumbent_value": values[best],
        "latent_incumbent_trial_id": model.observations[best]["trial_id"],
        "best_observed_desirability": max(observed),
    }


def restore_mixture_planning_model(
    snapshot: dict[str, Any], *, _allow_unfinished: bool = False
) -> MixturePlanningModel:
    import numpy as np

    base = {
        "schema_version",
        "policy",
        "design_domain",
        "calculation_request",
        "inner_model_kind",
        "response_states",
        "response_models",
        "warnings",
        "fit_evaluations",
        "fit_elapsed_ms",
    }
    if (
        type(snapshot) is not dict
        or set(snapshot) != (base if _allow_unfinished else base | {"incumbent"})
        or type(snapshot["schema_version"]) is not int
        or snapshot["schema_version"] != 3
        or snapshot["policy"] != POLICY
    ):
        raise _error()
    try:
        design, objective, fit, rows = _parsed(snapshot["calculation_request"])
        mixed = any(isinstance(f, BoCategoricalFactorDomain) for f in design.process_factors)
        if (
            snapshot["design_domain"] != design.payload()
            or snapshot["inner_model_kind"] != ("mixed" if mixed else "numeric")
            or set(snapshot["response_states"]) != {r.response_id for r in objective.responses}
        ):
            raise _error()
        models: dict[str, Any] = {}
        warnings: list[str] = []
        evaluations = 0
        specifications = {r.response_id: r for r in fit.response_models}
        for goal, record in zip(objective.responses, snapshot["response_models"], strict=True):
            key = goal.response_id
            x, _, members, targets, within, mean, scale = _training(design, fit, rows, key)
            state = snapshot["response_states"][key]
            model = (
                load_bo_mixed_surrogate(
                    state,
                    expected_factor_domains=_kernel_domains(design),
                    expected_training_targets_scaled=targets,
                    expected_within_ss_scaled=within,
                )
                if mixed
                else load_bo_surrogate(
                    state,
                    expected_training_targets_scaled=targets,
                    affine_factor_domains=_kernel_domains(design),
                )
            )
            specification = specifications[key]
            if (
                not np.array_equal(model.x_train, x[[g[0] for g in members]])
                or model.normalization_mean != mean
                or model.normalization_scale != scale
                or model.direction_multiplier != 1
                or model.group_counts != tuple(len(g) for g in members)
                or model.raw_observation_count != len(rows)
                or model.kernel_spec != BoKernelSpec(specification.kernel.kind)
                or model.policy != BoSurrogatePolicy(**specification.surrogate.model_dump())
                or model.jitter != fit.search.jitter
                or model.optimizer["seed"] != fit.search.random_seed
                or model.optimizer["restarts"] != fit.search.hyperparameter_restart_count
                or model.optimizer["max_iterations"] != fit.search.model_max_iterations
                or model.fit_diagnostics is None
                or model.fit_diagnostics["deterministic_start_count"]
                != fit.fit_policy.deterministic_start_count
                or model.optimizer["max_evaluations"]
                != fit.search.model_max_evaluations - evaluations
            ):
                raise _error()
            metadata = {**model.metadata(), "package_versions": state["fit"]["package_versions"]}
            if record != {"response_id": key, "model": metadata}:
                raise _error()
            models[key] = model
            evaluations += model.optimizer["evaluations"]
            warnings.extend(model.warning_codes)
        if (
            snapshot["warnings"] != list(dict.fromkeys(warnings))
            or snapshot["fit_evaluations"] != evaluations
            or evaluations > fit.search.model_max_evaluations
            or type(snapshot["fit_elapsed_ms"]) not in {float, int}
            or not math.isfinite(snapshot["fit_elapsed_ms"])
            or snapshot["fit_elapsed_ms"] < 0
        ):
            raise _error()
        result = MixturePlanningModel(design, objective, fit, rows, models)
        if "incumbent" in snapshot:
            from app.statistics.bo_planning_model import _same_incumbent

            if not _same_incumbent(snapshot["incumbent"], _incumbent(result)):
                raise _error()
        return result
    except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
        raise _error() from None


def evaluate_mixture_planning_points(
    snapshot: dict[str, Any],
    points: list[dict[str, Any]],
    *,
    excluded_actual: list[dict[str, Any]] | None = None,
    compute_acquisition: bool = True,
    time_budget_ms: int = 60000,
    max_moment_evaluations: int = 4096,
) -> list[dict[str, Any]]:
    from app.api.v1.schemas.bo_mixture import MixtureEvaluatedRow
    from app.statistics.bo_planning_model import PlanningEvaluationBudget
    from app.storage.bo_planning import planning_sha

    budget = PlanningEvaluationBudget(
        time.perf_counter() + time_budget_ms / 1000, max_moment_evaluations
    )
    model = restore_mixture_planning_model(snapshot)
    budget.consume(
        len(
            {
                tuple(r["actual_coordinates"][k] for k in model.design.keys)
                for r in model.observations
            }
        )
    )
    if (
        type(points) is not list
        or not 1 <= len(points) <= 10000
        or type(compute_acquisition) is not bool
    ):
        raise _error("bayesian_mixture_planning_input_invalid")
    excluded = excluded_actual or [row["actual_coordinates"] for row in model.observations]
    goals = [r.calculation_goal() for r in model.objective.responses]
    incumbent = snapshot["incumbent"]["latent_incumbent_value"]
    result, seen = [], set()
    for index, original in enumerate(points):
        budget.consume(1)
        actual, encoded = model.design.canonical(original)
        identity = tuple(actual[k] for k in model.design.keys)
        if identity in seen:
            raise _error("bayesian_candidate_duplicate_row")
        seen.add(identity)
        nearest = min((model.design.distance(actual, old) for old in excluded), default=None)
        feasible = mixed_constraints_satisfied(actual, model.design.constraints)
        novel = nearest is None or nearest > model.fit.search.duplicate_tolerance
        prediction = evaluate_mixed_surrogate_desirability(model.models, goals, encoded)
        acquisition = (
            {
                "kind": "desirability_beta_expected_improvement",
                **asdict(
                    beta_expected_improvement(
                        prediction.moments.mean,
                        prediction.moments.variance,
                        incumbent,
                        xi=model.fit.xi_desirability,
                    )
                ),
                "xi_desirability": model.fit.xi_desirability,
            }
            if compute_acquisition
            else None
        )
        result.append(
            {
                "schema_version": 4,
                "row_id": planning_sha(actual),
                "source_row_number": index + 1,
                "input_coordinates": dict(original),
                "actual_coordinates": actual,
                "encoded_coordinates": dict(zip(model.design.keys, encoded, strict=True)),
                "coordinate_encoding": ENCODING,
                "distance_policy": METRIC,
                "constraints_satisfied": feasible,
                "nearest_existing_distance": nearest,
                "novel": novel,
                "eligible": feasible and novel,
                "response_predictions": [asdict(r) for r in prediction.responses],
                "desirability_moments": asdict(prediction.moments),
                "acquisition": acquisition,
                "prediction_source": "completed_observations_base_posterior",
            }
        )
    return [MixtureEvaluatedRow.model_validate(row).model_dump(mode="json") for row in result]


def mixture_profile_path(
    snapshot: dict[str, Any], holds: dict[str, Any], axis_id: str, *, count: int = 21
) -> dict[str, Any]:
    model = restore_mixture_planning_model(snapshot)
    return model.design.profile(holds, axis_id, count=count)


def calculate_mixture_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    model = restore_mixture_planning_model(payload["snapshot"])
    source = payload["source"]
    generation = None
    if source["kind"] == "seeded_uniform":
        deadline = time.perf_counter() + payload["time_budget_ms"] / 1000

        def check() -> None:
            if time.perf_counter() >= deadline:
                raise _error("bayesian_optimization_time_budget_exhausted")

        generated = model.design.sample(
            seed=source["seed"], count=source["count"], check_budget=check
        )
        points, generation = generated["points"], generated["generation"]
    elif source["kind"] == "explicit_rows":
        points = source["points"]
    else:
        raise _error("bayesian_candidate_input_invalid")
    items = evaluate_mixture_planning_points(
        payload["snapshot"],
        points,
        excluded_actual=payload["excluded_actual"],
        time_budget_ms=payload["time_budget_ms"],
        max_moment_evaluations=payload["max_moment_evaluations"],
    )
    return {"generation": generation, "items": items}


def calculate_mixture_selection(payload: dict[str, Any]) -> dict[str, Any]:
    from app.api.v1.schemas.bo_mixture import MixtureSelectionCreateRequest

    config = MixtureSelectionCreateRequest.model_validate(payload["config"])
    deadline = time.perf_counter() + config.time_budget_ms / 1000
    model = restore_mixture_planning_model(payload["snapshot"])
    rows = payload["rows"]
    if type(rows) is not list or not 1 <= len(rows) <= 10000:
        raise _error("bayesian_planning_selection_invalid")
    if config.policy == "manual_mixture_base_posterior_v1":
        by_id = {r["row_id"]: r for r in rows}
        try:
            chosen = [by_id[key] for key in config.row_ids]
        except KeyError:
            raise _error("bayesian_planning_selection_invalid") from None
    else:
        available = [r for r in rows if r["eligible"]]
        chosen = []
        for _ in range(config.batch_size):
            if not available:
                raise _error("bayesian_augmentation_insufficient_candidates")
            prior = payload["excluded_actual"] + [r["actual_coordinates"] for r in chosen]

            def score(row: dict[str, Any], prior: list[Any] = prior) -> tuple[float, str]:
                if time.perf_counter() >= deadline:
                    raise _error("bayesian_optimization_time_budget_exhausted")
                return (
                    min(
                        (model.design.distance(row["actual_coordinates"], p) for p in prior),
                        default=0.0,
                    ),
                    row["row_id"],
                )

            next_row = max(available, key=score)
            chosen.append(next_row)
            available.remove(next_row)
    originals = [r["input_coordinates"] for r in chosen]
    evaluated = evaluate_mixture_planning_points(
        payload["snapshot"],
        originals,
        excluded_actual=payload["excluded_actual"],
        time_budget_ms=config.time_budget_ms,
        max_moment_evaluations=config.max_moment_evaluations,
    )
    result: list[dict[str, Any]] = []
    for rank, row in enumerate(evaluated, 1):
        if not row["eligible"]:
            raise _error("bayesian_planning_selection_ineligible")
        nearest = min(
            (
                model.design.distance(row["actual_coordinates"], old["actual_coordinates"])
                for old in result
            ),
            default=None,
        )
        if nearest is not None and nearest < config.min_batch_distance:
            raise _error("bayesian_planning_selection_distance")
        result.append({**row, "rank": rank, "nearest_selected_distance": nearest})
    return {
        "schema_version": 13,
        "selection_policy": config.policy,
        "model_refit": False,
        "distance_policy": METRIC,
        "joint_improvement_claimed": False,
        "items": result,
    }
