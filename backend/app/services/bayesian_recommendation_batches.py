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
    BayesianBatchSearchBudgetResponse,
    BayesianBatchSharedModelResponse,
    BayesianLatestRecommendationBatchResponse,
    BayesianRecommendationBatchCreateRequest,
    BayesianRecommendationBatchItemResponse,
    BayesianRecommendationBatchListResponse,
    BayesianRecommendationBatchProvenance,
    BayesianRecommendationBatchResponse,
    BayesianRecommendationCurrentTrialResponse,
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
from app.services.bayesian_studies import get_bayesian_study
from app.statistics.bayesian_batch import (
    BAYESIAN_BATCH_ITEM_SCHEMA_VERSION,
    BAYESIAN_BATCH_MODEL_SCHEMA_VERSION,
    BAYESIAN_BATCH_POLICY,
    BAYESIAN_BATCH_RESULT_SCHEMA_VERSION,
    bayesian_batch_worker_entry,
)
from app.storage.bayesian_studies import (
    BayesianRecommendationBatchItemRecord,
    BayesianRecommendationBatchRecord,
    BayesianStorageConflict,
    BayesianTrialRecord,
    count_bayesian_recommendation_batch_records,
    get_bayesian_history_revision_record,
    get_bayesian_recommendation_batch_record,
    get_latest_bayesian_recommendation_batch_record,
    insert_bayesian_recommendation_batch_bundle,
    list_bayesian_recommendation_batch_item_records,
    list_bayesian_recommendation_batch_records,
)

BAYESIAN_METHOD_ID: Final[Literal["doe.bayesian_optimization"]] = "doe.bayesian_optimization"
BAYESIAN_BATCH_CONFIG_SCHEMA_VERSION: Final[Literal[1]] = 1
WORKER_STARTUP_ALLOWANCE_MS: Final = 20_000


