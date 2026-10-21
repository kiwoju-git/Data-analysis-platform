from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import status
from pydantic import ValidationError

from app.api.v1.schemas.bayesian import (
    BayesianReplicateCreateRequest,
    BayesianReplicateCreateResponse,
    BayesianReplicateTrialResponse,
)
from app.core.config import Settings
from app.core.errors import ApiError
from app.services.analysis_run_execution import canonical_json_bytes, utc_now
from app.storage.bayesian_replicates import (
    insert_bayesian_replicates,
    list_bayesian_replicate_requests,
)
from app.storage.bayesian_studies import (
    BayesianHistoryRevisionRecord,
    BayesianStorageConflict,
    BayesianStudyVersionRecord,
    BayesianTrialRecord,
    get_bayesian_trial_record,
)


def create_bayesian_replicates(
    settings: Settings,
    study_id: UUID,
    trial_id: UUID,
    body: BayesianReplicateCreateRequest,
) -> BayesianReplicateCreateResponse:
    from app.services.bayesian_studies import _trial_response, get_bayesian_study

    study = get_bayesian_study(settings, study_id)
    parent = get_bayesian_trial_record(settings.workspace_root, str(trial_id))
    if parent is None or parent.study_version_id != str(study.study_version_id):
        raise _error("bayesian_replicate_parent_not_completed")
    now = utc_now()
    payload = {
        "schema_version": 1,
        "study_id": str(study_id),
        "study_version_id": str(study.study_version_id),
        "parent_trial_id": str(trial_id),
        "request": body.model_dump(mode="json"),
    }
    request_bytes = canonical_json_bytes(payload)
    request_sha = hashlib.sha256(request_bytes).hexdigest()
    records = []
    for index in range(body.count):
        number = study.trial_count + index + 1
        coordinates = {
            "definition_sha256": study.definition_sha256,
            "trial_number": number,
            "origin": "replicate",
            "actual_coordinates": json.loads(parent.actual_coordinates_json),
            "normalized_coordinates": json.loads(parent.normalized_coordinates_json),
            "replicate_of_trial_id": str(trial_id),
        }
        records.append(
            BayesianTrialRecord(
                trial_id=str(uuid4()),
                study_version_id=str(study.study_version_id),
                trial_number=number,
                origin="replicate",
                state="pending",
                actual_coordinates_json=parent.actual_coordinates_json,
                normalized_coordinates_json=parent.normalized_coordinates_json,
                coordinates_sha256=hashlib.sha256(canonical_json_bytes(coordinates)).hexdigest(),
                objective_value=None,
                created_at=now,
                closed_at=None,
                replicate_of_trial_id=str(trial_id),
            )
        )
    try:
        identities, replayed = insert_bayesian_replicates(
            settings.workspace_root,
            study_version_id=str(study.study_version_id),
            parent_trial_id=str(trial_id),
            request_id=str(body.request_id),
            request_sha256=request_sha,
            request_json=request_bytes.decode("utf-8"),
            expected_history_revision_id=str(body.expected_history_revision_id),
            expected_history_sha256=body.expected_history_sha256,
            trials=records,
            total_trial_budget=body.total_trial_budget,
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    trials = []
    for identity in identities:
        record = get_bayesian_trial_record(settings.workspace_root, identity)
        if record is None:
            raise _error("bayesian_optimization_artifact_mismatch")
        response = _trial_response(record)
        if not isinstance(response, BayesianReplicateTrialResponse):
            raise _error("bayesian_optimization_artifact_mismatch")
        trials.append(response)
    return BayesianReplicateCreateResponse(
        study_id=study_id,
        study_version_id=study.study_version_id,
        request_id=body.request_id,
        parent_trial_id=trial_id,
        source_history_revision_id=body.expected_history_revision_id,
        source_history_sha256=body.expected_history_sha256,
        request_sha256=request_sha,
        trials=trials,
        replayed=replayed,
    )


def validate_replicate_requests(
    workspace_root: Path,
    version: BayesianStudyVersionRecord,
    trials: list[BayesianTrialRecord],
    histories: list[BayesianHistoryRevisionRecord],
) -> None:
    records = list_bayesian_replicate_requests(workspace_root, version.study_version_id)
    by_id = {trial.trial_id: trial for trial in trials}
    history_by_id = {history.history_revision_id: history for history in histories}
    seen: set[str] = set()
    try:
        for record in records:
            payload, identities = json.loads(record.request_json), json.loads(record.trial_ids_json)
            request = BayesianReplicateCreateRequest.model_validate(payload["request"])
            history = history_by_id.get(record.source_history_revision_id)
            parent = by_id.get(record.parent_trial_id)
            if (
                hashlib.sha256(record.request_json.encode("utf-8")).hexdigest()
                != record.request_sha256
                or payload.get("schema_version") != 1
                or payload.get("study_id") != version.study_id
                or payload.get("study_version_id") != version.study_version_id
                or payload.get("parent_trial_id") != record.parent_trial_id
                or str(request.request_id) != record.request_id
                or str(request.expected_history_revision_id) != record.source_history_revision_id
                or request.expected_history_sha256 != record.source_history_sha256
                or history is None
                or history.observation_history_sha256 != record.source_history_sha256
                or parent is None
                or parent.state != "completed"
                or parent.trial_id not in json.loads(history.completed_trial_ids_json)
                or not isinstance(identities, list)
                or len(identities) != request.count
                or any(not isinstance(identity, str) for identity in identities)
                or len(set(identities)) != len(identities)
                or seen.intersection(identities)
            ):
                raise ValueError("replicate relationship mismatch")
            numbers = []
            for identity in identities:
                trial = by_id.get(identity)
                if (
                    trial is None
                    or trial.origin != "replicate"
                    or trial.replicate_of_trial_id != parent.trial_id
                    or trial.created_at != record.created_at
                    or trial.trial_number <= parent.trial_number
                    or trial.trial_number > request.total_trial_budget
                ):
                    raise ValueError("replicate ownership mismatch")
                numbers.append(trial.trial_number)
            if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
                raise ValueError("replicate bundle is not consecutive")
            seen.update(identities)
        if seen != {trial.trial_id for trial in trials if trial.origin == "replicate"}:
            raise ValueError("replicate provenance missing")
    except (KeyError, TypeError, ValueError, ValidationError) as exc:
        raise _error("bayesian_optimization_artifact_mismatch") from exc


def validate_replicate_observation_history(
    workspace_root: Path,
    trial: BayesianTrialRecord,
    current_history: BayesianHistoryRevisionRecord,
    histories: list[BayesianHistoryRevisionRecord],
) -> None:
    records = list_bayesian_replicate_requests(workspace_root, trial.study_version_id)
    current_ids = set(json.loads(current_history.completed_trial_ids_json))
    history_by_id = {history.history_revision_id: history for history in histories}
    for record in records:
        sibling_ids = set(json.loads(record.trial_ids_json))
        if trial.trial_id not in sibling_ids:
            continue
        source = history_by_id.get(record.source_history_revision_id)
        if source is not None:
            source_ids = set(json.loads(source.completed_trial_ids_json))
            if source_ids <= current_ids and current_ids - source_ids <= sibling_ids:
                return
        break
    raise _error("bayesian_optimization_history_stale")


def _error(code: str) -> ApiError:
    return ApiError(
        code=code,
        message="The replicate request could not be safely applied.",
        status_code=status.HTTP_409_CONFLICT,
    )
