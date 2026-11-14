"""Mixture replication preserves actual settings through the shared atomic store."""

from uuid import UUID

from app.api.v1.schemas.bayesian import BayesianReplicateCreateRequest
from app.api.v1.schemas.bo_mixture_lifecycle import MixtureReplicateCreateResponse
from app.core.config import Settings
from app.services.analysis_run_execution import utc_now
from app.services.bayesian_replicates import _error
from app.services.bo_mixture_studies import (
    load_validated_mixture_study,
    mixture_trial_response,
    new_mixture_trial_record,
)
from app.storage.bayesian_replicates import insert_bayesian_replicates
from app.storage.bayesian_studies import BayesianStorageConflict
from app.storage.bo_planning import planning_json, planning_sha


def create_mixture_replicates(
    settings: Settings, study_id: UUID, trial_id: UUID, body: BayesianReplicateCreateRequest
) -> MixtureReplicateCreateResponse:
    bundle = load_validated_mixture_study(settings, str(study_id))
    parent = next((t for t in bundle.trials if t.trial_id == str(trial_id)), None)
    if parent is None or parent.state != "completed":
        raise _error("bayesian_replicate_parent_not_completed")
    point = mixture_trial_response(bundle, parent).actual_coordinates
    payload = {
        "schema_version": 1,
        "study_id": str(study_id),
        "study_version_id": bundle.version.study_version_id,
        "parent_trial_id": str(trial_id),
        "request": body.model_dump(mode="json"),
    }
    checksum, now = planning_sha(payload), utc_now()
    trials = [
        new_mixture_trial_record(
            study_version_id=bundle.version.study_version_id,
            definition_sha256=bundle.version.definition_sha256,
            design=bundle.design,
            trial_number=len(bundle.trials) + i + 1,
            actual=point,
            created_at=now,
            origin="replicate",
            replicate_of_trial_id=str(trial_id),
        )
        for i in range(body.count)
    ]
    try:
        identities, replayed = insert_bayesian_replicates(
            settings.workspace_root,
            study_version_id=bundle.version.study_version_id,
            parent_trial_id=str(trial_id),
            request_id=str(body.request_id),
            request_sha256=checksum,
            request_json=planning_json(payload),
            expected_history_revision_id=str(body.expected_history_revision_id),
            expected_history_sha256=body.expected_history_sha256,
            trials=trials,
            total_trial_budget=body.total_trial_budget,
        )
    except BayesianStorageConflict as exc:
        raise _error(exc.code) from exc
    updated = load_validated_mixture_study(settings, str(study_id))
    by_id = {t.trial_id: t for t in updated.trials}
    return MixtureReplicateCreateResponse(
        study_id=study_id,
        study_version_id=UUID(bundle.version.study_version_id),
        request_id=body.request_id,
        parent_trial_id=trial_id,
        source_history_revision_id=body.expected_history_revision_id,
        source_history_sha256=body.expected_history_sha256,
        request_sha256=checksum,
        trials=[mixture_trial_response(updated, by_id[k]) for k in identities],
        replayed=replayed,
    )