def create_bayesian_recommendation_batch(
    settings: Settings,
    study_id: UUID,
    body: BayesianRecommendationBatchCreateRequest,
) -> BayesianRecommendationBatchResponse:
    study = get_bayesian_study(settings, study_id)
    if study.status != "active":
        raise _batch_error("bayesian_study_closed")
    if str(body.expected_history_revision_id) != str(study.observation_history.history_revision_id):
        raise _batch_error("bayesian_optimization_history_stale")
    if any(trial.origin == "initial_design" and trial.state == "pending" for trial in study.trials):
        raise _batch_error("bayesian_optimization_history_incomplete")
    if any(trial.origin == "recommendation" and trial.state == "pending" for trial in study.trials):
        raise _batch_error("bayesian_optimization_pending_recommendation_exists")
    completed = [trial for trial in study.trials if trial.state == "completed"]
    if (
        len(completed) < study.recommendation_minimum_completed_observations
        or len(completed) > MAX_COMPLETED_OBSERVATIONS
    ):
        raise _batch_error("bayesian_optimization_history_incomplete")
    goal_type = study.objective.goal_type or study.objective.direction
    expected_acquisition = (
        "expected_target_improvement" if goal_type == "match_target" else "expected_improvement"
    )
    if body.acquisition.kind != expected_acquisition:
        raise _batch_error("bayesian_optimization_acquisition_goal_mismatch")
    remaining = min(
        body.search.total_trial_budget,
        MAX_BAYESIAN_TRIALS,
    ) - len(study.trials)
    if body.batch_size > remaining:
        raise _batch_error("bayesian_optimization_batch_budget_exceeded")

    raw_result = _run_worker(
        _worker_payload(study, body, completed),
        timeout_ms=body.search.time_budget_ms + WORKER_STARTUP_ALLOWANCE_MS,
    )
    try:
        shared_model = BayesianBatchSharedModelResponse.model_validate(raw_result["shared_model"])
        search_budget = BayesianBatchSearchBudgetResponse.model_validate(
            raw_result["search_budget"]
        )
        raw_items = raw_result["items"]
    except (KeyError, TypeError, ValidationError) as exc:
        raise _batch_error("bayesian_optimization_artifact_mismatch") from exc
    if (
        raw_result.get("schema_version") != BAYESIAN_BATCH_RESULT_SCHEMA_VERSION
        or raw_result.get("batch_policy") != BAYESIAN_BATCH_POLICY
        or raw_result.get("batch_size") != body.batch_size
        or not isinstance(raw_items, list)
        or len(raw_items) != body.batch_size
        or shared_model.schema_version != BAYESIAN_BATCH_MODEL_SCHEMA_VERSION
        or shared_model.objective_goal_type != goal_type
        or shared_model.completed_observation_count != len(completed)
    ):
        raise _batch_error("bayesian_optimization_artifact_mismatch")

    batch_id = uuid4()
    item_ids = [uuid4() for _ in range(body.batch_size)]
    trial_ids = [uuid4() for _ in range(body.batch_size)]
    created_at = utc_now()
    trial_records: list[BayesianTrialRecord] = []
    trial_responses: list[BayesianTrialResponse] = []
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict) or raw_item.get("rank") != index + 1:
            raise _batch_error("bayesian_optimization_artifact_mismatch")
        actual = _numeric_dict(raw_item.get("actual_coordinates"))
        normalized = _numeric_dict(raw_item.get("normalized_coordinates"))
        factor_ids = {factor.factor_id for factor in study.factors}
        if set(actual) != factor_ids or set(normalized) != factor_ids:
            raise _batch_error("bayesian_optimization_artifact_mismatch")
        trial_number = len(study.trials) + index + 1
        coordinates_sha256 = _sha256(
            {
                "definition_sha256": study.definition_sha256,
                "trial_number": trial_number,
                "origin": "recommendation",
                "actual_coordinates": actual,
                "normalized_coordinates": normalized,
            }
        )
        trial_record = BayesianTrialRecord(
            trial_id=str(trial_ids[index]),
            study_version_id=str(study.study_version_id),
            trial_number=trial_number,
            origin="recommendation",
            state="pending",
            actual_coordinates_json=_json_dumps(actual),
            normalized_coordinates_json=_json_dumps(normalized),
            coordinates_sha256=coordinates_sha256,
            objective_value=None,
            created_at=created_at,
            closed_at=None,
        )
        trial_records.append(trial_record)
        trial_responses.append(
            BayesianTrialResponse(
                trial_id=trial_ids[index],
                study_version_id=study.study_version_id,
                trial_number=trial_number,
                origin="recommendation",
                state="pending",
                actual_coordinates=actual,
                normalized_coordinates=normalized,
                coordinates_sha256=coordinates_sha256,
                objective_value=None,
                created_at=created_at,
                closed_at=None,
            )
        )

    items: list[BayesianRecommendationBatchItemResponse] = []
    for index, raw_item in enumerate(raw_items):
        conditioned_ranks = raw_item.get("conditioned_on_ranks")
        if not isinstance(conditioned_ranks, list) or conditioned_ranks != list(
            range(1, index + 1)
        ):
            raise _batch_error("bayesian_optimization_artifact_mismatch")
        try:
            item_payload = {
                key: value for key, value in raw_item.items() if key != "conditioned_on_ranks"
            }
            item = BayesianRecommendationBatchItemResponse.model_validate(
                {
                    **item_payload,
                    "item_id": str(item_ids[index]),
                    "batch_id": str(batch_id),
                    "trial": trial_responses[index].model_dump(mode="json"),
                    "current_trial": {
                        "trial_id": str(trial_ids[index]),
                        "state": "pending",
                        "objective_value": None,
                        "closed_at": None,
                    },
                    "conditioned_on_item_ids": [
                        str(item_ids[rank - 1]) for rank in conditioned_ranks
                    ],
                }
            )
        except ValidationError as exc:
            raise _batch_error("bayesian_optimization_artifact_mismatch") from exc
        items.append(item)

    method_version = METHOD_VERSIONS[BAYESIAN_METHOD_ID]
    config_payload = {
        "schema_version": BAYESIAN_BATCH_CONFIG_SCHEMA_VERSION,
        "study_id": str(study.study_id),
        "study_version_id": str(study.study_version_id),
        "definition_sha256": study.definition_sha256,
        "source_history_revision_id": str(study.observation_history.history_revision_id),
        "source_observation_history_sha256": (study.observation_history.observation_history_sha256),
        "request": body.model_dump(mode="json"),
    }
    config_json = _json_dumps(config_payload)
    config_sha256 = hashlib.sha256(config_json.encode("utf-8")).hexdigest()
    runtime = runtime_build_provenance(settings)
    provenance = BayesianRecommendationBatchProvenance(
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        batch_id=batch_id,
        source_history_revision_id=study.observation_history.history_revision_id,
        source_observation_history_sha256=(study.observation_history.observation_history_sha256),
        definition_sha256=study.definition_sha256,
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        config_schema_version=BAYESIAN_BATCH_CONFIG_SCHEMA_VERSION,
        result_schema_version=BAYESIAN_BATCH_RESULT_SCHEMA_VERSION,
        model_schema_version=BAYESIAN_BATCH_MODEL_SCHEMA_VERSION,
        item_schema_version=BAYESIAN_BATCH_ITEM_SCHEMA_VERSION,
        app_version=APP_VERSION,
        python_version=str(runtime["python_version"]),
        platform=str(runtime["platform"]),
        build_commit=cast(str | None, runtime["build_commit"]),
        package_versions=shared_model.package_versions,
        created_at=created_at,
    )
    response = BayesianRecommendationBatchResponse(
        batch_id=batch_id,
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        source_history_revision_id=study.observation_history.history_revision_id,
        source_observation_history_sha256=(study.observation_history.observation_history_sha256),
        definition_sha256=study.definition_sha256,
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        config_schema_version=BAYESIAN_BATCH_CONFIG_SCHEMA_VERSION,
        result_schema_version=BAYESIAN_BATCH_RESULT_SCHEMA_VERSION,
        model_schema_version=BAYESIAN_BATCH_MODEL_SCHEMA_VERSION,
        item_schema_version=BAYESIAN_BATCH_ITEM_SCHEMA_VERSION,
        batch_policy=BAYESIAN_BATCH_POLICY,
        execution_mode=body.execution_mode,
        batch_size=body.batch_size,
        acquisition=body.acquisition,
        shared_model=shared_model,
        search_budget=search_budget,
        items=items,
        warnings=_string_list(raw_result.get("warnings")),
        limitations=_string_list(raw_result.get("limitations")),
        config_sha256=config_sha256,
        result_sha256="0" * 64,
        provenance=provenance,
        created_at=created_at,
        is_latest=False,
        batch_state="pending",
        requested_total_trial_budget=body.search.total_trial_budget,
    )
    immutable_payload = response.model_dump(
        mode="json",
        exclude={"is_latest", "batch_state"},
    )
    result_sha256 = _sha256(immutable_payload)
    response = response.model_copy(update={"result_sha256": result_sha256, "is_latest": True})
    result_json = _json_dumps(
        response.model_dump(mode="json", exclude={"is_latest", "batch_state"})
    )
    batch_record = BayesianRecommendationBatchRecord(
        batch_id=str(batch_id),
        study_version_id=str(study.study_version_id),
        source_history_revision_id=str(study.observation_history.history_revision_id),
        source_observation_history_sha256=(study.observation_history.observation_history_sha256),
        method_id=BAYESIAN_METHOD_ID,
        method_version=method_version,
        batch_size=body.batch_size,
        batch_policy=BAYESIAN_BATCH_POLICY,
        config_schema_version=BAYESIAN_BATCH_CONFIG_SCHEMA_VERSION,
        result_schema_version=BAYESIAN_BATCH_RESULT_SCHEMA_VERSION,
        model_schema_version=BAYESIAN_BATCH_MODEL_SCHEMA_VERSION,
        item_schema_version=BAYESIAN_BATCH_ITEM_SCHEMA_VERSION,
        config_json=config_json,
        config_sha256=config_sha256,
        result_json=result_json,
        result_sha256=hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
        created_at=created_at,
        app_version=APP_VERSION,
    )
    item_records = [
        BayesianRecommendationBatchItemRecord(
            item_id=str(item.item_id),
            batch_id=str(batch_id),
            trial_id=str(item.trial.trial_id),
            rank=item.rank,
            item_schema_version=BAYESIAN_BATCH_ITEM_SCHEMA_VERSION,
            item_result_json=_json_dumps(item.model_dump(mode="json")),
            item_result_sha256=hashlib.sha256(
                _json_dumps(item.model_dump(mode="json")).encode("utf-8")
            ).hexdigest(),
            created_at=created_at,
        )
        for item in items
    ]
    try:
        insert_bayesian_recommendation_batch_bundle(
            settings.workspace_root,
            trials=trial_records,
            batch=batch_record,
            items=item_records,
            expected_history_revision_id=str(study.observation_history.history_revision_id),
            expected_history_sha256=(study.observation_history.observation_history_sha256),
            total_trial_budget=body.search.total_trial_budget,
        )
    except BayesianStorageConflict as exc:
        raise _batch_error(exc.code) from exc
    return response


