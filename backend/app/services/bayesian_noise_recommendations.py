"""Versioned noise-aware recommendations with immutable legacy readers."""

from __future__ import annotations

import hashlib
import json
import math
import multiprocessing
from multiprocessing.connection import Connection
from typing import Any, cast
from uuid import UUID, uuid4

from pydantic import ValidationError

from app.api.v1.schemas.bayesian import (
    BayesianRecommendationCurrentTrialResponse,
    BayesianTrialResponse,
)
from app.api.v1.schemas.bayesian_noise import (
    BayesianNoiseBatchCreateRequest,
    BayesianNoiseBatchItem,
    BayesianNoiseBatchResponse,
    BayesianNoiseCalculation,
    BayesianNoiseSingleCreateRequest,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    canonical_json_bytes,
    runtime_build_provenance,
    utc_now,
)
from app.storage.bayesian_studies import (
    BayesianRecommendationBatchItemRecord,
    BayesianRecommendationBatchRecord,
    BayesianStorageConflict,
    BayesianTrialRecord,
    insert_bayesian_recommendation_batch_bundle,
    list_bayesian_recommendation_batch_item_records,
)

METHOD = "doe.bayesian_optimization"
POLICY = "greedy_mc_joint_latent_improvement_v2"
VERSION = "0.7.0"
MAX_WORKER_BYTES = 4 * 1024 * 1024


def _error(code: str = "bayesian_optimization_artifact_mismatch") -> ApiError:
    return ApiError(
        code=code,
        message="The Bayesian recommendation could not be safely created or restored.",
        status_code=409,
    )


def _json(value: Any) -> str:
    return canonical_json_bytes(value).decode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def create_noise_single(
    settings: Settings, study_id: UUID, body: BayesianNoiseSingleCreateRequest
) -> BayesianNoiseBatchResponse:
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    search = body.search.model_dump(mode="json")
    xi = search.pop("xi")
    for old, new in (
        ("candidate_count", "candidate_count_per_step"),
        ("local_start_count", "local_start_count_per_step"),
        ("max_iterations", "max_iterations_per_step"),
        ("max_evaluations", "max_evaluations_total"),
    ):
        search[new] = search.pop(old)
    search["batch_policy"] = POLICY
    goal = study.objective.goal_type or study.objective.direction
    request = BayesianNoiseBatchCreateRequest.model_validate(
        {
            **body.model_dump(mode="json", exclude={"search"}),
            "search": search,
            "acquisition": {
                "kind": "expected_target_improvement"
                if goal == "match_target"
                else "expected_improvement",
                "exploration_profile": "custom",
                "xi_standardized": xi,
            },
        }
    )
    return create_noise_batch(settings, study_id, request)


def worker_payload(
    study: Any, body: BayesianNoiseBatchCreateRequest, completed: list[Any]
) -> dict[str, Any]:
    return {
        "factors": [
            {
                "factor_id": f.factor_id,
                "low": f.low,
                "high": f.high,
                "domain_kind": f.domain_kind,
                "step": f.step,
            }
            for f in study.factors
        ],
        "constraints": [c.model_dump(mode="json") for c in study.constraints],
        "observations": [
            {
                "trial_id": str(t.trial_id),
                "actual_coordinates": t.actual_coordinates,
                "normalized_coordinates": t.normalized_coordinates,
                "objective_value": t.objective_value,
            }
            for t in completed
        ],
        "excluded_normalized": [
            [t.normalized_coordinates[f.factor_id] for f in study.factors] for t in study.trials
        ],
        "objective": {
            "goal_type": study.objective.goal_type or study.objective.direction,
            "target_value": study.objective.target_value,
        },
        "batch_size": body.batch_size,
        "acquisition": body.acquisition.model_dump(mode="json"),
        "search": body.search.model_dump(mode="json", exclude={"total_trial_budget"}),
        "surrogate": body.surrogate.model_dump(mode="json"),
        "observation_policy": body.observation_policy.model_dump(mode="json"),
        "batch_options": body.batch_options.model_dump(mode="json"),
    }


