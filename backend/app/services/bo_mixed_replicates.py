"""Explicit mixed-condition replication using the existing atomic lifecycle store."""

from uuid import UUID

from app.api.v1.schemas.bayesian import BayesianReplicateCreateRequest
from app.api.v1.schemas.bo_mixed_studies import MixedReplicateCreateResponse
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_replicates import _error
from app.services.bayesian_studies import _json_dumps, _sha256
from app.services.bo_mixed_studies import (
    load_validated_mixed_study,
    mixed_trial_response,
    new_mixed_trial_record,
    project_mixed_trial,
)
from app.storage.bayesian_replicates import insert_bayesian_replicates
from app.storage.bayesian_studies import BayesianStorageConflict


def create_mixed_replicates(
    settings: Settings, study_id: UUID, trial_id: UUID, body: BayesianReplicateCreateRequest
) -> MixedReplicateCreateResponse:
    bundle = load_validated_mixed_study(settings, str(study_id))
    parent = next((trial for trial in bundle.trials if trial.trial_id == str(trial_id)), None)
    if parent is None or parent.state != "completed":
        raise _error("bayesian_replicate_parent_not_completed")
    point = project_mixed_trial(bundle, parent).actual_coordinates
    payload = {
        "schema_version": 1,
        "study_id": str(study_id),
        "study_version_id": bundle.version.study_version_id,
        "parent_trial_id": str(trial_id),
        "request": body.model_dump(mode="json"),
    }
    checksum = _sha256(payload)
    now = utc_now()
    trials = [
        new_mixed_trial_record(
            study_version_id=bundle.version.study_version_id,
            definition_sha256=bundle.version.definition_sha256,
            domains=bundle.factor_domains,
            trial_number=len(bundle.trials) + index + 1,
            actual=point,
            created_at=now,
            origin="replicate",
            replicate_of_trial_id=str(trial_id),
        )
        for index in range(body.count)
    ]
    try:
        identities, replayed = insert_bayesian_replicates(
            settings.workspace_root,
            study_version_id=bundle.version.study_version_id,
            parent_trial_id=str(trial_id),
            request_id=str(body.request_id),
            request_sha256=checksum,
            request_json=_json_dumps(payload),
            expected_history_revision_id=str(body.expected_history_revision_id),
            expected_history_sha256=body.expected_history_sha256,
            trials=trials,
            total_trial_budget=body.total_trial_budget,
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    updated = load_validated_mixed_study(settings, str(study_id))
    by_id = {trial.trial_id: trial for trial in updated.trials}
    return MixedReplicateCreateResponse(
        study_id=study_id,
        study_version_id=UUID(bundle.version.study_version_id),
        request_id=body.request_id,
        parent_trial_id=trial_id,
        source_history_revision_id=body.expected_history_revision_id,
        source_history_sha256=body.expected_history_sha256,
        request_sha256=checksum,
        trials=[mixed_trial_response(updated, by_id[identity]) for identity in identities],
        replayed=replayed,
    )