def get_bayesian_recommendation_batch(
    settings: Settings,
    study_id: UUID,
    batch_id: UUID,
) -> BayesianRecommendationBatchResponse:
    study = get_bayesian_study(settings, study_id)
    record = get_bayesian_recommendation_batch_record(
        settings.workspace_root,
        str(batch_id),
    )
    if record is None or record.study_version_id != str(study.study_version_id):
        raise ApiError(
            code="bayesian_recommendation_batch_not_found",
            message="요청한 Bayesian recommendation batch를 찾을 수 없습니다.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    latest = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root,
        str(study.study_version_id),
    )
    return _validated_response(
        settings,
        study,
        record,
        is_latest=latest is not None and latest.batch_id == record.batch_id,
    )


def get_latest_bayesian_recommendation_batch(
    settings: Settings,
    study_id: UUID,
) -> BayesianLatestRecommendationBatchResponse:
    study = get_bayesian_study(settings, study_id)
    record = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root,
        str(study.study_version_id),
    )
    return BayesianLatestRecommendationBatchResponse(
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        item=(
            None if record is None else _validated_response(settings, study, record, is_latest=True)
        ),
    )


def list_bayesian_recommendation_batches(
    settings: Settings,
    study_id: UUID,
    *,
    offset: int,
    limit: int,
) -> BayesianRecommendationBatchListResponse:
    study = get_bayesian_study(settings, study_id)
    records = list_bayesian_recommendation_batch_records(
        settings.workspace_root,
        str(study.study_version_id),
        offset=offset,
        limit=limit,
    )
    latest = get_latest_bayesian_recommendation_batch_record(
        settings.workspace_root,
        str(study.study_version_id),
    )
    return BayesianRecommendationBatchListResponse(
        study_id=study.study_id,
        study_version_id=study.study_version_id,
        total=count_bayesian_recommendation_batch_records(
            settings.workspace_root,
            str(study.study_version_id),
        ),
        offset=offset,
        limit=limit,
        items=[
            _validated_response(
                settings,
                study,
                record,
                is_latest=latest is not None and latest.batch_id == record.batch_id,
            )
            for record in records
        ],
    )


