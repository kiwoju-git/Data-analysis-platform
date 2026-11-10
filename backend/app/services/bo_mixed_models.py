"""Exact-source mixed planning snapshots, never a category-to-numeric adapter."""

import json
from typing import Any
from uuid import UUID, uuid4

from app.api.v1.schemas.bayesian import BayesianFactorRequest
from app.api.v1.schemas.bo_mixed_planning import MixedPlanningCalculationRequest
from app.api.v1.schemas.bo_mixed_studies import MixedCategoricalFactorRequest
from app.api.v1.schemas.bo_mixed_workflow import (
    MixedEvaluationRequest,
    MixedEvaluationResponse,
    MixedModelCreateRequest,
    MixedModelDetail,
    MixedModelList,
    MixedModelSummary,
    MixedSourceRequest,
)
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_noise_recommendations import _error
from app.services.bo_mixed_studies import get_mixed_study
from app.services.bo_planning import _current, _not_found, _run, _summary
from app.storage import bo_planning as storage
from app.storage.bayesian_studies import (
    BayesianStorageConflict,
    get_bayesian_history_revision_record,
)


def calculation_factors(study: Any) -> list[dict[str, Any]]:
    return [
        factor.model_dump(
            mode="json",
            include=set(
                MixedCategoricalFactorRequest.model_fields
                if factor.domain_kind in {"nominal", "ordinal"}
                else BayesianFactorRequest.model_fields
            ),
        )
        for factor in study.factors
    ]


def require_mixed_source(study: Any, body: MixedSourceRequest, *, current: bool = True) -> None:
    if (
        str(body.expected_study_version_id) != str(study.study_version_id)
        or body.expected_definition_sha256 != study.definition_sha256
        or body.expected_trial_count > len(study.trials)
    ):
        raise _error("bayesian_candidate_source_changed")
    if current and (
        body.expected_trial_count != len(study.trials)
        or body.expected_history_revision_id != study.observation_history.history_revision_id
        or body.expected_history_sha256 != study.observation_history.observation_history_sha256
    ):
        raise _error("bayesian_optimization_history_stale")
    if current and study.status != "active":
        raise _error("bayesian_study_closed")


def mixed_calculation_request(
    study: Any, body: MixedModelCreateRequest, source_ids: list[str]
) -> MixedPlanningCalculationRequest:
    trials = {str(row.trial_id): row for row in study.trials}
    source = [trials[key] for key in source_ids]
    if any(
        row.state != "completed" or row.trial_number > body.expected_trial_count for row in source
    ):
        raise _error("bayesian_planning_artifact_invalid")
    return MixedPlanningCalculationRequest.model_validate(
        {
            "schema_version": 8,
            "factors": calculation_factors(study),
            "constraints": [row.model_dump(mode="json") for row in study.constraints],
            "objective": study.objective.model_dump(mode="json"),
            "observations": [
                {
                    "trial_id": str(row.trial_id),
                    "actual_coordinates": row.actual_coordinates,
                    "encoded_coordinates": row.encoded_coordinates,
                    "response_values": row.response_values,
                }
                for row in source
            ],
            "excluded_encoded": [
                [trial.encoded_coordinates[factor.factor_id] for factor in study.factors]
                for trial in study.trials
                if trial.trial_number <= body.expected_trial_count
            ],
            **body.fit.model_dump(mode="json"),
        }
    )


def read_mixed_model(
    settings: Settings, study: Any, model_id: UUID
) -> tuple[dict[str, Any], dict[str, Any], MixedModelCreateRequest]:
    try:
        record = storage.get_planning_model(
            settings.workspace_root, str(model_id), str(study.study_version_id)
        )
        if record is None:
            raise _not_found()
        body = MixedModelCreateRequest.model_validate_json(record["config_json"])
        snapshot = json.loads(record["snapshot_json"])
        require_mixed_source(study, body, current=False)
        history = get_bayesian_history_revision_record(
            settings.workspace_root, str(body.expected_history_revision_id)
        )
        if (
            record["schema_version"] != 2
            or history is None
            or history.schema_version != 2
            or history.study_version_id != str(study.study_version_id)
            or history.observation_history_sha256 != body.expected_history_sha256
            or record["source_history_revision_id"] != history.history_revision_id
            or record["history_sha256"] != history.observation_history_sha256
            or record["definition_sha256"] != study.definition_sha256
            or record["request_id"] != str(body.request_id)
            or storage.planning_json(body.model_dump(mode="json")) != record["config_json"]
            or storage.planning_json(snapshot) != record["snapshot_json"]
            or snapshot["schema_version"] != 2
            or snapshot["policy"] != "source_locked_mixed_bo_planning_model_v1"
        ):
            raise ValueError
        expected = mixed_calculation_request(
            study, body, json.loads(history.completed_trial_ids_json)
        )
        if snapshot["calculation_request"] != expected.worker_payload():
            raise ValueError
        return record, snapshot, body
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    except (ValueError, TypeError, KeyError, AttributeError):
        raise _error("bayesian_planning_artifact_invalid") from None


