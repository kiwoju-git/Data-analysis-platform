"""Read only the explicitly requested mixed history/batch, never a new fit."""

import sqlite3
from dataclasses import asdict
from types import SimpleNamespace
from typing import Any

from pydantic import TypeAdapter

from app.api.v1.schemas.bayesian import BayesianLinearConstraintResponse
from app.api.v1.schemas.bo_curve_policy import AnyDesirabilityObjective
from app.api.v1.schemas.bo_dataset_source import DatasetImportedInitialDesign
from app.api.v1.schemas.bo_mixed_studies import (
    MixedFactorResponse,
    MixedInitialDesignResponse,
    mixed_constraint_definitions,
    mixed_factor_domains,
)
from app.api.v1.schemas.reports import BayesianHistoryReportSource
from app.core.config import Settings
from app.services.bayesian_studies import (
    SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS,
    canonical_bayesian_observation_history_sha256,
)
from app.services.bo_mixed_batches import validate_mixed_batch_record
from app.services.bo_mixed_studies import (
    mixed_definition_payload,
    mixed_trial_response,
)
from app.services.dedicated_report_readers import (
    digest,
    invalid,
    parsed,
    validate_imported_report_initial,
)
from app.statistics.bo_mixed_initial_design import validate_mixed_constraints
from app.storage.bayesian_studies import (
    get_bayesian_history_revision_record,
    get_bayesian_recommendation_batch_record,
    get_bayesian_study_record,
    get_bayesian_study_version_record,
    get_bayesian_trial_record,
    list_bayesian_trial_records,
)
from app.storage.metadata import metadata_db_path


def read_mixed_bayesian(
    settings: Settings, source: BayesianHistoryReportSource
) -> tuple[dict[str, Any], str, str]:
    root = settings.workspace_root
    owner = get_bayesian_study_record(root, str(source.study_id))
    with sqlite3.connect(metadata_db_path(root)) as connection:
        version_row = connection.execute(
            "SELECT study_id,version_number FROM bayesian_study_versions WHERE study_version_id=?",
            (str(source.study_version_id),),
        ).fetchone()
    version = (
        None
        if version_row is None
        else get_bayesian_study_version_record(
            root, study_id=version_row[0], version_number=version_row[1]
        )
    )
    history = get_bayesian_history_revision_record(root, str(source.history_revision_id))
    if owner is None or version is None or history is None:
        raise invalid("report_source_not_found")
    if (
        owner.method_id != "doe.bayesian_optimization"
        or owner.method_version not in SUPPORTED_BAYESIAN_STUDY_METHOD_VERSIONS
        or version.study_id != owner.study_id
        or version.schema_version != 7
        or history.schema_version != 2
        or history.study_version_id != version.study_version_id
        or str(source.study_version_id) != version.study_version_id
        or source.definition_sha256 != version.definition_sha256
        or source.expected_source_sha256 != history.observation_history_sha256
    ):
        raise invalid("report_source_changed")
    factors = TypeAdapter(list[MixedFactorResponse]).validate_python(parsed(version.factors_json))
    domains = mixed_factor_domains(factors)
    objective: AnyDesirabilityObjective = TypeAdapter(AnyDesirabilityObjective).validate_python(
        parsed(version.objective_json)
    )
    constraints = [
        BayesianLinearConstraintResponse.model_validate(row)
        for row in parsed(version.constraints_json)
    ]
    validate_mixed_constraints(domains, mixed_constraint_definitions(constraints))
    initial_raw = parsed(version.initial_design_json)
    initial = (
        DatasetImportedInitialDesign
        if isinstance(initial_raw, dict) and initial_raw.get("policy") == "dataset_observations_v1"
        else MixedInitialDesignResponse
    ).model_validate(initial_raw)
    if [factor.order for factor in factors] != list(range(1, len(factors) + 1)):
        raise invalid("report_source_changed")
    definition = mixed_definition_payload(
        method_version=owner.method_version,
        factors=factors,
        objective=objective,
        constraints=constraints,
        initial_design=initial,
    )
    if digest(definition) != version.definition_sha256:
        raise invalid("report_source_changed")
    if isinstance(initial, DatasetImportedInitialDesign):
        validate_imported_report_initial(settings, version, initial)
    context: Any = SimpleNamespace(
        version=version, factor_domains=domains, objective=objective, constraints=constraints
    )
    members = parsed(history.completed_trial_ids_json)
    if (
        not isinstance(members, list)
        or not all(isinstance(item, str) for item in members)
        or len(members) != history.completed_trial_count
        or len(members) > 200
        or len(set(members)) != len(members)
    ):
        raise invalid("report_source_changed")
    observation_records = []
    observations = []
    for identity in members:
        trial = get_bayesian_trial_record(root, identity)
        if (
            trial is None
            or trial.study_version_id != version.study_version_id
            or trial.state != "completed"
        ):
            raise invalid("report_source_changed")
        value = mixed_trial_response(context, trial)
        if value.response_values is None:
            raise invalid("report_source_changed")
        observation_records.append(trial)
        observations.append(value.model_dump(mode="json"))
    numbers = [trial.trial_number for trial in observation_records]
    if (
        numbers != sorted(set(numbers))
        or canonical_bayesian_observation_history_sha256(
            definition_sha256=version.definition_sha256,
            completed_trials=observation_records,
            schema_version=2,
        )
        != history.observation_history_sha256
    ):
        raise invalid("report_source_changed")
    attachment = None
    if source.attachment.kind == "recommendation":
        raise invalid("report_source_kind_mismatch")
    if source.attachment.kind == "batch":
        ref = source.attachment
        record = get_bayesian_recommendation_batch_record(root, str(ref.batch_id))
        if (
            record is None
            or record.study_version_id != version.study_version_id
            or record.source_history_revision_id != history.history_revision_id
            or record.source_observation_history_sha256 != history.observation_history_sha256
            or record.result_sha256 != ref.result_json_sha256
        ):
            raise invalid("report_source_changed")
        config = parsed(record.config_json)
        cutoff = config.get("source_trial_count") if isinstance(config, dict) else None
        if (
            type(cutoff) is not int
            or not 1 <= cutoff <= 200
            or not 1 <= record.batch_size <= 8
            or cutoff + record.batch_size > 200
        ):
            raise invalid("report_source_changed")
        # Later trials and batches are not dependencies of this immutable source.
        required_count = cutoff + record.batch_size
        trials = list_bayesian_trial_records(root, version.study_version_id, limit=required_count)
        if [trial.trial_number for trial in trials] != list(range(1, required_count + 1)):
            raise invalid("report_source_changed")
        saved = validate_mixed_batch_record(
            settings,
            version=version,
            factors=factors,
            objective=objective,
            constraints=constraints,
            trials=trials,
            history=history,
            record=record,
        )
        if saved.result_sha256 != ref.result_payload_sha256:
            raise invalid("report_source_changed")
        attachment = saved.model_dump(mode="json", exclude={"is_latest", "batch_state"})
        for item in attachment["items"]:
            item.pop("current_trial", None)
    return (
        {
            "definition": definition,
            "history": asdict(history),
            "observations": observations,
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