def _validated_response(
    settings: Settings,
    study: Any,
    record: BayesianRecommendationBatchRecord,
    *,
    is_latest: bool,
) -> BayesianRecommendationBatchResponse:
    if (
        hashlib.sha256(record.config_json.encode("utf-8")).hexdigest() != record.config_sha256
        or hashlib.sha256(record.result_json.encode("utf-8")).hexdigest() != record.result_sha256
    ):
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    try:
        config = json.loads(record.config_json)
        request = BayesianRecommendationBatchCreateRequest.model_validate(config["request"])
        response = BayesianRecommendationBatchResponse.model_validate(
            json.loads(record.result_json)
        )
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise _batch_error("bayesian_optimization_artifact_mismatch") from exc
    immutable_payload = response.model_dump(
        mode="json",
        exclude={"is_latest", "batch_state"},
    )
    result_sha = immutable_payload.pop("result_sha256", None)
    if (
        result_sha != response.result_sha256
        or _sha256({**immutable_payload, "result_sha256": "0" * 64}) != response.result_sha256
        or record.batch_id != str(response.batch_id)
        or record.study_version_id != str(study.study_version_id)
        or record.source_history_revision_id != str(response.source_history_revision_id)
        or record.source_observation_history_sha256 != response.source_observation_history_sha256
        or record.config_sha256 != response.config_sha256
        or record.batch_size != response.batch_size
        or record.batch_policy != response.batch_policy
        or response.definition_sha256 != study.definition_sha256
        or response.method_version != record.method_version
    ):
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    history = get_bayesian_history_revision_record(
        settings.workspace_root,
        record.source_history_revision_id,
    )
    if (
        history is None
        or history.study_version_id != record.study_version_id
        or history.observation_history_sha256 != record.source_observation_history_sha256
    ):
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    item_records = list_bayesian_recommendation_batch_item_records(
        settings.workspace_root,
        record.batch_id,
    )
    if len(item_records) != record.batch_size:
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    trials = {str(item.trial_id): item for item in study.trials}
    current_items: list[BayesianRecommendationBatchItemResponse] = []
    for expected_rank, (stored_item, response_item) in enumerate(
        zip(item_records, response.items, strict=True),
        start=1,
    ):
        item_json = _json_dumps(response_item.model_dump(mode="json"))
        trial = trials.get(stored_item.trial_id)
        if (
            expected_rank != stored_item.rank
            or response_item.rank != expected_rank
            or stored_item.item_id != str(response_item.item_id)
            or stored_item.batch_id != record.batch_id
            or stored_item.item_result_json != item_json
            or hashlib.sha256(item_json.encode("utf-8")).hexdigest()
            != stored_item.item_result_sha256
            or trial is None
            or response_item.trial.trial_id != trial.trial_id
            or response_item.trial.coordinates_sha256 != trial.coordinates_sha256
            or response_item.actual_coordinates != trial.actual_coordinates
            or response_item.normalized_coordinates != trial.normalized_coordinates
        ):
            raise _batch_error("bayesian_optimization_artifact_mismatch")
        current_items.append(
            response_item.model_copy(
                update={
                    "current_trial": BayesianRecommendationCurrentTrialResponse(
                        trial_id=trial.trial_id,
                        state=trial.state,
                        objective_value=trial.objective_value,
                        closed_at=trial.closed_at,
                    )
                }
            )
        )
    return response.model_copy(
        update={
            "items": current_items,
            "is_latest": is_latest,
            "batch_state": _batch_state(current_items),
            "requested_total_trial_budget": request.search.total_trial_budget,
        }
    )