def get_mixed_model(settings: Settings, study_id: UUID, model_id: UUID) -> MixedModelDetail:
    study = get_mixed_study(settings, study_id)
    record, snapshot, body = read_mixed_model(settings, study, model_id)
    try:
        return MixedModelDetail.model_validate(
            {
                **_summary(study, record),
                "fit": body.fit,
                "objective": snapshot["calculation_request"]["objective"],
                **{
                    key: snapshot[key]
                    for key in (
                        "response_models",
                        "incumbent",
                        "observation_view",
                        "warnings",
                    )
                },
            }
        )
    except (ValueError, KeyError):
        raise _error("bayesian_planning_artifact_invalid") from None


def list_mixed_models(settings: Settings, study_id: UUID) -> MixedModelList:
    study = get_mixed_study(settings, study_id)
    records = storage.list_planning_models(settings.workspace_root, str(study.study_version_id))
    return MixedModelList(
        items=[MixedModelSummary.model_validate(_summary(study, record)) for record in records]
    )


def create_mixed_model(
    settings: Settings, study_id: UUID, body: MixedModelCreateRequest
) -> MixedModelDetail:
    study = get_mixed_study(settings, study_id)
    try:
        old = storage.find_planning_request(
            settings.workspace_root, str(study.study_version_id), str(body.request_id), kind="model"
        )
        config = body.model_dump(mode="json")
        if old is not None:
            if old["schema_version"] != 2 or old["config_sha256"] != storage.planning_sha(config):
                raise _error("bayesian_planning_request_conflict")
            return get_mixed_model(settings, study_id, UUID(old["model_id"]))
        require_mixed_source(study, body)
        request = mixed_calculation_request(
            study, body, [str(row.trial_id) for row in study.trials if row.state == "completed"]
        )
        snapshot = _run(
            "mixed_fit", request.worker_payload(), time_budget_ms=body.fit.search.time_budget_ms
        )
        if snapshot["calculation_request"] != request.worker_payload():
            raise _error("bayesian_planning_snapshot_invalid")
        record = {
            "model_id": str(uuid4()),
            "study_version_id": str(study.study_version_id),
            "source_history_revision_id": str(body.expected_history_revision_id),
            "definition_sha256": study.definition_sha256,
            "history_sha256": body.expected_history_sha256,
            "schema_version": 2,
            "request_id": str(body.request_id),
            "config_json": storage.planning_json(config),
            "config_sha256": storage.planning_sha(config),
            "snapshot_json": storage.planning_json(snapshot),
            "snapshot_sha256": storage.planning_sha(snapshot),
            "created_at": utc_now(),
        }
        identity = storage.insert_planning_model(settings.workspace_root, record)
        return get_mixed_model(settings, study_id, UUID(identity))
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc


def evaluate_mixed_model(
    settings: Settings, study_id: UUID, model_id: UUID, body: MixedEvaluationRequest
) -> MixedEvaluationResponse:
    study = get_mixed_study(settings, study_id)
    record, snapshot, _ = read_mixed_model(settings, study, model_id)
    if body.expected_model_sha256 != record["snapshot_sha256"]:
        raise _error("bayesian_planning_model_mismatch")
    rows = _run(
        "mixed_evaluate",
        {
            "snapshot": snapshot,
            "points": body.points,
            "time_budget_ms": body.time_budget_ms,
            "max_moment_evaluations": body.max_moment_evaluations,
            "eligibility_excluded_encoded": [
                [trial.encoded_coordinates[factor.factor_id] for factor in study.factors]
                for trial in study.trials
            ],
        },
        time_budget_ms=body.time_budget_ms,
    )
    return MixedEvaluationResponse(
        model_id=model_id,
        snapshot_sha256=record["snapshot_sha256"],
        items=rows,
        eligibility_history_sha256=study.observation_history.observation_history_sha256,
        eligibility_is_current=_current(study, record),
    )