def create_noise_batch(
    settings: Settings, study_id: UUID, body: BayesianNoiseBatchCreateRequest
) -> BayesianNoiseBatchResponse:
    from app.services.bayesian_studies import get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    history = study.observation_history
    if study.status != "active":
        raise _error("bayesian_study_closed")
    if (
        str(body.expected_history_revision_id) != str(history.history_revision_id)
        or body.expected_history_sha256 != history.observation_history_sha256
    ):
        raise _error("bayesian_optimization_history_stale")
    if any(t.state == "pending" and t.origin == "initial_design" for t in study.trials):
        raise _error("bayesian_optimization_history_incomplete")
    if any(t.state == "pending" for t in study.trials):
        raise _error("bayesian_optimization_pending_recommendation_exists")
    completed = [t for t in study.trials if t.state == "completed"]
    if not study.recommendation_minimum_completed_observations <= len(completed) <= 200:
        raise _error("bayesian_optimization_history_incomplete")
    goal = study.objective.goal_type or study.objective.direction
    if body.acquisition.kind != (
        "expected_target_improvement" if goal == "match_target" else "expected_improvement"
    ):
        raise _error("bayesian_optimization_acquisition_goal_mismatch")
    if len(study.trials) + body.batch_size > min(body.search.total_trial_budget, 200):
        raise _error("bayesian_optimization_batch_budget_exceeded")
    payload = worker_payload(study, body, completed)
    try:
        calculated = BayesianNoiseCalculation.model_validate(
            _run_worker(payload, timeout_ms=body.search.time_budget_ms + 20_000)
        )
    except ValidationError as exc:
        raise _error() from exc
    validate_calculation(calculated, payload, body)
    batch_id = uuid4()
    created_at = utc_now()
    trials: list[BayesianTrialRecord] = []
    items: list[BayesianNoiseBatchItem] = []
    for item in calculated.items:
        trial_id = uuid4()
        number = len(study.trials) + item.rank
        coordinates_hash = _sha(
            {
                "definition_sha256": study.definition_sha256,
                "trial_number": number,
                "origin": "recommendation",
                "actual_coordinates": item.actual_coordinates,
                "normalized_coordinates": item.normalized_coordinates,
            }
        )
        trial = BayesianTrialResponse(
            trial_id=trial_id,
            study_version_id=study.study_version_id,
            trial_number=number,
            origin="recommendation",
            state="pending",
            actual_coordinates=item.actual_coordinates,
            normalized_coordinates=item.normalized_coordinates,
            coordinates_sha256=coordinates_hash,
            objective_value=None,
            created_at=created_at,
            closed_at=None,
        )
        trials.append(
            BayesianTrialRecord(
                trial_id=str(trial_id),
                study_version_id=str(study.study_version_id),
                trial_number=number,
                origin="recommendation",
                state="pending",
                actual_coordinates_json=_json(item.actual_coordinates),
                normalized_coordinates_json=_json(item.normalized_coordinates),
                coordinates_sha256=coordinates_hash,
                objective_value=None,
                created_at=created_at,
                closed_at=None,
            )
        )
        items.append(
            BayesianNoiseBatchItem(
                **item.model_dump(),
                item_id=uuid4(),
                batch_id=batch_id,
                trial=trial,
                current_trial=BayesianRecommendationCurrentTrialResponse(
                    trial_id=trial_id, state="pending", objective_value=None, closed_at=None
                ),
            )
        )
    identity = {
        "study_id": str(study.study_id),
        "study_version_id": str(study.study_version_id),
        "source_history_revision_id": str(history.history_revision_id),
        "source_observation_history_sha256": history.observation_history_sha256,
        "definition_sha256": study.definition_sha256,
    }
    versions = {
        "method_id": METHOD,
        "method_version": VERSION,
        "config_schema_version": 2,
        "result_schema_version": 2,
        "model_schema_version": 3,
        "item_schema_version": 2,
    }
    config = {"schema_version": 2, **identity, "request": body.model_dump(mode="json")}
    config_json = _json(config)
    runtime = runtime_build_provenance(settings)
    provenance = {
        **identity,
        **versions,
        "batch_id": str(batch_id),
        "app_version": APP_VERSION,
        "python_version": runtime["python_version"],
        "platform": runtime["platform"],
        "build_commit": runtime["build_commit"],
        "package_versions": calculated.shared_model.package_versions,
        "created_at": created_at,
    }
    response = BayesianNoiseBatchResponse.model_validate(
        {
            **calculated.model_dump(mode="json", exclude={"schema_version", "items"}),
            **identity,
            **versions,
            "batch_id": str(batch_id),
            "execution_mode": body.execution_mode,
            "acquisition": body.acquisition.model_dump(mode="json"),
            "items": [i.model_dump(mode="json") for i in items],
            "config_sha256": _sha(config),
            "result_sha256": "0" * 64,
            "provenance": provenance,
            "created_at": created_at,
            "requested_total_trial_budget": body.search.total_trial_budget,
        }
    )
    immutable = response.model_dump(mode="json", exclude={"is_latest", "batch_state"})
    response = response.model_copy(update={"result_sha256": _sha(immutable), "is_latest": True})
    result_json = _json(response.model_dump(mode="json", exclude={"is_latest", "batch_state"}))
    record = BayesianRecommendationBatchRecord(
        batch_id=str(batch_id),
        study_version_id=str(study.study_version_id),
        source_history_revision_id=str(history.history_revision_id),
        source_observation_history_sha256=history.observation_history_sha256,
        method_id=METHOD,
        method_version=VERSION,
        config_schema_version=2,
        result_schema_version=2,
        model_schema_version=3,
        item_schema_version=2,
        batch_size=body.batch_size,
        batch_policy=POLICY,
        config_json=config_json,
        config_sha256=_sha(config),
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode()).hexdigest(),
        created_at=created_at,
        app_version=APP_VERSION,
    )
    records = [
        BayesianRecommendationBatchItemRecord(
            item_id=str(i.item_id),
            batch_id=str(batch_id),
            trial_id=str(i.trial.trial_id),
            rank=i.rank,
            item_schema_version=2,
            item_result_json=_json(i.model_dump(mode="json")),
            item_result_sha256=_sha(i.model_dump(mode="json")),
            created_at=created_at,
        )
        for i in items
    ]
    try:
        insert_bayesian_recommendation_batch_bundle(
            settings.workspace_root,
            trials=trials,
            batch=record,
            items=records,
            expected_history_revision_id=str(history.history_revision_id),
            expected_history_sha256=history.observation_history_sha256,
            total_trial_budget=body.search.total_trial_budget,
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    return response


def validate_calculation(
    result: BayesianNoiseCalculation, payload: dict[str, Any], body: BayesianNoiseBatchCreateRequest
) -> None:
    from app.statistics.bo_observation_groups import (
        BoObservationGroupsError,
        prepare_bo_observation_view,
    )

    try:
        view = prepare_bo_observation_view(
            payload["observations"], payload["factors"], **body.observation_policy.model_dump()
        )
    except BoObservationGroupsError as exc:
        raise _error() from exc
    model = result.shared_model
    goal = payload["objective"]["goal_type"]
    direction = -1.0 if goal == "minimize" else 1.0
    if (
        result.batch_size != body.batch_size
        or len(result.items) != body.batch_size
        or result.observation_view.model_dump(mode="json") != view.provenance()
        or model.raw_observation_count != view.raw_observation_count
        or model.effective_training_count != view.effective_training_count
        or model.training_group_counts != view.training_counts.tolist()
        or model.normalization.mean != direction * view.normalization_mean
        or model.normalization.scale != view.normalization_scale
        or model.normalization.direction_multiplier != direction
        or model.objective_goal_type != goal
        or model.noise.mode != body.surrogate.noise_mode
        or model.jitter != body.search.jitter
        or model.optimizer.seed != body.search.random_seed
        or model.optimizer.restarts != body.search.hyperparameter_restart_count
        or model.optimizer.max_iterations != body.search.model_max_iterations
        or model.optimizer.max_evaluations != body.search.model_max_evaluations
        or result.search_budget.max_evaluations_total != body.search.max_evaluations_total
        or result.search_budget.time_budget_ms != body.search.time_budget_ms
        or result.search_budget.min_batch_distance_normalized
        != body.batch_options.min_batch_distance_normalized
        or len(model.signal_kernel.length_scales) != len(payload["factors"])
        or model.signal_kernel.amplitude <= 0
        or any(value <= 0 for value in model.signal_kernel.length_scales)
        or result.search_budget.evaluations_consumed > body.search.max_evaluations_total
        or len(result.search_budget.searches) != body.batch_size
    ):
        raise _error()
    if body.surrogate.noise_mode == "estimate":
        bounds = (
            body.surrogate.lower_noise_variance_scaled,
            body.surrogate.upper_noise_variance_scaled,
        )
        if (
            model.noise.bounds_scaled != bounds
            or model.noise.initial_variance_scaled != body.surrogate.initial_noise_variance_scaled
            or not bounds[0] * (1 - 1e-12)
            <= model.noise.fitted_variance_scaled
            <= bounds[1] * (1 + 1e-12)
            or model.noise.fixed_sd_raw is not None
        ):
            raise _error()
    else:
        expected_noise = (
            0.0
            if body.surrogate.noise_mode == "near_noiseless"
            else (cast(float, body.surrogate.fixed_noise_sd) / model.normalization.scale) ** 2
        )
        if (
            model.noise.bounds_scaled is not None
            or model.noise.fixed_sd_raw != body.surrogate.fixed_noise_sd
            or not math.isclose(
                model.noise.fitted_variance_scaled, expected_noise, rel_tol=1e-12, abs_tol=0
            )
        ):
            raise _error()
    if not math.isclose(
        model.observation_noise_sd_raw**2,
        model.noise.fitted_variance_scaled * model.normalization.scale**2,
        rel_tol=1e-10,
        abs_tol=1e-14,
    ):
        raise _error()
    ids = {o["trial_id"] for o in payload["observations"]}
    if (
        str(result.incumbent.best_observed_trial_id) not in ids
        or str(result.incumbent.latent_incumbent_trial_id) not in ids
    ):
        raise _error()
    observations_by_id = {o["trial_id"]: o for o in payload["observations"]}
    best = observations_by_id[str(result.incumbent.best_observed_trial_id)]
    # The core fits canonical actual-to-normalized coordinates, which can differ
    # by one ULP from an earlier stored normalized-to-actual round trip.
    latent_index = view.trial_ids.index(str(result.incumbent.latent_incumbent_trial_id))
    factor_ids = [f["factor_id"] for f in payload["factors"]]
    expected_best = (
        min(view.raw_y, key=lambda y: abs(y - payload["objective"]["target_value"]))
        if goal == "match_target"
        else (min(view.raw_y) if goal == "minimize" else max(view.raw_y))
    )
    expected_target = (
        (payload["objective"]["target_value"] - model.normalization.mean)
        / model.normalization.scale
        if goal == "match_target"
        else None
    )
    if (
        result.incumbent.best_observed_objective != best["objective_value"]
        or result.incumbent.best_observed_objective != expected_best
        or result.incumbent.latent_incumbent_coordinates_normalized
        != view.raw_x[latent_index].tolist()
        or model.target_scaled != expected_target
        or result.incumbent.target_scaled != expected_target
        or result.incumbent.incumbent_kind
        != ("latent_target_distance" if goal == "match_target" else "directional_latent_mean")
        or result.incumbent.xi_standardized != body.acquisition.xi_standardized
        or not math.isclose(
            result.incumbent.xi_raw,
            body.acquisition.xi_standardized * model.normalization.scale,
            rel_tol=1e-12,
            abs_tol=0,
        )
    ):
        raise _error()
    seen = list(payload["excluded_normalized"])
    selected: list[list[float]] = []
    for rank, item in enumerate(result.items, 1):
        if (
            item.rank != rank
            or set(item.actual_coordinates) != set(factor_ids)
            or set(item.normalized_coordinates) != set(factor_ids)
            or item.acquisition_kind != body.acquisition.kind
            or item.planning.conditioned_on_selected_ranks != list(range(1, rank))
            or item.planning.batch_step != rank - 1
            or item.planning.root_seed != body.search.random_seed
            or item.planning.requested_sample_count != body.batch_options.posterior_sample_count
            or item.planning.effective_sample_count
            != (0 if rank == 1 else body.batch_options.posterior_sample_count)
            or not math.isclose(
                item.acquisition_value_raw,
                item.acquisition_value_standardized * model.normalization.scale,
                rel_tol=1e-12,
                abs_tol=0,
            )
            or not math.isclose(
                item.predictive_standard_deviation**2 - item.latent_standard_deviation**2,
                model.observation_noise_sd_raw**2,
                rel_tol=1e-8,
                abs_tol=1e-12,
            )
        ):
            raise _error()
        for f in payload["factors"]:
            actual = item.actual_coordinates[f["factor_id"]]
            normalized = item.normalized_coordinates[f["factor_id"]]
            if (
                not f["low"] <= actual <= f["high"]
                or not 0 <= normalized <= 1
                or not math.isclose(
                    actual,
                    f["low"] + normalized * (f["high"] - f["low"]),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            ):
                raise _error()
            if f["domain_kind"] == "discrete_numeric":
                level = (actual - f["low"]) / f["step"]
                if not math.isclose(level, round(level), abs_tol=1e-8):
                    raise _error()
        point = [item.normalized_coordinates[f] for f in factor_ids]
        nearest_existing = min(
            (math.dist(point, old) for old in payload["excluded_normalized"]), default=None
        )
        nearest_selected = min((math.dist(point, old) for old in selected), default=None)
        if not _optional_close(
            item.nearest_existing_distance, nearest_existing
        ) or not _optional_close(item.nearest_selected_distance, nearest_selected):
            raise _error()
        if any(math.dist(point, old) <= body.search.duplicate_tolerance for old in seen):
            raise _error()
        if any(
            math.dist(point, old) < body.batch_options.min_batch_distance_normalized
            for old in selected
        ):
            raise _error()
        selected.append(point)
        seen.append(point)
        for constraint in payload["constraints"]:
            lhs = sum(
                term["coefficient"] * item.actual_coordinates[term["factor_id"]]
                for term in constraint["terms"]
            )
            bound = constraint["bound"]
            if (constraint["relation"] == "less_than_or_equal" and lhs > bound + 1e-8) or (
                constraint["relation"] == "greater_than_or_equal" and lhs < bound - 1e-8
            ):
                raise _error()


def _optional_close(actual: float | None, expected: float | None) -> bool:
    if actual is None or expected is None:
        return actual is expected
    return math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12)


def validate_noise_record(
    settings: Settings,
    *,
    version: Any,
    factors: list[Any],
    objective: Any,
    constraints: list[Any],
    trials: list[Any],
    history: Any,
    record: BayesianRecommendationBatchRecord,
) -> BayesianNoiseBatchResponse:
    try:
        if (
            hashlib.sha256(record.config_json.encode()).hexdigest() != record.config_sha256
            or hashlib.sha256(record.result_json.encode()).hexdigest() != record.result_sha256
        ):
            raise _error()
        config = json.loads(record.config_json)
        body = BayesianNoiseBatchCreateRequest.model_validate(config["request"])
        response = BayesianNoiseBatchResponse.model_validate_json(record.result_json)
        immutable = response.model_dump(mode="json", exclude={"is_latest", "batch_state"})
        immutable["result_sha256"] = "0" * 64
        identity = {
            "study_id": version.study_id,
            "study_version_id": version.study_version_id,
            "definition_sha256": version.definition_sha256,
            "source_history_revision_id": record.source_history_revision_id,
            "source_observation_history_sha256": record.source_observation_history_sha256,
        }
        if (
            config != {"schema_version": 2, **identity, "request": body.model_dump(mode="json")}
            or _sha(immutable) != response.result_sha256
            or record.method_id != METHOD
            or record.method_version != VERSION
            or (
                record.config_schema_version,
                record.result_schema_version,
                record.model_schema_version,
                record.item_schema_version,
            )
            != (2, 2, 3, 2)
            or record.batch_policy != POLICY
            or record.batch_id != str(response.batch_id)
            or record.batch_size != response.batch_size
            or response.batch_size != body.batch_size
            or response.execution_mode != body.execution_mode
            or response.acquisition != body.acquisition
            or response.config_sha256 != record.config_sha256
            or response.created_at != record.created_at
            or response.provenance.created_at != record.created_at
            or str(response.provenance.batch_id) != record.batch_id
            or response.provenance.package_versions != response.shared_model.package_versions
            or response.provenance.app_version != record.app_version
            or response.requested_total_trial_budget != body.search.total_trial_budget
            or history is None
            or history.study_version_id != version.study_version_id
            or history.observation_history_sha256 != record.source_observation_history_sha256
            or str(body.expected_history_revision_id) != record.source_history_revision_id
            or body.expected_history_sha256 != record.source_observation_history_sha256
        ):
            raise _error()
        for key, value in identity.items():
            if (
                str(getattr(response, key)) != value
                or str(getattr(response.provenance, key)) != value
            ):
                raise _error()
        source_ids = json.loads(history.completed_trial_ids_json)
        trial_map = {t.trial_id: t for t in trials}
        source = [trial_map[key] for key in source_ids]
        observations = [
            {
                "trial_id": t.trial_id,
                "actual_coordinates": json.loads(t.actual_coordinates_json),
                "normalized_coordinates": json.loads(t.normalized_coordinates_json),
                "objective_value": t.objective_value,
            }
            for t in source
        ]
        earliest_number = min(i.trial.trial_number for i in response.items)
        payload = {
            "observations": observations,
            "factors": [
                {
                    "factor_id": f.factor_id,
                    "low": f.low,
                    "high": f.high,
                    "domain_kind": f.domain_kind,
                    "step": f.step,
                }
                for f in factors
            ],
            "objective": {
                "goal_type": objective.goal_type or objective.direction,
                "target_value": objective.target_value,
            },
            "constraints": [c.model_dump(mode="json") for c in constraints],
            "excluded_normalized": [
                [json.loads(t.normalized_coordinates_json)[f.factor_id] for f in factors]
                for t in trials
                if t.trial_number < earliest_number
            ],
        }
        calculated = BayesianNoiseCalculation.model_validate(
            {
                "schema_version": 2,
                **response.model_dump(
                    mode="json",
                    include={
                        "batch_policy",
                        "batch_size",
                        "shared_model",
                        "incumbent",
                        "observation_view",
                        "search_budget",
                        "warnings",
                        "limitations",
                    },
                ),
                "items": [
                    i.model_dump(
                        mode="json", exclude={"item_id", "batch_id", "trial", "current_trial"}
                    )
                    for i in response.items
                ],
            }
        )
        validate_calculation(calculated, payload, body)
        records = list_bayesian_recommendation_batch_item_records(
            settings.workspace_root, record.batch_id
        )
        if len(records) != len(response.items):
            raise _error()
        for stored, item in zip(records, response.items, strict=True):
            trial = trial_map.get(stored.trial_id)
            if (
                trial is None
                or trial.origin != "recommendation"
                or stored.item_schema_version != 2
                or stored.rank != item.rank
                or stored.item_id != str(item.item_id)
                or stored.batch_id != str(item.batch_id)
                or stored.batch_id != record.batch_id
                or stored.item_result_json != _json(item.model_dump(mode="json"))
                or stored.item_result_sha256 != _sha(item.model_dump(mode="json"))
                or trial.trial_id != str(item.trial.trial_id)
                or item.trial.state != "pending"
                or item.trial.objective_value is not None
                or item.trial.closed_at is not None
                or item.trial.trial_number != trial.trial_number
                or item.trial.created_at != trial.created_at
                or str(item.trial.study_version_id) != trial.study_version_id
                or item.trial.actual_coordinates != item.actual_coordinates
                or item.trial.normalized_coordinates != item.normalized_coordinates
                or item.current_trial.trial_id != item.trial.trial_id
                or item.current_trial.state != "pending"
                or item.current_trial.objective_value is not None
                or item.current_trial.closed_at is not None
                or trial.coordinates_sha256 != item.trial.coordinates_sha256
                or item.actual_coordinates != json.loads(trial.actual_coordinates_json)
                or item.normalized_coordinates != json.loads(trial.normalized_coordinates_json)
            ):
                raise _error()
        return response
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise _error() from exc


def _worker_entry(output: Connection, payload: dict[str, Any]) -> None:
    from threadpoolctl import threadpool_limits  # type: ignore[import-untyped]

    from app.statistics.bayesian_optimization import BayesianOptimizationError
    from app.statistics.bo_recommendation_core import calculate_noise_aware_batch

    try:
        with threadpool_limits(limits=1):
            result = calculate_noise_aware_batch(payload)
        message = {"status": "ok", "result": result}
    except BayesianOptimizationError as exc:
        message = {"status": "error", "code": exc.code}
    except Exception:
        message = {"status": "error", "code": "bayesian_optimization_surrogate_fit_failed"}
    try:
        data = canonical_json_bytes(message)
        if len(data) > MAX_WORKER_BYTES:
            data = canonical_json_bytes(
                {"status": "error", "code": "bayesian_optimization_artifact_mismatch"}
            )
        output.send_bytes(data)
    finally:
        output.close()


def _run_worker(payload: dict[str, Any], *, timeout_ms: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_worker_entry, args=(send, payload))
    try:
        process.start()
        send.close()
        if not receive.poll(timeout_ms / 1000):
            raise _error("bayesian_optimization_batch_incomplete")
        try:
            message = json.loads(receive.recv_bytes(MAX_WORKER_BYTES))
        except (EOFError, OSError, ValueError) as exc:
            raise _error("bayesian_optimization_surrogate_fit_failed") from exc
        process.join(timeout=5)
        if message.get("status") != "ok":
            code = message.get("code", "")
            allowed = {
                "bayesian_optimization_batch_incomplete",
                "bayesian_optimization_budget_exhausted",
                "bayesian_optimization_no_feasible_candidate",
                "bayesian_optimization_history_incomplete",
                "bayesian_optimization_duplicate_candidate",
                "bayesian_optimization_surrogate_fit_failed",
                "bayesian_optimization_artifact_mismatch",
                "bayesian_optimization_invalid_options",
                "bayesian_unique_conditions_insufficient",
                "bayesian_observation_limit_reached",
                "bayesian_nearby_options_invalid",
                "bayesian_observation_statistics_nonfinite",
                "bayesian_surrogate_noise_invalid",
                "bayesian_surrogate_covariance_invalid",
                "bayesian_optimization_time_budget_exhausted",
                "bayesian_optimization_acquisition_goal_mismatch",
            }
            raise _error(code if code in allowed else "bayesian_optimization_surrogate_fit_failed")
        if not isinstance(message.get("result"), dict):
            raise _error()
        return message["result"]
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)
            process.close()
