"""Historical mixture reports validate only their immutable source dependency graph."""

from dataclasses import asdict
from typing import Any

from app.api.v1.schemas.reports import BayesianHistoryReportSource
from app.core.config import Settings
from app.services.bayesian_studies import canonical_bayesian_observation_history_sha256
from app.services.bo_mixture_studies import (
    MixtureValidatedStudy,
    load_validated_mixture_definition,
    mixture_factors,
    mixture_trial_response,
)
from app.services.bo_mixture_workflow import read_mixture_model, validate_mixture_batch_record
from app.services.dedicated_report_readers import invalid, parsed
from app.storage import bayesian_studies as storage


def read_mixture_bayesian(
    settings: Settings, source: BayesianHistoryReportSource
) -> tuple[dict[str, Any], str, str]:
    root = settings.workspace_root
    owner, version, body, design, initial = load_validated_mixture_definition(
        settings, str(source.study_id)
    )
    history = storage.get_bayesian_history_revision_record(root, str(source.history_revision_id))
    if (
        history is None
        or history.study_version_id != version.study_version_id
        or history.schema_version != 2
        or str(source.study_version_id) != version.study_version_id
        or source.definition_sha256 != version.definition_sha256
        or source.expected_source_sha256 != history.observation_history_sha256
    ):
        raise invalid("report_source_changed")
    if source.attachment.kind not in {"none", "batch"}:
        raise invalid("report_source_kind_mismatch")
    members = parsed(history.completed_trial_ids_json)
    if (
        not isinstance(members, list)
        or not all(isinstance(item, str) for item in members)
        or len(members) != history.completed_trial_count
        or len(set(members)) != len(members)
        or len(members) > 200
    ):
        raise invalid("report_source_changed")
    observations = []
    for identity in members:
        trial = storage.get_bayesian_trial_record(root, identity)
        if (
            trial is None
            or trial.study_version_id != version.study_version_id
            or trial.state != "completed"
        ):
            raise invalid("report_source_changed")
        observations.append(trial)
    numbers = [trial.trial_number for trial in observations]
    if (
        numbers != sorted(set(numbers))
        or canonical_bayesian_observation_history_sha256(
            definition_sha256=version.definition_sha256,
            completed_trials=observations,
            schema_version=2,
        )
        != history.observation_history_sha256
    ):
        raise invalid("report_source_changed")
    record = None
    trials = observations
    if source.attachment.kind == "batch":
        ref = source.attachment
        record = storage.get_bayesian_recommendation_batch_record(root, str(ref.batch_id))
        if (
            record is None
            or record.study_version_id != version.study_version_id
            or record.source_history_revision_id != history.history_revision_id
            or record.source_observation_history_sha256 != history.observation_history_sha256
            or record.result_sha256 != ref.result_json_sha256
            or record.result_sha256 != ref.result_payload_sha256
        ):
            raise invalid("report_source_changed")
        config = parsed(record.config_json)
        cutoff = config.get("expected_trial_count") if isinstance(config, dict) else None
        if (
            type(cutoff) is not int
            or not 1 <= cutoff <= 200
            or not 1 <= record.batch_size <= 8
            or cutoff + record.batch_size > 200
        ):
            raise invalid("report_source_changed")
        trials = storage.list_bayesian_trial_records(
            root, version.study_version_id, limit=cutoff + record.batch_size
        )
        if [trial.trial_number for trial in trials] != list(
            range(1, cutoff + record.batch_size + 1)
        ):
            raise invalid("report_source_changed")
    bundle = MixtureValidatedStudy(
        owner, version, body, design, trials, [history], history, None, []
    )
    projected = [
        mixture_trial_response(bundle, trial).model_dump(mode="json") for trial in observations
    ]
    if any(value["response_values"] is None for value in projected):
        raise invalid("report_source_changed")
    attachment = None
    if record is not None:
        attachment = validate_mixture_batch_record(
            settings, bundle, record, immutable_selected_trials=True
        )
        for item in attachment["items"]:
            selected_trial = item.pop("trial")
            item["trial_reference"] = {
                key: selected_trial[key]
                for key in ("trial_id", "trial_number", "coordinates_sha256")
            }
        from uuid import UUID

        _, snapshot, _ = read_mixture_model(
            settings, bundle, UUID(attachment["config"]["model_id"])
        )
        attachment["response_models"] = snapshot["response_models"]
        attachment["warnings"] = snapshot["warnings"]
    return (
        {
            "definition": {
                "schema_version": 8,
                "method_version": owner.method_version,
                "request": body.model_dump(mode="json"),
                "design_domain": design.payload(),
                "initial_design": initial,
                "report_projection_policy": "mixture_definition_display_v1",
                "objective": body.objective.model_dump(mode="json"),
                "factors": mixture_factors(body),
            },
            "history": asdict(history),
            "observations": projected,
            "attachment": attachment,
            "source_warnings": ["historical_snapshot_without_current_trial_overlay"],
            "owner": {
                "method_id": owner.method_id,
                "method_version": owner.method_version,
                "app_version": owner.app_version,
                "created_at": owner.created_at,
            },
        },
        owner.name,
        history.created_at,
    )
