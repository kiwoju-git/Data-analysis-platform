from __future__ import annotations

import hashlib
import json
import multiprocessing
import queue
from typing import Any, Final, Literal, cast
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.analyses.registry import METHOD_VERSIONS
from app.api.v1.schemas.bayesian import (
    MAX_BAYESIAN_TRIALS,
    MAX_COMPLETED_OBSERVATIONS,
    BayesianLatestRecommendationResponse,
    BayesianRecommendationCreateRequest,
    BayesianRecommendationCurrentTrialResponse,
    BayesianRecommendationListResponse,
    BayesianRecommendationProvenance,
    BayesianRecommendationResponse,
    BayesianRecommendationResult,
    BayesianTrialResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import (
    APP_VERSION,
    canonical_json_bytes,
    runtime_build_provenance,
    utc_now,
)
from app.services.bayesian_recommendation_consistency import (
    validate_bayesian_recommendation_record,
)
from app.services.bayesian_studies import get_bayesian_study
from app.statistics.bayesian_optimization import (
    BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION,
    BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION,
    bayesian_worker_entry,
)
from app.storage.bayesian_studies import (
    BayesianRecommendationRecord,
    BayesianStorageConflict,
    BayesianTrialRecord,
    count_bayesian_recommendation_records,
    get_bayesian_history_revision_record,
    get_bayesian_recommendation_record,
    get_latest_bayesian_recommendation_record,
    insert_bayesian_recommendation_bundle,
    list_bayesian_recommendation_records,
)

BAYESIAN_METHOD_ID: Final[Literal["doe.bayesian_optimization"]] = "doe.bayesian_optimization"
BAYESIAN_RECOMMENDATION_CONFIG_SCHEMA_VERSION: Final[Literal[1]] = 1
WORKER_STARTUP_ALLOWANCE_MS: Final = 20_000


def create_bayesian_recommendation(
    settings: Settings,
    study_id: UUID,
    body: BayesianRecommendationCreateRequest,
) -> BayesianRecommendationResponse:
    study = get_bayesian_study(settings, study_id)
    if study.status != "active":
        raise _optimization_error("bayesian_study_closed")
    if str(body.expected_history_revision_id) != str(study.observation_history.history_revision_id):
        raise _optimization_error("bayesian_optimization_history_stale")
    if any(trial.origin == "initial_design" and trial.state == "pending" for trial in study.trials):
        raise _optimization_error("bayesian_optimization_history_incomplete")
    if any(trial.origin == "recommendation" and trial.state == "pending" for trial in study.trials):
        raise _optimization_error("bayesian_optimization_pending_recommendation_exists")
    completed = [trial for trial in study.trials if trial.state == "completed"]
    if (
        len(completed) < study.recommendation_minimum_completed_observations
        or len(completed) > MAX_COMPLETED_OBSERVATIONS
    ):
        raise _optimization_error("bayesian_optimization_history_incomplete")
    if _trial_budget_reached(
        trial_count=len(study.trials),
        total_trial_budget=body.search.total_trial_budget,
    ):
        raise _optimization_error("bayesian_optimization_budget_exhausted")

    worker_payload = _recommendation_worker_payload(study, body, completed)
    result_payload = _run_worker(
        worker_payload,
        timeout_ms=body.search.time_budget_ms + WORKER_STARTUP_ALLOWANCE_MS,
    )
    try:
        result = BayesianRecommendationResult.model_validate(result_payload)
    except ValidationError as exc:
        raise _optimization_error("bayesian_optimization_artifact_mismatch") from exc
    factor_ids = {factor.factor_id for factor in study.factors}
    if (
        result.schema_version != BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION
        or result.model.schema_version != BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION
        or set(result.recommended_actual_coordinates) != factor_ids
        or set(result.recommended_normalized_coordinates) != factor_ids
        or len(result.model.length_scales) != len(study.factors)
        or result.objective_direction != study.objective.direction
        or result.model.objective_direction_multiplier
        != (1.0 if study.objective.direction == "maximize" else -1.0)
        or result.model.completed_observation_count != len(completed)
    ):
        raise _optimization_error("bayesian_optimization_artifact_mismatch")

    recommendation_id = uuid4()
    trial_id = uuid4()
    created_at = utc_now()
    trial_number = len(study.trials) + 1
    coordinates_payload = {
        "definition_sha256": study.definition_sha256,
        "trial_number": trial_number,
        "origin": "recommendation",
        "actual_coordinates": result.recommended_actual_coordinates,
        "normalized_coordinates": result.recommended_normalized_coordinates,
    }
    coordinates_sha256 = _sha256(coordinates_payload)
    trial_record = BayesianTrialRecord(
        trial_id=str(trial_id),
        study_version_id=str(study.study_version_id),
        trial_number=trial_number,
        origin="recommendation",
        state="pending",
        actual_coordinates_json=_json_dumps(result.recommended_actual_coordinates),
        normalized_coordinates_json=_json_dumps(result.recommended_normalized_coordinates),
        coordinates_sha256=coordinates_sha256,
        objective_value=None,
        created_at=created_at,
        closed_at=None,
    )
    trial = BayesianTrialResponse(
        trial_id=trial_id,
        study_version_id=study.study_version_id,
        trial_number=trial_number,
        origin="recommendation",
        state="pending",
        actual_coordinates=result.recommended_actual_coordinates,
        normalized_coordinates=result.recommended_normalized_coordinates,
        coordinates_sha256=coordinates_sha256,
        objective_value=None,
        created_at=created_at,
        closed_at=None,
    )
    method_version = METHOD_VERSIONS[BAYESIAN_METHOD_ID]
    config_payload = {
        "schema_version": BAYESIAN_RECOMMENDATION_CONFIG_SCHEMA_VERSION,
        "study_id": str(study.study_id),
        "study_version_id": str(study.study_version_id),
        "definition_sha256": study.definition_sha256,
        "source_history_revision_id": str(study.observation_history.history_revision_id),
        "source_observation_history_sha256": (study.observation_history.observation_history_sha256),
        "request": body.model_dump(mode="json"),
    }
    config_json = _json_dumps(config_payload)
    config_sha256 = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
    result_payload_sha256 = _sha256(result.model_dump(mode="json"))
    runtime = runtime_build_provenance(settings)
    provenance = BayesianRecommendationProvenance(
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        recommendation_id=recommendation_id,
        recommendation_trial_id=trial_id,
        source_history_revision_id=study.observation_history.history_revision_id,
        source_observation_history_sha256=(study.observation_history.observation_history_sha256),
        definition_sha256=study.definition_sha256,
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        config_schema_version=BAYESIAN_RECOMMENDATION_CONFIG_SCHEMA_VERSION,
        result_schema_version=BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION,
        model_schema_version=BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION,
        app_version=APP_VERSION,
        python_version=str(runtime["python_version"]),
        platform=str(runtime["platform"]),
        build_commit=cast(str | None, runtime["build_commit"]),
        package_versions=result.model.package_versions,
        created_at=created_at,
    )
    response = BayesianRecommendationResponse(
        recommendation_id=recommendation_id,
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        source_history_revision_id=study.observation_history.history_revision_id,
        source_observation_history_sha256=(study.observation_history.observation_history_sha256),
        definition_sha256=study.definition_sha256,
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        config_schema_version=BAYESIAN_RECOMMENDATION_CONFIG_SCHEMA_VERSION,
        result_schema_version=BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION,
        model_schema_version=BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION,
        config_sha256=config_sha256,
        result_payload_sha256=result_payload_sha256,
        created_at=created_at,
        trial=trial,
        result=result,
        provenance=provenance,
    )
    result_json = _json_dumps(
        response.model_dump(
            mode="json",
            exclude={"current_trial", "is_latest", "requested_total_trial_budget"},
        )
    )
    record = BayesianRecommendationRecord(
        recommendation_id=str(recommendation_id),
        study_version_id=str(study.study_version_id),
        trial_id=str(trial_id),
        source_history_revision_id=str(study.observation_history.history_revision_id),
        source_observation_history_sha256=(study.observation_history.observation_history_sha256),
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        config_schema_version=BAYESIAN_RECOMMENDATION_CONFIG_SCHEMA_VERSION,
        result_schema_version=BAYESIAN_RECOMMENDATION_RESULT_SCHEMA_VERSION,
        model_schema_version=BAYESIAN_SURROGATE_MODEL_SCHEMA_VERSION,
        config_json=config_json,
        config_sha256=config_sha256,
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        result_payload_sha256=result_payload_sha256,
        created_at=created_at,
        app_version=APP_VERSION,
    )
    try:
        insert_bayesian_recommendation_bundle(
            settings.workspace_root,
            trial=trial_record,
            recommendation=record,
            expected_history_revision_id=str(study.observation_history.history_revision_id),
            expected_history_sha256=(study.observation_history.observation_history_sha256),
        )
    except BayesianStorageConflict as exc:
        raise _optimization_error(exc.code) from exc
    return _with_current_context(
        response,
        current_trial=trial,
        is_latest=True,
        requested_total_trial_budget=body.search.total_trial_budget,
    )


def get_bayesian_recommendation(
    settings: Settings,
    study_id: UUID,
    recommendation_id: UUID,
) -> BayesianRecommendationResponse:
    study = get_bayesian_study(settings, study_id)
    record = get_bayesian_recommendation_record(settings.workspace_root, str(recommendation_id))
    if record is None or record.study_version_id != str(study.study_version_id):
        raise ApiError(
            code="bayesian_recommendation_not_found",
            message="요청한 Bayesian recommendation을 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    latest = get_latest_bayesian_recommendation_record(
        settings.workspace_root,
        str(study.study_version_id),
    )
    return _validated_response(
        settings,
        study,
        record,
        is_latest=latest is not None and latest.recommendation_id == record.recommendation_id,
    )


def get_latest_bayesian_recommendation(
    settings: Settings,
    study_id: UUID,
) -> BayesianLatestRecommendationResponse:
    study = get_bayesian_study(settings, study_id)
    record = get_latest_bayesian_recommendation_record(
        settings.workspace_root,
        str(study.study_version_id),
    )
    return BayesianLatestRecommendationResponse(
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        item=(
            None if record is None else _validated_response(settings, study, record, is_latest=True)
        ),
    )


def list_bayesian_recommendations(
    settings: Settings,
    study_id: UUID,
    *,
    offset: int,
    limit: int,
) -> BayesianRecommendationListResponse:
    study = get_bayesian_study(settings, study_id)
    records = list_bayesian_recommendation_records(
        settings.workspace_root,
        str(study.study_version_id),
        offset=offset,
        limit=limit,
    )
    latest = get_latest_bayesian_recommendation_record(
        settings.workspace_root,
        str(study.study_version_id),
    )
    return BayesianRecommendationListResponse(
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        total=count_bayesian_recommendation_records(
            settings.workspace_root, str(study.study_version_id)
        ),
        offset=offset,
        limit=limit,
        items=[
            _validated_response(
                settings,
                study,
                record,
                is_latest=(
                    latest is not None and latest.recommendation_id == record.recommendation_id
                ),
            )
            for record in records
        ],
    )


def _validated_response(
    settings: Settings,
    study: Any,
    record: BayesianRecommendationRecord,
    *,
    is_latest: bool,
) -> BayesianRecommendationResponse:
    trial = next(
        (item for item in study.trials if str(item.trial_id) == record.trial_id),
        None,
    )
    if trial is None:
        raise _optimization_error("bayesian_optimization_artifact_mismatch")
    try:
        source_observation_values = _source_observation_values(settings, study, record)
        response = validate_bayesian_recommendation_record(
            record=record,
            study_id=str(study.study_id),
            study_version_id=str(study.study_version_id),
            definition_sha256=study.definition_sha256,
            source_history_revision_id=record.source_history_revision_id,
            source_history_sha256=record.source_observation_history_sha256,
            source_observation_values=source_observation_values,
            factors=study.factors,
            constraints=study.constraints,
            objective_direction=study.objective.direction,
            current_trial=trial,
        )
        config = json.loads(record.config_json)
        request = BayesianRecommendationCreateRequest.model_validate(config["request"])
        return _with_current_context(
            response,
            current_trial=trial,
            is_latest=is_latest,
            requested_total_trial_budget=request.search.total_trial_budget,
        )
    except ValueError as exc:
        raise _optimization_error("bayesian_optimization_artifact_mismatch") from exc


def _with_current_context(
    response: BayesianRecommendationResponse,
    *,
    current_trial: BayesianTrialResponse,
    is_latest: bool,
    requested_total_trial_budget: int,
) -> BayesianRecommendationResponse:
    return response.model_copy(
        update={
            "current_trial": BayesianRecommendationCurrentTrialResponse(
                trial_id=current_trial.trial_id,
                state=current_trial.state,
                objective_value=current_trial.objective_value,
                closed_at=current_trial.closed_at,
            ),
            "is_latest": is_latest,
            "requested_total_trial_budget": requested_total_trial_budget,
        }
    )


def _recommendation_worker_payload(
    study: Any,
    body: BayesianRecommendationCreateRequest,
    completed: list[BayesianTrialResponse],
) -> dict[str, Any]:
    return {
        "factors": [
            {"factor_id": factor.factor_id, "low": factor.low, "high": factor.high}
            for factor in study.factors
        ],
        "constraints": [item.model_dump(mode="json") for item in study.constraints],
        "observations": [
            {
                "normalized": trial.normalized_coordinates,
                "objective_value": trial.objective_value,
            }
            for trial in completed
        ],
        "excluded_normalized": [
            [trial.normalized_coordinates[factor.factor_id] for factor in study.factors]
            for trial in study.trials
        ],
        "objective_direction": study.objective.direction,
        "search": {
            key: value
            for key, value in body.search.model_dump(mode="json").items()
            if key != "total_trial_budget"
        },
    }


def _trial_budget_reached(*, trial_count: int, total_trial_budget: int) -> bool:
    return trial_count >= min(total_trial_budget, MAX_BAYESIAN_TRIALS)


def _source_observation_values(
    settings: Settings,
    study: Any,
    record: BayesianRecommendationRecord,
) -> list[float]:
    history = get_bayesian_history_revision_record(
        settings.workspace_root,
        record.source_history_revision_id,
    )
    if (
        history is None
        or history.study_version_id != record.study_version_id
        or history.observation_history_sha256 != record.source_observation_history_sha256
    ):
        raise ValueError("bayesian recommendation source history mismatch")
    completed_ids = json.loads(history.completed_trial_ids_json)
    if (
        not isinstance(completed_ids, list)
        or not all(isinstance(item, str) for item in completed_ids)
        or len(completed_ids) != history.completed_trial_count
    ):
        raise ValueError("bayesian recommendation source history is invalid")
    trials = {str(item.trial_id): item for item in study.trials}
    values: list[float] = []
    for trial_id in completed_ids:
        trial = trials.get(trial_id)
        if trial is None or trial.objective_value is None:
            raise ValueError("bayesian recommendation source observation is missing")
        values.append(float(trial.objective_value))
    return values


def _run_worker(payload: dict[str, Any], *, timeout_ms: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    output_queue = context.Queue(maxsize=1)
    process = context.Process(target=bayesian_worker_entry, args=(output_queue, payload))
    process.start()
    process.join(timeout_ms / 1000.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
        output_queue.close()
        output_queue.join_thread()
        process.close()
        raise _optimization_error("bayesian_optimization_budget_exhausted")
    try:
        message = output_queue.get(timeout=2.0)
    except queue.Empty as exc:
        raise _optimization_error("bayesian_optimization_surrogate_fit_failed") from exc
    finally:
        output_queue.close()
        output_queue.join_thread()
        process.close()
    if not isinstance(message, dict) or message.get("status") != "ok":
        code = (
            message.get("code")
            if isinstance(message, dict)
            else "bayesian_optimization_surrogate_fit_failed"
        )
        raise _optimization_error(str(code))
    result = message.get("result")
    if not isinstance(result, dict):
        raise _optimization_error("bayesian_optimization_artifact_mismatch")
    return result


def _optimization_error(code: str) -> ApiError:
    allowed = {
        "bayesian_optimization_history_incomplete",
        "bayesian_optimization_history_stale",
        "bayesian_optimization_pending_recommendation_exists",
        "bayesian_optimization_constraint_invalid",
        "bayesian_optimization_no_feasible_candidate",
        "bayesian_optimization_duplicate_candidate",
        "bayesian_optimization_surrogate_fit_failed",
        "bayesian_optimization_budget_exhausted",
        "bayesian_optimization_artifact_mismatch",
        "bayesian_study_closed",
    }
    if code == "bayesian_optimization_time_budget_exhausted":
        stable_code = "bayesian_optimization_budget_exhausted"
    else:
        stable_code = code if code in allowed else "bayesian_optimization_surrogate_fit_failed"
    return ApiError(
        code=stable_code,
        message="Bayesian recommendation을 안전하게 생성하거나 복원할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _json_dumps(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