def _worker_payload(
    study: Any,
    body: BayesianRecommendationBatchCreateRequest,
    completed: list[BayesianTrialResponse],
) -> dict[str, Any]:
    goal_type = study.objective.goal_type or study.objective.direction
    return {
        "factors": [
            {
                "factor_id": factor.factor_id,
                "low": factor.low,
                "high": factor.high,
                "domain_kind": factor.domain_kind,
                "step": factor.step,
            }
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
        "objective": {
            "goal_type": goal_type,
            "target_value": study.objective.target_value,
        },
        "batch_size": body.batch_size,
        "acquisition": body.acquisition.model_dump(mode="json"),
        "search": {
            key: value
            for key, value in body.search.model_dump(mode="json").items()
            if key != "total_trial_budget"
        },
    }


def _run_worker(payload: dict[str, Any], *, timeout_ms: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    output_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=bayesian_batch_worker_entry,
        args=(output_queue, payload),
    )
    process.start()
    process.join(timeout_ms / 1000.0)
    if process.is_alive():
        process.terminate()
        process.join(timeout=5.0)
        output_queue.close()
        output_queue.join_thread()
        process.close()
        raise _batch_error("bayesian_optimization_batch_incomplete")
    try:
        message = output_queue.get(timeout=2.0)
    except queue.Empty as exc:
        raise _batch_error("bayesian_optimization_surrogate_fit_failed") from exc
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
        raise _batch_error(str(code))
    result = message.get("result")
    if not isinstance(result, dict):
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    return result


def _batch_state(
    items: list[BayesianRecommendationBatchItemResponse],
) -> Literal[
    "pending",
    "partially_completed",
    "completed",
    "abandoned",
    "closed_mixed",
]:
    states = [item.current_trial.state for item in items]
    if all(state == "pending" for state in states):
        return "pending"
    if any(state == "pending" for state in states):
        return "partially_completed"
    if all(state == "completed" for state in states):
        return "completed"
    if all(state == "abandoned" for state in states):
        return "abandoned"
    return "closed_mixed"


def _numeric_dict(value: object) -> dict[str, float]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) and isinstance(item, int | float) and not isinstance(item, bool)
        for key, item in value.items()
    ):
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    return {key: float(item) for key, item in value.items()}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _batch_error("bayesian_optimization_artifact_mismatch")
    return list(value)


def _batch_error(code: str) -> ApiError:
    allowed = {
        "bayesian_optimization_history_incomplete",
        "bayesian_optimization_history_stale",
        "bayesian_optimization_pending_recommendation_exists",
        "bayesian_optimization_no_feasible_candidate",
        "bayesian_optimization_duplicate_candidate",
        "bayesian_optimization_surrogate_fit_failed",
        "bayesian_optimization_budget_exhausted",
        "bayesian_optimization_batch_budget_exceeded",
        "bayesian_optimization_batch_incomplete",
        "bayesian_optimization_acquisition_goal_mismatch",
        "bayesian_optimization_artifact_mismatch",
        "bayesian_study_closed",
    }
    stable = code if code in allowed else "bayesian_optimization_surrogate_fit_failed"
    return ApiError(
        code=stable,
        message="Bayesian recommendation batch를 안전하게 생성하거나 복원할 수 없습니다.",
        status_code=status.HTTP_409_CONFLICT,
    )


def _json_dumps(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
